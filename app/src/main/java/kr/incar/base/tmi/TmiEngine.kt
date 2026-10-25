package kr.incar.base.tmi

import android.content.SharedPreferences
import android.os.SystemClock
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kr.incar.base.car.CarState
import kr.incar.base.car.Gear
import kr.incar.base.voice.Voice
import kotlin.math.roundToInt

/**
 * Pixel TMI의 두뇌.
 * - 내 위치: 속도를 시간에 곱해 "길 위 몇 미터 지점"인지 계속 더한다 (posM).
 * - 다가가면: 500m·100m 앞에서 음성 + 큰 카드, 지나가면 "아직 있나요?"
 * - 차가 스스로 제보: 급감속(같은 지점에 몰리면 위험 구간), 와이퍼(국지성 비)
 * - 평화로우면: 동네 TMI를 꺼낸다. 사용자가 끄지 않는 한 계속.
 * 모든 함수는 메인 스레드(viewModelScope)에서 부른다.
 */
class TmiEngine(
    private val scope: CoroutineScope,
    private val voice: Voice,
    private val fleet: FleetSimulator,
    private val prefs: SharedPreferences,
) {
    private val _ui = MutableStateFlow(TmiUi(rewards = loadRewards(), fleetNearby = fleet.nearbyCars))
    val ui: StateFlow<TmiUi> = _ui.asStateFlow()

    private val _fx = MutableSharedFlow<Fx>(extraBufferCapacity = 16)
    /** 화면 효과(컷인·코인·레벨 업)를 한 번씩 알린다 */
    val fx: SharedFlow<Fx> = _fx.asSharedFlow()

    /** 시연 배속 — 길 위 이동을 몇 배로 빨리 감을지 (실차 = 1) */
    var timeScale = 1.0
    /** 평화로울 때 동네 TMI 간격 */
    var peacefulGapMs = 60_000L

    private var car = CarState()
    private var navi = NaviState()
    private var naviBaseM = 0.0
    private var lastTick = 0L
    private val alerted = mutableSetOf<String>()
    private val passed = mutableSetOf<String>()
    private var lastLineAt = 0L
    private var localIndex = 0
    private val speeds = ArrayDeque<Pair<Long, Float>>()
    private var lastAutoBrakeAt = 0L
    private var drivenSinceParkM = 0.0
    private var briefedThisTrip = false
    private var greeted = false
    private var lastRouteName: String? = null
    private var loop: Job? = null

    fun start() {
        _ui.update { it.copy(history = loadHistory()) }
        if (loop != null) return
        lastTick = SystemClock.elapsedRealtime()
        loop = scope.launch {
            while (isActive) {
                tick()
                housekeeping()
                delay(200)
            }
        }
    }

    // ───────────────────────── 입력 ─────────────────────────

    fun onCar(s: CarState) {
        val prev = car
        car = s
        // 와이퍼는 비 말고도 그냥 워셔액을 뿌릴 때가 있어서 비 제보로 치지 않는다 (비 = 그날 기상청 예보 · "소나기" 제보)
        // P → 주행: 이번 운행 첫 브리핑
        if (prev.gear == Gear.P && s.gear != null && s.gear != Gear.P) {
            _ui.update { it.copy(parkedSummary = false) }
            if (!briefedThisTrip) briefing()
        }
        // 주행 → P: 정산
        if (prev.gear != null && prev.gear != Gear.P && s.gear == Gear.P && drivenSinceParkM > 300) parkSummary()
    }

    fun onNavi(n: NaviState) {
        val hadRoute = navi.hasRoute
        val now = SystemClock.elapsedRealtime()
        // 차는 서 있는데 남은 거리가 줄면 = 내비 모의 주행(가상 도로 주행). 그 속도로 길을 따라간다
        val prev = navi.remainM
        val cur = n.remainM
        if (allowNaviSim && !demoMode && hadRoute && n.hasRoute && n.destinationName == navi.destinationName && prev != null && cur != null && cur < prev) {
            val dtS = (now - lastNaviAt) / 1000.0
            if (dtS in 0.4..30.0) naviSpeedMps = ((prev - cur) / dtS).coerceIn(0.0, 60.0)
            lastNaviMoveAt = now
        }
        lastNaviAt = now
        navi = n
        naviBaseM = _ui.value.posM
        if (n.hasRoute && (!hadRoute || n.destinationName != lastRouteName)) {
            lastRouteName = n.destinationName
            routeStartPos = _ui.value.posM; routeLen = (n.remainM ?: 0).toDouble(); chaserFired = false
            if (!demoMode) _ui.update { it.copy(hazards = fleet.seedRoute(it.posM, n.remainM ?: 0)) }
            say("목적지가 정해졌어요. 가는 길 TMI 알려 드릴게요.", listOf("dest_set"), kind = TmiKind.SYSTEM, speech = "route_set",
                text = "${n.destinationName}까지 ${"%.1f".format((n.remainM ?: 0) / 1000.0)}km\n가는 길 TMI 시작")
            briefing()
        }
        if (!n.hasRoute) lastRouteName = null
    }

    private var lastNaviAt = 0L
    private var lastNaviMoveAt = 0L
    private var naviSpeedMps = 0.0

    // ── 내 제보 기록 (설정 저장소에 최근 50건) ──
    private fun loadHistory(): List<ReportRecord> = runCatching {
        val arr = org.json.JSONArray(prefs.getString("history", "[]"))
        (0 until arr.length()).mapNotNull { i ->
            val o = arr.getJSONObject(i)
            val t = runCatching { HazardType.valueOf(o.getString("type")) }.getOrNull() ?: return@mapNotNull null
            ReportRecord(o.getString("id"), t, if (o.has("lane")) o.getInt("lane") else null, o.getLong("at"),
                runCatching { ReportStage.valueOf(o.getString("stage")) }.getOrDefault(ReportStage.RECEIVED),
                o.optInt("reports", 1), o.optInt("sharedTo"), o.optInt("confirms"), o.optInt("coins"))
        }
    }.getOrDefault(emptyList())

    private fun saveHistory(list: List<ReportRecord>) {
        val arr = org.json.JSONArray()
        list.take(50).forEach { r ->
            arr.put(org.json.JSONObject().apply {
                put("id", r.id); put("type", r.type.name); r.lane?.let { put("lane", it) }; put("at", r.at)
                put("stage", r.stage.name); put("reports", r.reports); put("sharedTo", r.sharedTo); put("confirms", r.confirms); put("coins", r.coins)
            })
        }
        prefs.edit().putString("history", arr.toString()).apply()
    }

    private fun record(id: String, change: (ReportRecord) -> ReportRecord) {
        val list = _ui.value.history.map { if (it.id == id) change(it) else it }
        _ui.update { it.copy(history = list) }
        saveHistory(list)
    }

    /** 시연(출근길 시연·모의 주행) 중인가 — 뒤에서 오는 긴급차량 장면을 넣을지 */
    var demoNow: () -> Boolean = { demoMode }
    private var routeStartPos = 0.0
    private var routeLen = 0.0
    private var chaserFired = false
    private var chaserName = "구급차"

    /** 뒤차가 제보한 긴급차량: 뒤 350m에서 나보다 조금 빠르게 다가와 앞질러 간다 */
    fun emergencyFromBehind(kind: String = if (kotlin.random.Random.nextBoolean()) "구급차" else "소방차") {
        val pos = _ui.value.posM
        chaserName = kind
        val h = Hazard("chase-${System.currentTimeMillis()}", HazardType.EMERGENCY, lane = null, atM = pos - 350, reports = 3, minutesAgo = 0, source = Source.DRIVER)
        _ui.update { it.copy(chaser = h) }
        say("뒤에서 ${kind}가 와요. 길을 터 주세요.", listOf("sfx_zing"), urgent = true, kind = TmiKind.DANGER,
            text = "뒤차 제보 · ${kind} 접근 중\n오른쪽으로 비켜 길을 터 주세요")
    }

    /** 긴급차량은 함께 다니지 않고 6초 안에 휙 앞질러 지나간다 */
    @Suppress("UNUSED_PARAMETER")
    private fun moveChaser(pos: Double, v: Double, dt: Double) {
        val c = _ui.value.chaser ?: return
        if (System.currentTimeMillis() - c.reportedAt > 6000) {
            _ui.update { it.copy(chaser = null) }
            line(TmiLine(TmiKind.SYSTEM, "${chaserName}가 지나갔어요 · 다시 원래 차로로", emptyList()), speak = false)
        }
    }

    /** 오늘 날씨 한 줄 (기상청 예보, 없으면 null) — 브리핑 맨 앞 */
    var weatherLine: () -> String? = { null }

    /** 펫 이름 (설정에서 바꿈) — "안녕! ○○예요" */
    var petName = "티미"
    /** "TMI, 잠실역 가자" → 길안내 (탭: 네이버 지도) */
    var onNavigate: ((String) -> Unit)? = null

    /** 차는 섰는데 남은 거리가 줄면 내비 모의 주행으로 본다 (Pleos 에뮬레이터용 — 탭은 GPS가 흔들려 끈다) */
    var allowNaviSim = true
    private var arrivedAt = 0L
    /** 내비가 '도착'을 알렸을 때 */
    fun markArrived() { arrivedAt = SystemClock.elapsedRealtime() }
    private fun atDestination() = SystemClock.elapsedRealtime() - arrivedAt < 15 * 60_000 || (navi.hasRoute && remainingM() < 500)

    /** 시연 시나리오 중이면 true — 제보 1건으로 바로 공유 */
    var demoMode = false
    /** 같은 지점 제보가 몇 건 모여야 다른 차에 공유하나 (설정에서 1~3) */
    var requiredReports = 2
    /** 같은 지점 제보가 몇 건 모여야 공유하나 — 실제 차는 기준대로, 시연(출근길·태블릿)은 1건으로 바로 */
    val neededReports: Int get() = if (demoMode || !kr.incar.base.car.CarSpeedSource.available) 1 else requiredReports

    /** 말 한마디 처리 (음성 인식 결과 또는 시연 주입) */
    fun onUtterance(text: String) {
        _ui.update { it.copy(heard = text) }
        if (resetAskedAt != 0L && answerReset(text)) return             // "정말 지울까요?" 대답 먼저
        val armed = SystemClock.elapsedRealtime() < reportArmedUntil
        when (val cmd = VoiceCommand.parse(text)) {
            VoiceCommand.Briefing -> briefing()
            is VoiceCommand.Navigate -> onNavigate?.invoke(cmd.place)
            is VoiceCommand.Refuse -> { reportArmedUntil = 0L; say("그건 공유하지 않아요.", emptyList(), kind = TmiKind.SYSTEM, text = cmd.why) }
            is VoiceCommand.Report -> if (!cmd.weak || armed || cmd.lane != null) { reportArmedUntil = 0L; report(cmd.type, cmd.lane) }
            VoiceCommand.StartReport -> {
                reportArmedUntil = SystemClock.elapsedRealtime() + 10_000
                say("제보 시작?", emptyList(), kind = TmiKind.SYSTEM, speech = "report_start", text = "무엇을 제보할까요?\n예: 1차로 포트홀 · 구급차 · 화재 · 고라니\n침수·범람 · 결빙 · 폭설 · 안개 · 신호등 고장")
            }
            VoiceCommand.StillThere -> if (_ui.value.verify != null) answerVerify(true)
            VoiceCommand.Gone -> if (_ui.value.verify != null) answerVerify(false)
            VoiceCommand.Reset -> askReset()
            VoiceCommand.TurnOff -> setOn(false)
            VoiceCommand.TurnOn -> setOn(true)
            VoiceCommand.Mute -> {
                voice.stop()
                voice.muted = true
                line(TmiLine(TmiKind.SYSTEM, "음소거 · 소리를 껐어요\n말풍선은 그대로 보여 드릴게요", emptyList()), speak = false)
            }
            VoiceCommand.Louder -> {
                voice.volume = (voice.volume + 0.2f).coerceAtMost(1f)
                say("소리를 키웠어요.", emptyList(), kind = TmiKind.SYSTEM, text = "소리 크기 ${(voice.volume * 100).toInt()}%")
            }
            VoiceCommand.Quieter -> {
                voice.volume = (voice.volume - 0.2f).coerceAtLeast(0.2f)
                say("소리를 줄였어요.", emptyList(), kind = TmiKind.SYSTEM, text = "소리 크기 ${(voice.volume * 100).toInt()}%")
            }
            VoiceCommand.Unmute -> {
                voice.muted = false
                say("소리를 다시 켰어요.", emptyList(), kind = TmiKind.SYSTEM, text = "소리를 다시 켰어요")
            }
            // 늘 듣고 있으니 상관없는 말(동승자 대화 등)은 조용히 넘긴다. 제보 시작 뒤에만 다시 묻는다
            VoiceCommand.Unknown -> if (armed) say("다시 말해 주세요.", emptyList(), kind = TmiKind.SYSTEM, text = "잘 못 들었어요\n예: 2차로 낙하물")
        }
    }

    // ── 리셋: "정말 지울까요?" 한 번 더 · 30초 안에 대답이 없으면 취소 ──
    private var resetAskedAt = 0L

    private fun askReset() {
        resetAskedAt = SystemClock.elapsedRealtime()
        say("정말 지울까요?", emptyList(), urgent = true, kind = TmiKind.SYSTEM,
            text = "정말 지울까요?\n내가 한 제보 표시를 모두 지워요 · \"응\" / \"아니\"")
    }

    /** 대답이면 처리하고 true (지우기 · 취소), 아니면 false */
    private fun answerReset(text: String): Boolean {
        val t = text.replace(" ", "").trimEnd('.', '!', '?', '~')
        val yes = t in setOf("응", "네", "예", "어", "엉", "웅", "넵", "넹") || listOf("그래", "맞아", "지워", "좋아", "해줘", "확인", "오케이", "응지").any { it in t }
        val no = listOf("아니", "취소", "하지마", "됐어", "그만", "싫어", "놔둬", "그냥둬").any { it in t }
        return when {
            no -> { resetAskedAt = 0L; say("취소했어요.", emptyList(), kind = TmiKind.SYSTEM, text = "취소했어요 · 그대로 둘게요"); true }
            yes -> { resetAskedAt = 0L; clearMine("다 지웠어요 · 깨끗해졌어요!"); true }
            else -> false
        }
    }

    /** 내 제보 표시(길 위에 남은 것) 지우기 — 기록(내 제보 기록·코인)은 그대로 */
    private fun clearMine(msg: String?) {
        _ui.update { it.copy(mine = emptyList(), myReport = null) }
        if (msg != null) line(TmiLine(TmiKind.SYSTEM, msg, emptyList()), speak = false)
    }

    /** 주차한 채로 20분이 지나면 길 위 내 제보 표시를 정리한다 */
    private var parkedSince = 0L

    private fun housekeeping() {
        val now = SystemClock.elapsedRealtime()
        if (resetAskedAt != 0L && now - resetAskedAt > 30_000) {
            resetAskedAt = 0L
            say("대답이 없어서 취소했어요.", emptyList(), kind = TmiKind.SYSTEM, text = "대답이 없어서 취소했어요")
        }
        if (car.gear == Gear.P) {
            if (parkedSince == 0L) parkedSince = now
            if (now - parkedSince > 20 * 60_000L && _ui.value.mine.isNotEmpty()) clearMine("주차 20분 · 제보 표시를 정리했어요")
        } else parkedSince = 0L
    }

    /** "제보" 한마디 뒤 10초 동안은 위험 이름만 말해도 접수 */
    private var reportArmedUntil = 0L

    fun setListening(on: Boolean) = _ui.update { it.copy(listening = on, heard = if (on) null else it.heard) }

    /** TMI를 켜고 끌 때 (듣기도 같이 쉬게) */
    var onToggle: ((Boolean) -> Unit)? = null

    fun setOn(on: Boolean) {
        _ui.update { it.copy(on = on) }
        onToggle?.invoke(on)
        if (on) voice.say("TMI를 켭니다.", listOf("tmi_on")) else {
            voice.stop()
            voice.say("TMI를 끕니다.", listOf("tmi_off"))
        }
    }

    // ───────────────────────── 제보 ─────────────────────────

    /** 큰 버튼 한 번 또는 음성 한마디 — 지금 내 위치에 제보 */
    fun report(type: HazardType, lane: Int?) {
        val t0 = SystemClock.elapsedRealtime()
        val h = Hazard(
            id = "mine-${System.currentTimeMillis()}", type = type, lane = lane, atM = _ui.value.posM,
            reports = 1, minutesAgo = 0, source = Source.MINE, stage = ReportStage.RECEIVED,
        )
        _ui.update { it.withMine(h).copy(history = listOf(ReportRecord(h.id, type, lane, h.reportedAt)) + it.history) }
        saveHistory(_ui.value.history)
        passed += h.id
        addCoins(0, reports = 1)   // 코인은 여기서 안 준다 — 같은 지점 제보가 여러 건 모여 확인되면 그때
        val laneTxt = laneText(lane)
        val need = neededReports
        if (need <= 1) {
            say("제보 접수했어요. 주변 차량에 바로 알릴게요.", listOf("report_done"), kind = TmiKind.MINE, speech = "report_shared_now",
                text = "제보 접수 ${clockText(h.reportedAt)}\n${laneTxt}${type.label} · 주변 차량에 바로 공유\n다른 차량이 확인하면 코인")
        } else {
            say("제보 접수했어요. 같은 제보가 더 모이면 공유할게요.", listOf("report_done"), kind = TmiKind.MINE, speech = "report_pending",
                text = "제보 접수 ${clockText(h.reportedAt)}\n${laneTxt}${type.label} · 확인 대기 1/$need\n같은 제보가 더 모이면 코인을 드려요")
        }
        fleet.submit(h, timeScale, need) { updated -> onReportUpdate(updated, t0) }
    }

    /** 내 제보 목록에 넣기 (같은 건은 새 것으로, 최근 8건) */
    private fun TmiUi.withMine(h: Hazard): TmiUi = copy(myReport = h, mine = (listOf(h) + mine.filter { it.id != h.id }).take(8))

    private fun onReportUpdate(h: Hazard, t0: Long) {
        val first = _ui.value.lastReportLatencyMs == null || _ui.value.myReport?.stage == ReportStage.RECEIVED
        _ui.update {
            it.copy(
                myReport = if (it.myReport?.id == h.id) h else it.myReport,
                mine = it.mine.map { m -> if (m.id == h.id) h else m },
                lastReportLatencyMs = if (h.stage == ReportStage.SHARED && first) SystemClock.elapsedRealtime() - t0 else it.lastReportLatencyMs,
            )
        }
        if (h.source == Source.MINE) record(h.id) { it.copy(stage = h.stage, reports = h.reports, sharedTo = h.sharedTo, confirms = h.confirms) }
        if (h.stage == ReportStage.RECEIVED && h.reports > 1) {
            line(TmiLine(TmiKind.MINE, "같은 지점 제보 ${h.reports}/$neededReports · 다른 차량도 봤어요", emptyList()), speak = false)
        }
        if (h.stage == ReportStage.SHARED && h.source == Source.MINE) {
            val secs = (h.sharedAt ?: h.reportedAt) - h.reportedAt
            line(TmiLine(TmiKind.MINE, "제보 ${h.reports}건 모임 → ${h.sharedTo}대에 공유\n접수 ${clockText(h.reportedAt)} · 공유 ${clockText(h.sharedAt ?: h.reportedAt)} (${"%.1f".format(secs / 1000.0)}초)", emptyList()), speak = false)
        }
        if (h.stage == ReportStage.CONFIRMED) {
            // 내 음성 제보가 여러 건으로 확인됐을 때만 코인 (자동 감지는 0)
            val coins = if (h.source == Source.MINE) h.confirms * COINS_PER_CONFIRM else 0
            addCoins(coins, helped = h.sharedTo)
            if (coins > 0) record(h.id) { it.copy(coins = coins) }
            say("다른 차량들도 확인했습니다. 신뢰도가 올라갔습니다.", listOf("confirmed"), kind = TmiKind.MINE,
                text = "같은 지점 제보 ${h.reports}건 + 다른 차량 ${h.confirms}대 확인 ${clockText(h.lastSeenAt)} · 신뢰도 높음" +
                    if (coins > 0) " · +${coins}코인" else "")
        }
    }

    /** 지나간 위험 "아직 있나요?"에 대한 답 */
    fun answerVerify(stillThere: Boolean) {
        val v = _ui.value.verify ?: return
        _ui.update { it.copy(verify = null) }
        if (stillThere) {
            val now = System.currentTimeMillis()
            _ui.update { u -> u.copy(hazards = u.hazards.map { if (it.id == v.hazard.id) it.copy(lastSeenAt = now, confirms = it.confirms + 1) else it }) }
            say("확인 감사합니다.", listOf("verify_thanks"), kind = TmiKind.MINE,
                text = "고마워요! 뒤따르는 차들에게 도움이 됐어요\n${v.hazard.type.label} 아직 있음 · ${clockText(now)}")
        } else {
            _ui.update { u -> u.copy(hazards = u.hazards.filterNot { it.id == v.hazard.id }) }
            say("해결된 것으로 표시했습니다. 고맙습니다.", listOf("verify_gone"), kind = TmiKind.MINE,
                text = "고마워요! ${v.hazard.type.label} 해결로 표시했어요\n뒤따르는 차들에게 도움이 됐어요")
        }
    }

    private fun autoBrake() {
        val h = Hazard(
            id = "auto-${System.currentTimeMillis()}", type = HazardType.HARD_BRAKE, lane = null, atM = _ui.value.posM,
            reports = 1, minutesAgo = 0, source = Source.AUTO, stage = ReportStage.RECEIVED,
        )
        val t0 = SystemClock.elapsedRealtime()
        _ui.update { it.withMine(h) }
        say("급감속을 감지했습니다. 위험 구간으로 공유합니다.", listOf("auto_brake"), urgent = true, kind = TmiKind.MINE,
            text = "급감속 자동 감지 · 같은 지점 기록과 맞춰 보는 중")
        fleet.submit(h, timeScale, 1) { updated -> onReportUpdate(updated, t0) }   // 급감속은 차가 직접 감지한 1건 + 같은 지점 기록
    }

    private fun autoRain() {
        val h = Hazard(
            id = "rain-${System.currentTimeMillis()}", type = HazardType.RAIN, lane = null, atM = _ui.value.posM,
            reports = 1, minutesAgo = 0, source = Source.AUTO, stage = ReportStage.SHARED, sharedTo = FleetSimulator.RAIN_SHARED_TO,
        )
        _ui.update { it.withMine(h) }
        addCoins(0, helped = FleetSimulator.RAIN_SHARED_TO)
        say("비를 감지했습니다. 뒤따르는 차량에 알립니다.", listOf("auto_rain"), kind = TmiKind.MINE,
            text = "와이퍼 작동 = 비 감지 · 뒤따르는 차량 ${FleetSimulator.RAIN_SHARED_TO}대에 공유")
    }

    // ───────────────────────── 브리핑 ─────────────────────────

    /** "TMI 알려줘" — 목적지가 있으면 가는 길, 없으면 내 주변 */
    fun briefing() {
        briefedThisTrip = true
        val pos = _ui.value.posM
        val route = navi.hasRoute
        val range = if (route) remainingM().toDouble() else AROUND_M
        // 단속카메라·보호구역은 브리핑에서 빼고 (주행 중 300m 앞에서 따로 알린다)
        val ahead = _ui.value.hazards.filter { it.atM - pos in 0.0..range && it.type != HazardType.CAMERA && it.type != HazardType.SCHOOL }.sortedBy { it.atM }.take(3)

        val boarding = !greeted
        greeted = true
        val clips = mutableListOf<String>()
        val parts = mutableListOf<String>()
        if (boarding) {
            // 차에 타면 티미가 먼저 인사한다
            clips += listOf("sfx_hello", "hello")
            parts += "안녕! ${petName}${josa(petName, "예요", "이에요")}"
        }
        if (boarding) weatherLine()?.let { parts += it }
        clips += if (route) "tmi_intro" else "around_intro"
        parts += if (route) "가는 길 TMI" else "앞길 2km TMI"
        if (ahead.isEmpty()) {
            clips += if (route) "tmi_none" else "around_none"
            parts += if (route) "가는 길에 위험 제보 없음" else "진행 방향 2km 안 위험 제보 없음 · 평화로운 길"
        } else {
            clips += "tmi_n${ahead.size}"
            parts += "위험 ${ahead.size}곳"
            ahead.forEach { h ->
                // 1.5km는 "1킬로미터 앞", 4.2km는 "4킬로미터 앞" (말로 들을 때 앞당겨 말하지 않게 내림 쪽으로)
                val km = kotlin.math.floor((h.atM - pos) / 1000.0 + 0.3).toInt().coerceIn(1, 9)
                clips += "km$km"
                h.lane?.let { clips += "l$it" }
                clips += h.type.clip
                parts += "${km}km 앞 ${laneText(h.lane)}${h.type.label}"
            }
        }
        if (route && fleet.rainAhead && car.washerLow == true) {
            clips += "car_washer_rain"
            parts += "가는 길 비 소식 · 워셔액 부족"
        }
        if (route && (car.fuelRangeKm ?: 0f) * 1000 > remainingM() * 1.5) {
            clips += "car_fuel_ok"
            parts += "연료 충분"
        }
        if (!route && ahead.isEmpty()) {
            val l = fleet.localPool.first()
            clips += l.clips
            parts += l.text
        }
        clips += "tmi_end"
        say(parts.joinToString(" · "), clips, kind = if (ahead.isEmpty()) TmiKind.LOCAL else TmiKind.BRIEF, text = parts.joinToString(" · "))
    }

    private fun parkSummary() {
        drivenSinceParkM = 0.0
        briefedThisTrip = false
        _ui.update { it.copy(parkedSummary = true, approach = null, verify = null) }
        say("도착했어요! 오늘도 도로를 지켜 주셨어요.", listOf("park_summary", "mine_helped"), kind = TmiKind.MINE, speech = if (atDestination()) "arrived" else "parked",
            text = "오늘 내 제보 덕분에 ${FleetSimulator.HELPED_TODAY}대가 미리 속도를 줄였습니다")
        val arrived = atDestination()
        arrivedAt = 0L
        if (arrived) {
            // 목적지 도착: 폭죽 세레모니 + 도착 보너스
            _fx.tryEmit(Fx.Arrived(ARRIVAL_COINS))
            addCoins(ARRIVAL_COINS)
        }
    }

    // ───────────────────────── 매 0.2초 ─────────────────────────

    private fun tick() {
        val now = SystemClock.elapsedRealtime()
        val dt = (now - lastTick) / 1000.0
        lastTick = now
        val carV = (car.speedKmh ?: 0f) / 3.6
        val naviMoving = !demoMode && navi.hasRoute && carV < 0.5 && now - lastNaviMoveAt < 8000
        val v = if (naviMoving) naviSpeedMps else carV
        if (naviMoving != _ui.value.naviMoving) _ui.update { it.copy(naviMoving = naviMoving) }
        val nk = if (naviMoving) (naviSpeedMps * 3.6).toFloat() else 0f
        if (kotlin.math.abs(nk - _ui.value.naviSpeedKmh) > 1f) _ui.update { it.copy(naviSpeedKmh = nk) }
        val step = v * dt * timeScale
        val pos = _ui.value.posM + step
        drivenSinceParkM += step
        _ui.update { it.copy(posM = pos) }

        if (step > 0) ensureCamera(pos)
        speedWatch(now, pos)
        moveChaser(pos, v, dt)
        if (!chaserFired && navi.hasRoute && routeLen > 0 && v > 1 && demoNow() && pos - routeStartPos > routeLen * 0.35) {
            chaserFired = true
            emergencyFromBehind()
        }
        detectHardBrake(now)
        expire(pos)
        proximity(pos)
        passing(pos, now)
        peaceful(pos, now)
    }

    private var camSeq = 0
    private var overSince = 0L
    private var overWarnedAt = 0L

    /** 지금 제한속도: 어린이보호구역 300m 안이면 30, 아니면 60 (도심 기준) */
    fun speedLimit(pos: Double = _ui.value.posM): Int =
        if (_ui.value.hazards.any { it.type == HazardType.SCHOOL && it.atM - pos in -100.0..300.0 }) 30 else 60

    private fun speedWatch(now: Long, pos: Double) {
        val kmh = car.speedKmh ?: 0f
        val lim = speedLimit(pos)
        if (kmh > lim + 5) {
            if (overSince == 0L) overSince = now
            if (now - overSince > 3000 && now - overWarnedAt > 30_000) {
                overWarnedAt = now
                say("너무 빨라요! 속도를 줄여 주세요.", listOf("sfx_zing"), urgent = true, kind = TmiKind.DANGER,
                    text = "과속 중 · 제한 ${lim}km/h\n너무 빨라요! 속도를 줄여 주세요")
            }
        } else overSince = 0L
    }

    /** 달리는 동안 늘 앞쪽 1.5km 안에 단속카메라 하나 (필살기 시연) — 없으면 900~1200m 앞에 세운다 */
    private fun ensureCamera(pos: Double) {
        val hs = _ui.value.hazards
        if (hs.any { it.type == HazardType.CAMERA && it.atM in pos..(pos + 1500) }) return
        val at = pos + 900 + kotlin.random.Random.nextDouble(300.0)
        val cam = Hazard("cam-${camSeq++}", HazardType.CAMERA, lane = null, atM = at, reports = 0, minutesAgo = 0, source = Source.NAVI)
        _ui.update { it.copy(hazards = it.hazards + cam) }
    }

    /** 마지막 제보·확인 뒤 수명이 지나도록 새 음성 제보가 없으면 길에서 지운다 */
    private fun expire(pos: Double) {
        val now = System.currentTimeMillis()
        val gone = _ui.value.hazards.filter { it.expired(now) }
        if (gone.isEmpty()) return
        _ui.update { u -> u.copy(hazards = u.hazards.filterNot { h -> gone.any { it.id == h.id } }, approach = null) }
        gone.filter { it.atM >= pos && it.id !in passed }.forEach { h ->
            _fx.tryEmit(Fx.Expired(h))
            if ((car.speedKmh ?: 0f) > 1f || (car.gear != null && car.gear != kr.incar.base.car.Gear.P))
                say("새 제보가 없어 지웠습니다.", emptyList(), kind = TmiKind.SYSTEM,
                    text = "${laneText(h.lane)}${h.type.label} 제보가 ${spanText(h.type.ttlMin ?: 0)}째 없어 지웠어요")
        }
    }

    private fun detectHardBrake(now: Long) {
        val sp = car.speedKmh ?: return
        speeds.addLast(now to sp)
        while (speeds.isNotEmpty() && now - speeds.first().first > 2000) speeds.removeFirst()
        val peak = speeds.maxOf { it.second }
        if (peak >= 35f && peak - sp >= 25f && now - lastAutoBrakeAt > 15_000) {
            lastAutoBrakeAt = now
            speeds.clear()
            autoBrake()
        }
    }

    private fun proximity(pos: Double) {
        val next = _ui.value.hazards.filter { it.atM > pos && it.id !in passed }.minByOrNull { it.atM }
        val d = next?.let { (it.atM - pos).roundToInt() }
        _ui.update { it.copy(approach = if (next != null && d != null && d <= 700) Approach(next, d) else null) }
        if (next == null || d == null) return
        if (next.type.fixed) {
            // 방지턱·카메라·보호구역: 300m 앞에서 한 번, 가볍게
            if (d <= 300 && alerted.add("${next.id}:300")) {
                say("300m 앞 ${next.type.label}", listOf("sfx_pop", "d300", next.type.clip), kind = TmiKind.LOCAL, speech = "near300_${next.type.name.lowercase()}",
                    text = "300m 앞 ${next.type.label}!")
            }
            return
        }
        if (d <= 500 && alerted.add("${next.id}:500")) {
            _fx.tryEmit(Fx.Danger(next))
            val clips = mutableListOf("sfx_zing", "d500")
            next.lane?.let { clips += "l$it" }
            clips += next.type.clip
            clips += next.type.advice
            say("500m 앞 ${laneText(next.lane)}${next.type.label}", clips, urgent = true, kind = TmiKind.DANGER,
                speech = "near500_${next.type.name.lowercase()}_${next.lane ?: 0}",
                text = "500m 앞 ${laneText(next.lane)}${next.type.label} · 제보 ${next.reports}건\n" +
                    "${clockText(next.reportedAt)} 제보 · ${agoText(next.reportedAt)} · ${next.sharedTo}대 공유")
        }
        if (d <= 100 && alerted.add("${next.id}:100")) {
            say("잠시 후 ${next.type.label}", listOf("d100", next.type.clip), urgent = true, kind = TmiKind.DANGER, speech = "near100_${next.type.name.lowercase()}",
                text = "잠시 후 ${laneText(next.lane)}${next.type.label}")
        }
    }

    private fun passing(pos: Double, now: Long) {
        _ui.value.verify?.let { if (now > it.untilMillis) _ui.update { u -> u.copy(verify = null) } }
        val justPassed = _ui.value.hazards.firstOrNull { it.atM < pos - 30 && it.id !in passed }
        if (justPassed != null) {
            passed += justPassed.id
            if (justPassed.source != Source.MINE && justPassed.source != Source.NAVI && !justPassed.type.fixed) {
                _ui.update { it.copy(verify = VerifyAsk(justPassed, now + 12_000)) }
                say("방금 지난 위험, 아직 있나요?", listOf("verify_ask"), kind = TmiKind.SYSTEM, speech = "verify_${justPassed.type.name.lowercase()}",
                    text = "방금 지난 ${justPassed.type.label}, 아직 있나요?")
            }
        }
    }

    private fun peaceful(pos: Double, now: Long) {
        if (!_ui.value.on || !(car.moving || _ui.value.naviMoving) || voice.speaking.value) return
        if (now - lastLineAt < peacefulGapMs) return
        val near = _ui.value.hazards.any { it.atM - pos in 0.0..1500.0 && it.id !in passed }
        if (near || _ui.value.verify != null) return
        val l = fleet.localPool[localIndex % fleet.localPool.size]
        localIndex++
        say(l.text, l.clips, kind = l.kind, text = l.text)
    }

    // ───────────────────────── 시연 준비 ─────────────────────────

    /** 시나리오를 처음부터 틀 때: 길 위치·위험·기억 초기화 (보상은 유지) */
    fun resetTrip(hazards: List<Hazard>) {
        alerted.clear()
        passed.clear()
        speeds.clear()
        drivenSinceParkM = 0.0
        briefedThisTrip = false
        greeted = false
        lastRouteName = null
        navi = NaviState()
        localIndex = 1
        lastLineAt = SystemClock.elapsedRealtime()
        _ui.update {
            // 내 제보는 시동이 꺼질 때까지 남는다 — 새 주행은 0m에서 시작하니 출발 자리에 둔다
            it.copy(posM = 0.0, hazards = hazards, approach = null, verify = null, myReport = null, mine = it.mine.map { m -> m.copy(atM = 0.0) }, feed = emptyList(),
                heard = null, parkedSummary = false, lastReportLatencyMs = null)
        }
    }

    fun dismissSummary() = _ui.update { it.copy(parkedSummary = false) }

    fun remainingM(): Int = navi.remainM?.let { (it - (_ui.value.posM - naviBaseM)).roundToInt().coerceAtLeast(0) } ?: 0

    // ───────────────────────── 말하기·보상 ─────────────────────────

    /** speech = 미리 만든 말소리 이름(say_<이름>.wav). 있으면 울음 뒤에 말로도 안내, 없으면 울음만 */
    private fun say(spoken: String, clips: List<String>, urgent: Boolean = false, kind: TmiKind = TmiKind.SYSTEM, text: String = spoken, speech: String? = null) {
        line(TmiLine(kind, text, clips), speak = true, urgent = urgent, spokenText = spoken, speech = speech)
    }

    private fun line(l: TmiLine, speak: Boolean = true, urgent: Boolean = false, spokenText: String = l.text, speech: String? = null) {
        lastLineAt = SystemClock.elapsedRealtime()
        _ui.update { it.copy(feed = (listOf(l) + it.feed).take(20)) }
        // 말풍선이 뽁 나오는 소리 (효과음이 이미 붙은 줄은 그대로)
        val clips = if (l.clips.firstOrNull()?.startsWith("sfx_") == true) l.clips else listOf("sfx_pop") + l.clips
        if (speak && _ui.value.on) voice.say(spokenText, clips, urgent, happy = l.kind == TmiKind.MINE, speech = speech)
    }

    /** 상점에서 코인 쓰기. 모자라면 false */
    fun spendCoins(n: Int): Boolean {
        val r = _ui.value.rewards
        if (r.coins < n) return false
        val after = r.copy(coins = r.coins - n)
        _ui.update { it.copy(rewards = after) }
        prefs.edit().putInt("coins", after.coins).apply()
        return true
    }

    /** 시연용 코인 받기 (PT에서 상점 보여 줄 때) */
    fun grantCoins(n: Int) = addCoins(n)

    /** 펫 말풍선 한 줄 (상점 안내 등) — 기쁜 일이면 기쁜 울음 */
    fun notice(text: String, happy: Boolean = false) =
        say(text, emptyList(), kind = if (happy) TmiKind.MINE else TmiKind.SYSTEM, text = text)

    private fun addCoins(n: Int, helped: Int = 0, reports: Int = 0) {
        val before = _ui.value.rewards
        val after = before.copy(coins = before.coins + n, helpedDrivers = before.helpedDrivers + helped, reportsToday = before.reportsToday + reports)
        _ui.update { it.copy(rewards = after) }
        if (n > 0) {
            _fx.tryEmit(Fx.Coins(n))
            if (_ui.value.on) voice.say("", listOf("sfx_coin"), cry = false)
        }
        prefs.edit().putInt("coins", after.coins).putInt("helped", after.helpedDrivers).putInt("reports", after.reportsToday).apply()
        if (after.level > before.level) {
            scope.launch {
                delay(2500)
                _fx.tryEmit(Fx.LevelUp(after.level, after.title))
                say("레벨이 올랐습니다.", listOf("sfx_levelup", "levelup"), kind = TmiKind.MINE, text = "레벨 업! ${petName}${josa(petName, "가", "이")} 자랐어요 · ${after.level}단계 ${after.title}")
            }
        }
    }

    private fun loadRewards() = Rewards(
        coins = prefs.getInt("coins", 0),
        helpedDrivers = prefs.getInt("helped", 0),
        reportsToday = prefs.getInt("reports", 0),
    )

    fun resetRewards() {
        prefs.edit().clear().apply()
        _ui.update { it.copy(rewards = Rewards()) }
    }

    companion object {
        /** 목적지가 없을 때: 진행 방향 앞 2km 안 */
        const val AROUND_M = 2000.0
        /** 목적지 도착 보너스 코인 */
        const val ARRIVAL_COINS = 30
        /** 내 제보를 확인해 준 차 1대당 코인 */
        const val COINS_PER_CONFIRM = 5
    }
}

/** 받침 있으면 b, 없으면 a ("티미예요" / "호랑이에요") */
fun josa(word: String, a: String, b: String): String {
    val ch = word.lastOrNull() ?: return a
    if (ch !in '가'..'힣') return a
    return if ((ch - '가') % 28 != 0) b else a
}
