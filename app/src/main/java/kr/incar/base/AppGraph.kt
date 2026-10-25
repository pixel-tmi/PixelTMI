package kr.incar.base

import android.app.Application
import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.HandlerThread
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kr.incar.base.car.CarSource
import kr.incar.base.car.CarState
import kr.incar.base.car.DemoCarSource
import kr.incar.base.car.PleosCarSource
import kr.incar.base.car.Scenario
import kr.incar.base.car.SourceStatus
import kr.incar.base.nav.MapAppNaviSource
import kr.incar.base.nav.PleosNaviSource
import kr.incar.base.pet.Catalog
import kr.incar.base.pet.PetChar
import kr.incar.base.pet.PetOverlay
import kr.incar.base.pet.PetScale
import kotlinx.coroutines.flow.map
import kr.incar.base.rules.AssistantEvent
import kr.incar.base.rules.RuleEngine
import kr.incar.base.rules.SampleRules
import kr.incar.base.tmi.CommuteDemo
import kr.incar.base.tmi.FleetSimulator
import kr.incar.base.tmi.NaviState
import kr.incar.base.tmi.TmiEngine
import kr.incar.base.voice.Listener
import kr.incar.base.voice.Voice

enum class Mode(val label: String) { LIVE("실제 차량 데이터"), DEMO("시연 시나리오") }

/**
 * Pixel TMI의 몸통 — 앱 화면이 아니라 앱(프로세스) 전체에 붙어 있다.
 * 앱 화면을 닫아도 티미(바탕화면 펫)와 TMI 엔진은 계속 돈다. App.onCreate에서 한 번 만든다.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class AppGraph(private val app: Application) {

    private val viewModelScope = MainScope()
    /** 차량·내비 SDK 연결 전용 일꾼 — SDK 구독이 한 번에 수 초씩 걸려서 화면(펫) 쪽 줄을 막지 않게 따로 돌린다 */
    private val sdkThread = HandlerThread("Pixel TMI-sdk").apply { start() }
    private val sdk = Handler(sdkThread.looper)

    val voice = Voice(app)
    val live = PleosCarSource(app, viewModelScope)
    val demo = DemoCarSource(viewModelScope)
    val navi = PleosNaviSource(app, viewModelScope)
    /** 갤럭시 탭: 네이버 지도·카카오맵·티맵 길안내 (목적지 → 깃발). Pleos 차량에선 차량 내비(현대·기아)가 먼저 */
    val maps = MapAppNaviSource(app, viewModelScope)
    private val front = kr.incar.base.nav.ForegroundWatcher(app)
    /** 탭 Pleos 전용 앱 화면이 보이는 중 (StageActivity가 알려 준다) */
    @Volatile var stageVisible = false
    /** 탭 'TMI 지도' 모드 — 길안내 앱 위에서만 고양이 */
    @Volatile var mapMode = false

    /** 'TMI 지도' 아이콘: 상주 시작 + 고른 길안내 앱 열기 */
    fun startMapMode() {
        (app as App).setOn(true)
        mapMode = true
        voice.suspended = false
        kr.incar.base.pet.PetService.start(app)
        if (_mode.value != Mode.LIVE) setMode(Mode.LIVE)
        if (!maps.showMap(false)) {
            mapMode = false
            engine.notice("${maps.app.label}${kr.incar.base.tmi.josa(maps.app.label, "가", "이")} 이 탭에 없어요" + "\n" + "설정에서 다른 지도 앱을 골라 주세요")
        }
    }

    /** 차가 아닌 기기(갤럭시 탭) — Pleos 전용 앱 화면 안에서만 */
    val tablet: Boolean get() = !kr.incar.base.car.CarSpeedSource.available
    val fleet = FleetSimulator(viewModelScope)
    val engine = TmiEngine(viewModelScope, voice, fleet, app.getSharedPreferences("Pixel TMI", Context.MODE_PRIVATE))
    val listener = Listener(app) { text -> engine.onUtterance(text) }.also { l ->
        l.quietStart = { stageVisible && !pet.isOverApps }   // 우리 화면일 때만 (길안내 앱 위에선 그 앱 음성을 건드리지 않는다)
    }
    private val _demoNavi = MutableStateFlow(NaviState())
    private val commute = CommuteDemo(demo, engine, fleet) { _demoNavi.value = it }

    private val _mode = MutableStateFlow(Mode.LIVE)
    val mode: StateFlow<Mode> = _mode.asStateFlow()

    private val _signals = MutableStateFlow(false)
    /** true면 "차량 신호" 점검 화면 */
    val signalsScreen: StateFlow<Boolean> = _signals.asStateFlow()

    private val _scale = MutableStateFlow(1.0)
    val scale: StateFlow<Double> = _scale.asStateFlow()

    private fun source(m: Mode): CarSource = if (m == Mode.LIVE) live else demo

    val state: StateFlow<CarState> = _mode
        .flatMapLatest { source(it).state }
        .stateIn(viewModelScope, SharingStarted.Eagerly, CarState())

    val status: StateFlow<SourceStatus> = _mode
        .flatMapLatest { source(it).status }
        .stateIn(viewModelScope, SharingStarted.Eagerly, SourceStatus(false, "연결 중"))

    /** 실제 내비: Pleos 내비에 경로가 있으면 그것, 없으면 네이버 지도(탭) */
    private val liveNavi: StateFlow<NaviState> = combine(navi.state, maps.state) { p, n -> if (p.hasRoute || !n.hasRoute) p else n }
        .stateIn(viewModelScope, SharingStarted.Eagerly, NaviState())

    /** 화면에 보여줄 내비 상태 — 실차면 실제 내비, 시연이면 시나리오가 넣은 값 */
    val naviView: StateFlow<NaviState> = combine(_mode, liveNavi, _demoNavi) { m, real, fake -> if (m == Mode.LIVE) real else fake }
        .stateIn(viewModelScope, SharingStarted.Eagerly, NaviState())

    /** 바탕화면 펫 — 목적지 깃발 글자 */
    private val destLabel: StateFlow<String?> = combine(naviView, engine.ui) { n, ui ->
        when {
            !n.hasRoute -> null
            ui.parkedSummary -> "${n.destinationName} 도착"
            else -> "${n.destinationName} ${"%.1f".format(engine.remainingM() / 1000.0)}km"   // 달리는 만큼 줄어든다
        }
    }.distinctUntilChanged().stateIn(viewModelScope, SharingStarted.Eagerly, null)
    private val prefs = app.getSharedPreferences("Pixel TMI_pet", Context.MODE_PRIVATE)

    /** 캐릭터: 기본 4종 무료 + 상점 (외관은 코인, 특별 캐릭터는 코인 또는 유료) */
    private val _character = MutableStateFlow(Catalog.get(prefs.getString("character", "cat") ?: "cat").id)
    val character: StateFlow<String> = _character.asStateFlow()
    private val owned: MutableSet<String> = (prefs.getStringSet("owned", null) ?: emptySet()).toMutableSet()
    private fun owns(c: PetChar) = c.free || c.id in owned
    fun ownsCharacter(c: PetChar) = owns(c)

    /** 배경 테마 (사계절 자동 · 벚꽃길 · 여름 바다 · 조선시대 · 공룡시대 · 우주 · 할로윈) */
    private val _theme = MutableStateFlow(kr.incar.base.pet.Themes.get(prefs.getString("theme", "auto") ?: "auto").id)
    val theme: StateFlow<String> = _theme.asStateFlow()
    fun ownsTheme(t: kr.incar.base.pet.Theme) = t.free || "bg_${t.id}" in owned

    /** 기상청 예보 (GPS 위치 기준 오늘 날씨) */
    val weather = kr.incar.base.tmi.WeatherSource(app, viewModelScope)

    /** 선택 화면에서 캐릭터를 골랐을 때 → 큰 글자로 보여 줄 한마디 */
    fun buyOrPick(c: PetChar): String = when {
        c.id == _character.value -> "함께하는 중!"
        owns(c) -> { pick(c); "선택!" }
        c.collab -> "곧 공개돼요"
        engine.spendCoins(c.coins) -> {
            owned += c.id
            prefs.edit().putStringSet("owned", owned.toSet()).apply()
            pick(c)
            "열었어요!"
        }
        else -> "코인이 모자라요"
    }

    fun buyOrPickTheme(t: kr.incar.base.pet.Theme): String {
        fun use() { _theme.value = t.id; prefs.edit().putString("theme", t.id).apply() }
        return when {
            t.id == _theme.value -> "쓰는 중!"
            ownsTheme(t) -> { use(); "선택!" }
            engine.spendCoins(t.coins) -> {
                owned += "bg_${t.id}"
                prefs.edit().putStringSet("owned", owned.toSet()).apply()
                use(); "열었어요!"
            }
            else -> "코인이 모자라요"
        }
    }

    /** 캐릭터·배경 고르기 (킹오파식 선택 화면) — 정차 중에만 */
    fun openShop(startTab: Int = 0) {
        pet.closeSettings()
        val s = state.value
        if (isMoving()) { engine.notice((if (startTab == 2) "내 기록 보기는" else "캐릭터 고르기는") + " 정차 중에만 돼요" + "\n" + "P단에서 다시 눌러 주세요"); return }
        pet.openShop(::ownsCharacter, ::ownsTheme, { _theme.value }, ::buyOrPick, ::buyOrPickTheme, startTab)
    }

    private fun pick(c: PetChar) {
        _character.value = c.id
        prefs.edit().putString("character", c.id).apply()
    }

    /** 상점 한 칸을 눌렀을 때 */
    private fun shopTap(c: PetChar) {
        when {
            owns(c) -> pick(c)
            c.collab -> engine.notice("콜라보 에디션 자리예요\n곧 공개돼요")
            engine.spendCoins(c.coins) -> {
                owned += c.id
                prefs.edit().putStringSet("owned", owned.toSet()).apply()
                pick(c)
                engine.notice("${c.name} 열었어요!\n-${"%,d".format(c.coins)}코인", happy = true)
            }
            else -> engine.notice("코인이 모자라요 (${"%,d".format(engine.ui.value.rewards.coins)} / ${"%,d".format(c.coins)})" +
                (c.won?.let { "\n유료 ₩${"%,d".format(it)} 결제는 출시 후에 열려요" } ?: ""))
        }
    }

    /** 탭 'Pleos 전용 앱' 화면 열기 */
    /** 차가 움직이는 중 (P가 아니거나 시속 3km 넘게) — 입력·상점·설정 대부분은 정차 중에만 */
    fun isMoving(): Boolean {
        val s = state.value
        return (s.gear != null && s.gear != kr.incar.base.car.Gear.P) || (s.speedKmh ?: 0f) > 3f
    }

    fun openStage() {
        app.startActivity(Intent(app, StageActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    /** 목적지·이름 입력 창 */
    fun openInput(mode: String) {
        pet.closeSettings()
        if (isMoving()) { engine.notice("주행 중엔 글자 입력이 안 돼요" + "\n" + "말로 해 주세요: \"TMI, 잠실역 가자\""); return }
        app.startActivity(Intent(app, InputActivity::class.java).putExtra("mode", mode).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    /** 네이버 지도 길안내 시작 (글자·말 둘 다 여기로). 실제 주행(GPS)으로 바꾸고 깃발을 세운다 */
    fun navigateTo(place: String) {
        if (_mode.value != Mode.LIVE) setMode(Mode.LIVE)
        engine.notice("'$place' 찾는 중…")
        if (!tablet) {
            // 차: 현대·기아 차량 내비가 먼저 — 위치를 찾아 차량 내비에 목적지를 넣는다
            viewModelScope.launch {
                val d = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) { maps.lookup(place) }
                engine.notice(when {
                    d == null -> "'$place' 위치를 못 찾았어요" + "\n" + "차량 내비에서 직접 골라 주세요"
                    navi.routeTo(d.name, d.lat, d.lng) -> "${d.name}까지 차량 내비 길안내"
                    else -> "차량 내비에 목적지를 못 넣었어요"
                })
            }
            return
        }
        maps.navigate(place, adjacent = PetScale.stage) { msg -> engine.notice(msg) }
    }

    /** 펫 이름 바꾸기 */
    fun setPetName(name: String) {
        val n = name.trim().take(8).ifEmpty { "티미" }
        engine.petName = n
        kr.incar.base.tmi.VoiceCommand.petName = n
        prefs.edit().putString("pet_name", n).apply()
        engine.notice("이제 제 이름은 ${n}${kr.incar.base.tmi.josa(n, "예요", "이에요")}!", happy = true)
    }

    /** 종료: 펫·상주 알림·음성 듣기·GPS를 모두 멈추고 앱을 닫는다 (다시 켜려면 앱 아이콘) */
    fun quit(closeStage: Boolean = true) {
        (app as App).setOn(false)          // 다시 깨워져도 아무것도 안 돌게
        pet.closeSettings()
        mapMode = false
        voice.suspended = true
        voice.stop()
        listener.pause()
        if (closeStage && stageVisible) app.startActivity(Intent(app, StageActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK).putExtra("close", true))
        app.stopService(Intent(app, kr.incar.base.pet.PetService::class.java))
        runCatching { maps.cancel() }
        shutdown()
        Handler(android.os.Looper.getMainLooper()).postDelayed({ android.os.Process.killProcess(android.os.Process.myPid()) }, 500)
    }

    /** 점검용: 캐릭터 바로 바꾸기 (am start ... --es char ufo) */
    fun selectCharacterForCheck(id: String) = pick(Catalog.get(id))

    private var menu = "main"
    private fun openMenu(m: String) {
        menu = m
        pet.reopenSettings()
    }

    private val actions: kr.incar.base.pet.PetActions = object : kr.incar.base.pet.PetActions {
        override fun talk() = this@AppGraph.talk()
        override fun locate() {
            pet.callHome()
            engine.briefing()
        }
        override fun settingsRows(): List<Pair<String, () -> Unit>> = if (isMoving() && menu == "main") listOf(
            "주행 중엔 꼭 필요한 것만 보여요" to { },
            (if (engine.ui.value.on) "TMI 알림  ● 켜짐" else "TMI 알림  ○ 꺼짐") to { engine.setOn(!engine.ui.value.on); openMenu("main") },
            (if (voice.muted) "소리  ○ 꺼짐" else "소리  ● 켜짐") to { voice.muted = !voice.muted; pet.refreshVolume(); openMenu("main") },
            (if (System.currentTimeMillis() - quitArmedAt < 3000) "■ 한 번 더 누르면 꺼져요" else "■ 종료 (앱 끄기)") to {
                if (System.currentTimeMillis() - quitArmedAt < 3000) quit() else { quitArmedAt = System.currentTimeMillis(); openMenu("main") }
            },
            "닫기" to { pet.closeSettings() },
        ) else when (menu) {
            "shop" -> shopRows()
            "sound" -> back() + listOf(
                (if (voice.muted) "소리  ○ 꺼짐" else "소리  ● 켜짐") to { voice.muted = !voice.muted; pet.refreshVolume(); openMenu("sound") },
                "소리 크기  ${(voice.volume * 100).toInt()}%" to {
                    voice.volume = when { voice.volume > 0.85f -> 0.7f; voice.volume > 0.55f -> 0.4f; else -> 1f }
                    pet.refreshVolume(); openMenu("sound")
                },
                (if (listener.continuous) "항상 듣기 (말만 하면 제보)  ●" else "항상 듣기 (말만 하면 제보)  ○") to { listener.continuous = !listener.continuous; openMenu("sound") },
            )
            "pet" -> back() + listOf(
                "캐릭터 · 배경 고르기  ${Catalog.get(_character.value).name} ▸" to { openShop() },
                "펫 이름  ${engine.petName} ▸" to { openInput("name") },
            )
            "drive" -> back() + listOf(
                "▶ 출근길 시연" to { pet.closeSettings(); startCommuteDemo() },
                (if (tablet) "실제 주행 (내 위치)" else "실차 연결") to { pet.closeSettings(); setMode(Mode.LIVE) },
                "공유 기준  같은 곳 ${engine.requiredReports}건${if (engine.demoMode) " (시연은 1건)" else ""}" to {
                    engine.requiredReports = engine.requiredReports % 3 + 1
                    prefs.edit().putInt("required_reports", engine.requiredReports).apply()
                    openMenu("drive")
                },
            )
            "buttons" -> back() + listOf(
                (if (pet.buttonsLocked) "버튼 위치  고정됨" else "버튼 위치  꾹 눌러 옮길 수 있음") to { pet.buttonsLocked = !pet.buttonsLocked; openMenu("buttons") },
                "버튼 자리 처음으로" to { pet.resetButtons(); openMenu("buttons") },
            )
            else -> listOf(
                (if (engine.ui.value.on) "TMI 알림  ● 켜짐" else "TMI 알림  ○ 꺼짐") to { engine.setOn(!engine.ui.value.on); openMenu("main") },
                *(if (tablet) arrayOf<Pair<String, () -> Unit>>(
                    (naviView.value.takeIf { maps.active }?.destinationName?.let { "길안내  $it ▸" } ?: "길안내  ${maps.app.label} ▸") to { openInput("dest") },
                ) else emptyArray()),
                *(if (tablet && !stageVisible) arrayOf<Pair<String, () -> Unit>>(
                    "플레오스 화면으로 ▸" to { pet.closeSettings(); openStage() },
                ) else emptyArray()),
                "소리 · 음성  ${if (voice.muted) "꺼짐" else "${(voice.volume * 100).toInt()}%"} ▸" to { openMenu("sound") },
                "캐릭터  ${Catalog.get(_character.value).name} · ${engine.petName} ▸" to { openMenu("pet") },
                "내 제보 기록  ${engine.ui.value.history.size}건 ▸" to { openShop(2) },
                "시연 · 주행  ${if (mode.value == Mode.DEMO) "출근길 시연 중" else "실제 주행"} ▸" to { openMenu("drive") },
                "버튼  ${if (pet.buttonsLocked) "고정됨" else "옮길 수 있음"} ▸" to { openMenu("buttons") },
                (if (System.currentTimeMillis() - quitArmedAt < 3000) "■ 한 번 더 누르면 꺼져요" else "■ 종료 (앱 끄기)") to {
                    if (System.currentTimeMillis() - quitArmedAt < 3000) quit() else {
                        quitArmedAt = System.currentTimeMillis(); openMenu("main")
                        android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({ if (menu == "main") openMenu("main") }, 3100)
                    }
                },
                "닫기" to { pet.closeSettings() },
            )
        }

        private fun back(): List<Pair<String, () -> Unit>> = listOf("◀ 뒤로" to { openMenu("main") })
        private var quitArmedAt = 0L

        override fun settingsOpened() { menu = "main" }

        private fun shopRows(): List<Pair<String, () -> Unit>> =
            listOf<Pair<String, () -> Unit>>("◀ 뒤로 · 코인 ${"%,d".format(engine.ui.value.rewards.coins)}" to { openMenu("pet") }) +
                Catalog.all.map { c ->
                    val tag = when {
                        c.id == _character.value -> "● 사용 중"
                        owns(c) -> "고르기"
                        c.collab -> "준비 중"
                        else -> "${"%,d".format(c.coins)}코인" + (c.won?.let { " · ₩${"%,d".format(it)}" } ?: "")
                    }
                    "${c.name}  $tag" to { shopTap(c) }
                } +
                listOf<Pair<String, () -> Unit>>("시연용 코인 +5,000" to { engine.grantCoins(5000) })
    }

    val pet: PetOverlay = PetOverlay(app, viewModelScope, engine, voice, state, destLabel, listener.listening, character, actions, theme, weather.state)

    /** 설정·시연 패널(앱 화면) 열기 — 티미 버튼을 길게 누르면 */
    fun openPanel() {
        app.startActivity(Intent(app, MainActivity::class.java).putExtra("panel", true).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    /** 펫 켜기/끄기. 권한이 없으면 false */
    fun togglePet(): Boolean = if (pet.shown.value) { pet.hide(); true } else pet.show()

    // "차량 신호" 화면용 기존 규칙 엔진 (소리는 내지 않고 목록만)
    private val rules = RuleEngine(SampleRules.all)
    private val _events = MutableStateFlow<List<AssistantEvent>>(emptyList())
    val events: StateFlow<List<AssistantEvent>> = _events.asStateFlow()

    init {
        engine.requiredReports = prefs.getInt("required_reports", 2)
        engine.petName = prefs.getString("pet_name", "티미") ?: "티미"
        kr.incar.base.tmi.VoiceCommand.petName = engine.petName
        engine.onNavigate = { place -> navigateTo(place) }
        engine.weatherLine = { weather.state.value.takeIf { it.ok }?.line() }
        weather.start()
        maps.onArrived = { engine.markArrived(); live.arrived() }
        engine.allowNaviSim = !tablet
        viewModelScope.launch { navi.arrivals.collect { engine.markArrived() } }
        engine.onToggle = { on -> if (on) listener.resume() else listener.pause() }
        listener.onGaveUp = { engine.notice("음성 인식이 잠깐 쉬어요" + "\n" + "마이크 버튼을 누르면 다시 들어요") }
        maps.simulating = { live.simulating }
        engine.demoNow = { _mode.value == Mode.DEMO || live.simulating }
        // 모의 주행은 시간을 빨리 감는다 (12km 경로도 2~3분에) — 진짜 주행·GPS는 그대로
        viewModelScope.launch {
            state.collect { if (tablet && _mode.value == Mode.LIVE) engine.timeScale = if (live.simulating) SIM_FAST else _scale.value }
        }
        // 모의 주행으로 남은 거리가 다 줄면 = 도착 (주차 → 세레모니)
        viewModelScope.launch {
            engine.ui.collect { if (tablet && maps.active && live.simulating && engine.remainingM() <= 15) maps.arriveBySim() }
        }
        engine.start()
        rules.attach(viewModelScope, state)
        viewModelScope.launch {
            rules.events.collect { e ->
                _events.value = (listOf(e) + _events.value).take(30)
                // 탭 Pleos 화면에서 문·와이퍼·창문을 건드리면 코파일럿 안내도 고양이 말풍선으로 (차량 상태 연동)
                if (tablet && e.ruleId in TABLET_RULES) engine.notice(e.message)
            }
        }
        viewModelScope.launch { state.collect { engine.onCar(it) } }
        viewModelScope.launch { liveNavi.collect { if (_mode.value == Mode.LIVE) engine.onNavi(it) } }
        viewModelScope.launch { listener.listening.collect { engine.setListening(it) } }
        viewModelScope.launch { character.collect { voice.character = it } }
        viewModelScope.launch { engine.ui.collect { pet.refreshVolume() } }
        // 탭: 우리가 띄운 길안내 앱이 앞에 오면 고양이도 지도 위로 따라 나오고, 홈·다른 앱이면 숨는다
        if (tablet) viewModelScope.launch {
            while (true) {
                delay(1200)
                if (stageVisible) continue
                val granted = front.granted()
                val pkg = if (granted) kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.Default) { front.current() } else null
                if (pkg == app.packageName) continue                           // 우리 입력 창 등 — 그대로 둔다
                val wanted = mapMode || maps.active                             // 'TMI 지도' 모드거나 Pleos 앱에서 길안내를 넘긴 경우
                val mapFront = if (granted) wanted && kr.incar.base.nav.MapApp.of(pkg) != null
                else wanted && (mapMode || maps.justOpened())                   // 사용 정보 접근이 없으면 대충
                if (mapFront && !pet.isOverApps) {
                    if (pet.showOverApps()) { voice.suspended = false; listener.resume() }
                } else if (!mapFront && pet.isOverApps && granted) {
                    pet.hide()
                    voice.suspended = true
                    voice.stop()
                    listener.pause()
                } else if (!mapFront && !pet.isOverApps && !listener.paused) {
                    listener.pause()             // 앱 밖(홈·다른 앱)에선 마이크도 쉰다
                    voice.suspended = true
                }
            }
        }
        // 차에 타면: 내 주변 TMI
        engine.resetTrip(fleet.seedCommute(0.0))
        viewModelScope.launch {
            // 펫부터 띄우고, 무거운 연결(차량·내비·음성 인식)은 한 번에 하나씩 → 메인 스레드가 오래 막히지 않게
            if (!tablet) voice.suspended = false                       // 차: 늘 화면 위에 있으니 바로 소리
            if (pet.show()) kr.incar.base.pet.PetService.start(app)   // 탭은 Pleos 전용 앱 화면이 열릴 때 붙는다
            delay(600); sdk.post { live.start() }
            delay(400); if (!tablet) sdk.post { navi.start() }   // 탭엔 차량 내비 서비스가 없다 (헛된 재연결 방지)
            delay(400)
            if (tablet && !stageVisible && !pet.isOverApps) listener.pause()   // 탭: 화면이 보일 때만 듣는다
            listener.start()
            delay(2000)
            engine.briefing()
        }
    }

    fun setMode(m: Mode) {
        if (m == Mode.LIVE) {
            demo.stop()
            engine.demoMode = false
            _mode.value = Mode.LIVE
            engine.timeScale = _scale.value
            engine.peacefulGapMs = 60_000
            reseed()
            engine.onNavi(liveNavi.value)
        } else {
            _mode.value = Mode.DEMO
        }
    }

    fun startCommuteDemo() {
        _mode.value = Mode.DEMO
        _signals.value = false
        _demoNavi.value = NaviState()
        commute.play()
    }

    fun reseed() {
        engine.resetTrip(fleet.seedCommute(engine.ui.value.posM))
    }

    fun cycleScale() {
        _scale.value = if (_scale.value >= 4.0) 1.0 else 4.0
        engine.timeScale = _scale.value
    }

    /** 말하기 버튼: Pleos 음성 인식이 되면 듣고, 안 되면 안내 후 버튼으로 */
    fun talk() {
        listener.resume()
        if (!listener.listen()) {
            engine.setListening(false)
            engine.notice("음성 인식 준비 중이에요" + "\n" + "잠시 뒤 다시 눌러 주세요")
        }
    }

    /** 정산 화면은 다음 출발 때 자동으로 닫히지만, 눌러서 먼저 닫을 수도 있다 */
    fun closeSummary() = engine.dismissSummary()

    fun showSignals(on: Boolean) { _signals.value = on }

    // ── "차량 신호" 화면 호환 ──
    fun play(scenario: Scenario) {
        _mode.value = Mode.DEMO
        demo.play(scenario)
    }

    fun stopScenario() = demo.stop()

    fun testVoice() = voice.say("픽셀 TMI가 전방 도로를 살피고 있습니다.", listOf("start"))

    fun shutdown() {
        pet.hide()
        live.stop()
        demo.stop()
        if (!tablet) navi.stop()
        listener.release()
        voice.shutdown()
        sdkThread.quitSafely()
        viewModelScope.cancel()
    }
}

/** 모의 주행 빨리 감기 배수 */
private const val SIM_FAST = 6.0

/** 탭 Pleos 화면 조작에 반응해 말풍선으로 띄울 코파일럿 안내 */
private val TABLET_RULES = setOf("door_moving", "rain_lights", "window_parked", "belt")

/** 화면 코드가 쓰던 이름 그대로 */
typealias AppViewModel = AppGraph
