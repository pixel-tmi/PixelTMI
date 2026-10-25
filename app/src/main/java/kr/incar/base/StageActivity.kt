package kr.incar.base

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.os.Bundle
import android.view.MotionEvent
import android.view.View
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.widget.FrameLayout
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import kr.incar.base.car.CarState
import kr.incar.base.car.Gear
import kr.incar.base.pet.PetScale
import kr.incar.base.pet.PetService
import kr.incar.base.tmi.NaviState
import kotlin.math.abs
import kotlin.math.min

/**
 * 갤럭시 탭 'Pleos 전용 앱' — 실제 Pleos 메인 화면(에뮬레이터에서 찍은 그림)을 탭 전체에 깔고,
 * 펫·버튼·말풍선을 이 화면 안에만 띄운다 (앱 밖 탭 화면엔 아무것도 안 뜬다).
 * 주차면 주차 화면, 달리면 주행 화면(실제 속도 숫자)으로 바꿔 끼고,
 * 가운데 내비 자리는 길안내 카드(목적지·남은 거리·시간)로 바꾼다.
 * 그림 속 버튼도 실제처럼 눌린다: P·R·N·D, 와이퍼·전조등·문·창문, 온도 ▲▼, 아래 바 내비·앱 목록 → 가상 차량 → TMI 연동.
 */
class StageActivity : ComponentActivity() {

    private val vm: AppGraph get() = (application as App).graph
    private lateinit var root: FrameLayout
    private lateinit var stage: StageView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (intent.getBooleanExtra("close", false)) { finish(); return }
        root = FrameLayout(this)
        stage = StageView(this, vm) { attachPet() }
        root.addView(stage, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT))
        setContentView(root)
        onBackPressedDispatcher.addCallback(this, object : androidx.activity.OnBackPressedCallback(true) {
            private var lastBack = 0L
            override fun handleOnBackPressed() {
                when {
                    vm.pet.settingsOpen -> vm.pet.closeSettings()
                    stage.closePopups() -> Unit
                    android.os.SystemClock.uptimeMillis() - lastBack < 2000 -> finish()
                    else -> {
                        lastBack = android.os.SystemClock.uptimeMillis()
                        android.widget.Toast.makeText(this@StageActivity, "한 번 더 누르면 꺼져요", android.widget.Toast.LENGTH_SHORT).show()
                    }
                }
            }
        })
        lifecycleScope.launch {
            combine(vm.state, vm.engine.ui, vm.naviView) { s, ui, n -> Triple(s, ui, n) }.collect { (s, ui, n) ->
                val kmh = maxOf(s.speedKmh ?: 0f, ui.naviSpeedKmh)
                val drivingNow = ui.naviMoving || (s.gear != null && s.gear != Gear.P) || kmh > 1f
                stage.update(drivingNow, kmh, n, s)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (intent.getBooleanExtra("close", false)) finish()   // 톱니 "종료"
    }

    override fun onStart() {
        super.onStart()
        // 탭 상태바·내비게이션바 숨기기 (밀어 올리면 잠깐 보임)
        window.insetsController?.let {
            it.hide(WindowInsets.Type.systemBars())
            it.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
        vm.stageVisible = true
        vm.voice.suspended = false
        vm.listener.resume()
        PetService.start(this)
        root.post { attachPet() }
    }

    override fun onStop() {
        super.onStop()
        vm.stageVisible = false
        vm.pet.detach(root)
        PetScale.stage = false
        PetScale.stageGroundLift = 0f
        // 우리가 방금 길안내 앱을 띄워서 가려진 거면 소리 TMI는 계속(조수석 친구처럼), 그 밖엔 앱 밖에서 조용히
        if (!(vm.maps.active && vm.maps.justOpened())) {
            vm.voice.suspended = true
            vm.voice.stop()
            vm.listener.pause()          // 듣기(와 인식 시작 '띵' 소리)도 멈춘다
        }
    }

    /** 뒤로 가기로 Pleos 전용 앱을 닫으면 소리·GPS·상주 알림까지 전부 같이 꺼진다 */
    override fun onDestroy() {
        super.onDestroy()
        if (isFinishing && !isChangingConfigurations && !quitting) vm.quit(closeStage = false)
    }

    private val quitting: Boolean get() = intent?.getBooleanExtra("close", false) == true

    /** 그림 배율이 정해지면(처음·크기 바뀜) 펫을 이 화면에 붙인다 */
    private fun attachPet() {
        if (!lifecycle.currentState.isAtLeast(androidx.lifecycle.Lifecycle.State.STARTED) || stage.width == 0) return
        val changed = !PetScale.stage || abs(PetScale.stageScale - stage.scale) > 0.001f
        PetScale.stage = true
        PetScale.stageScale = stage.scale
        PetScale.stageGroundLift = BAR_PX * stage.scale
        if (changed) vm.pet.detach(root)
        vm.pet.attach(root)
    }

    companion object {
        /** 그림(2560×1440) 속 Pleos 아래 바 높이 */
        const val BAR_PX = 140f
    }
}

/** Pleos 화면 그림 + 실시간 속도 + 가운데 내비 자리의 네이버 지도 길안내 카드 */
class StageView(context: Context, private val vm: AppGraph, private val onScale: () -> Unit) : View(context) {
    private var driving = false
    private var kmh = 0f
    private var navi = NaviState()
    private var car = CarState()
    /** 눌렀을 때 잠깐 뜨는 글자 (예: "와이퍼 켜짐") */
    private var toast: String? = null
    private var toastAt = 0L
    private var tapX = -1f
    private var tapY = -1f
    /** 아래 바 앱 목록 펼침 */
    private var appsOpen = false
    /** 가운데 내비 칸 (그린 내비) */
    private val naviMap = StageNavi { load(it) }
    private var routeName: String? = null
    private var routeTotal = 0f
    private var lastDrawAt = 0L
    private fun load(name: String): Bitmap? = runCatching { context.assets.open(name).use { BitmapFactory.decodeStream(it) } }.getOrNull()
    private val parked = load("stage/pleos_parked.png")
    private val moving = load("stage/pleos_driving.png") ?: parked
    private val paint = Paint().apply { isFilterBitmap = true }
    private val dst = RectF()
    /** 그림 배율·위치 (그림 1px → 화면 px) */
    var scale = 1f; private set
    private var ox = 0f
    private var oy = 0f
    private val bold = Typeface.create("sans-serif", Typeface.BOLD)
    private val text = Paint(Paint.ANTI_ALIAS_FLAG)
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG)
    /** 눌리는 곳 (화면 좌표) */
    private val hits = ArrayList<Pair<RectF, () -> Unit>>()

    /** 열린 앱 목록 닫기 — 닫았으면 true */
    fun closePopups(): Boolean {
        if (!appsOpen) return false
        appsOpen = false; invalidate(); return true
    }

    fun update(d: Boolean, speed: Float, n: NaviState, c: CarState) {
        val redraw = d != driving || abs(speed - kmh) >= 1f || n != navi || c.copy(speedKmh = null) != car.copy(speedKmh = null)
        driving = d; kmh = speed; navi = n; car = c
        if (redraw) invalidate()
    }

    private fun say(t: String) {
        toast = t; toastAt = android.os.SystemClock.uptimeMillis()
        invalidate()
        postDelayed({ invalidate() }, 1900)
    }

    override fun onSizeChanged(w: Int, h: Int, ow: Int, oh: Int) {
        super.onSizeChanged(w, h, ow, oh)
        val bmp = parked ?: return
        scale = min(w.toFloat() / bmp.width, h.toFloat() / bmp.height)
        ox = (w - bmp.width * scale) / 2
        oy = h - bmp.height * scale
        post { onScale() }
    }

    /** 그림 좌표 → 화면 좌표 */
    private fun X(x: Float) = ox + x * scale
    private fun Y(y: Float) = oy + y * scale

    override fun onDraw(c: Canvas) {
        c.drawColor(0xFFFFFFFF.toInt())
        val bmp = (if (driving) moving else parked) ?: return
        if (oy > 8f) {
            // 그림 위 남는 띠: 시연 화면이라는 표시 (흰 띠가 비어 보이지 않게)
            fill.color = 0xFF1B1F2A.toInt()
            c.drawRect(0f, 0f, width.toFloat(), oy, fill)
            label(c, "Pixel TMI  ·  플레오스 화면 시연", 40f * scale, oy / 2 + 14f * scale, 34f, 0xFFFFFFFF.toInt())
            label(c, if (driving) "● 주행 중" else "● 주차 중", width - 40f * scale, oy / 2 + 14f * scale, 30f,
                if (driving) 0xFF39D353.toInt() else 0xFFFFD23F.toInt(), Paint.Align.RIGHT)
        }
        dst.set(ox, oy, ox + bmp.width * scale, oy + bmp.height * scale)
        c.drawBitmap(bmp, null, dst, paint)
        hits.clear()
        // 주행 화면: 왼쪽 판 큰 속도 숫자를 실제 속도로
        if (driving) {
            text.typeface = Typeface.create("sans-serif-light", Typeface.NORMAL)
            text.textSize = 128f * scale
            text.color = 0xFF111111.toInt()
            text.textAlign = Paint.Align.CENTER
            c.drawText("${kmh.toInt()}", X(427f), Y(182f), text)
        }
        drawNaviCard(c)
        drawControls(c)
        if (appsOpen) drawApps(c)
        restHint()
        // 눌렀을 때 글자 (1.2초)
        val tt = toast
        if (tt != null && android.os.SystemClock.uptimeMillis() - toastAt < 1800) {
            text.typeface = bold; text.textSize = 34f * scale; text.textAlign = Paint.Align.CENTER
            val w = text.measureText(tt) + 60f * scale
            // 누른 자리 바로 위 (화면 밖으로 안 나가게)
            val cx = (if (tapX >= 0) tapX else X(426f)).coerceIn(w / 2 + 10f * scale, width - w / 2 - 10f * scale)
            val top = (if (tapY >= 0) tapY - 150f * scale else Y(300f)).coerceIn(Y(120f), height - 80f * scale)
            fill.color = 0xE61E1E1E.toInt()
            c.drawRoundRect(cx - w / 2, top, cx + w / 2, top + 70f * scale, 35f * scale, 35f * scale, fill)
            text.color = 0xFFFFFFFF.toInt()
            c.drawText(tt, cx, top + 47f * scale, text)
        }
    }

    // ── 그림 속 버튼: 실제 Pleos처럼 눌리고, 가상 차량(→ TMI)에 반영 ──
    private val GEAR_X = mapOf(Gear.P to 692f, Gear.R to 734f, Gear.N to 776f, Gear.D to 818f)

    private fun drawControls(c: Canvas) {
        val live = vm.live
        // 맨 위 오른쪽 시계 (그림 속 '03:31 오후'를 지금 시각으로)
        fill.color = 0xFFFFFFFF.toInt()
        c.drawRect(X(2380f), Y(14f), X(2558f), Y(76f), fill)
        val cal = java.util.Calendar.getInstance()
        val h = cal.get(java.util.Calendar.HOUR).let { if (it == 0) 12 else it }
        val ampm = if (cal.get(java.util.Calendar.AM_PM) == 0) "오전" else "오후"
        label(c, "%d:%02d %s".format(h, cal.get(java.util.Calendar.MINUTE), ampm), X(2548f), Y(57f), 30f, 0xFF1E1E1E.toInt(), Paint.Align.RIGHT)
        postInvalidateDelayed(30_000)
        // P R N D (누르면 기어)
        fill.color = 0xFFFFFFFF.toInt()
        c.drawRect(X(672f), Y(14f), X(848f), Y(76f), fill)
        val g = car.gear ?: Gear.P
        GEAR_X.forEach { (gear, gx) ->
            if (gear == g) {
                fill.color = 0xFF1E1E1E.toInt()
                c.drawRect(X(gx - 19f), Y(23f), X(gx + 19f), Y(67f), fill)
            }
            label(c, gear.label, X(gx), Y(58f), 32f, if (gear == g) 0xFFFFFFFF.toInt() else 0xFF5A5A5A.toInt(), Paint.Align.CENTER)
        }
        if (live.controllable) GEAR_X.forEach { (gear, gx) ->
            hits += RectF(X(gx - 21f), Y(0f), X(gx + 21f), Y(110f)) to {
                when {
                    vm.mode.value == Mode.DEMO -> say("출근길 시연 중엔 시연이 운전해요")
                    gear == Gear.P -> { live.setGear(Gear.P); say("P · 주차") }
                    gear == Gear.D -> { live.setGear(Gear.D); say("D · 출발!") }
                    else -> say("${gear.label}단은 실제 차에서 써요 · 시연은 P·D")
                }
            }
        }
        // 주차 화면 위쪽 '0km/h' → 지금 속도
        if (!driving) {
            fill.color = 0xFFFFFFFF.toInt()
            c.drawRect(X(360f), Y(20f), X(500f), Y(70f), fill)
            label(c, "${kmh.toInt()}km/h", X(430f), Y(58f), 30f, 0xFF1E1E1E.toInt(), Paint.Align.CENTER)
        }
        if (!live.controllable) return
        // 왼쪽 판 아이콘 줄: 문 · 전조등 · 와이퍼 · 창문
        val row2 = listOf(
            Triple(120f, car.anyDoorOpen == true, "문") to { live.toggleDoor(); say(if (car.anyDoorOpen == true) "문 닫힘" else "문 열림") },
            Triple(325f, car.headlightsOn == true, "전조등") to { live.toggleLights(); say(if (car.headlightsOn == true) "전조등 꺼짐" else "전조등 켜짐") },
            Triple(527f, car.wiperOn == true, "와이퍼") to { live.toggleWiper(); say(if (car.wiperOn == true) "와이퍼 꺼짐" else "와이퍼 켜짐 · 비") },
            Triple(727f, (car.driverWindowPercent ?: 0) > 0, "창문") to { live.toggleWindow(); say(if ((car.driverWindowPercent ?: 0) > 0) "창문 닫힘" else "창문 열림") },
        )
        row2.forEach { (info, act) ->
            val (ix, on, name) = info
            if (on) {
                fill.color = 0x332E7CF6
                c.drawRoundRect(X(ix - 70f), Y(1150f), X(ix + 70f), Y(1240f), 20f * scale, 20f * scale, fill)
                label(c, "$name 켜짐".replace("문 켜짐", "문 열림").replace("창문 켜짐", "창문 열림"), X(ix), Y(1268f), 22f, 0xFF2E7CF6.toInt(), Paint.Align.CENTER)
            }
            hits += RectF(X(ix - 90f), Y(1140f), X(ix + 90f), Y(1280f)) to act
        }
        if (!driving) {   // 주차 화면 윗줄: 창문 내리기 아이콘
            hits += RectF(X(590f), Y(975f), X(720f), Y(1070f)) to { live.toggleWindow(); say(if ((car.driverWindowPercent ?: 0) > 0) "창문 닫힘" else "창문 열림") }
        }
        // 아래 바 온도 (양쪽): ▼ ▲ + 가운데 글자
        val on = car.hvacOn == true
        val temp = car.cabinTempC ?: 22f
        for ((tx, down, up) in listOf(Triple(205f, 74f, 324f), Triple(2360f, 2236f, 2486f))) {
            fill.color = 0xFF000000.toInt()
            c.drawRect(X(tx - 88f), Y(1318f), X(tx + 88f), Y(1428f), fill)
            label(c, if (on) "%.1f°".format(temp) else "꺼짐", X(tx), Y(1384f), 44f, if (on) 0xFFFFFFFF.toInt() else 0xFF9A9A9A.toInt(), Paint.Align.CENTER)
            if (on) label(c, "냉방", X(tx), Y(1414f), 20f, 0xFF39D353.toInt(), Paint.Align.CENTER)
            hits += RectF(X(down - 45f), Y(1310f), X(down + 45f), Y(1436f)) to { live.nudgeTemp(-0.5f); say("온도 %.1f°".format(((car.cabinTempC ?: 22f) - 0.5f).coerceIn(16f, 30f))) }
            hits += RectF(X(up - 45f), Y(1310f), X(up + 45f), Y(1436f)) to { live.nudgeTemp(0.5f); say("온도 %.1f°".format(((car.cabinTempC ?: 22f) + 0.5f).coerceIn(16f, 30f))) }
            hits += RectF(X(tx - 88f), Y(1310f), X(tx + 88f), Y(1436f)) to { live.toggleHvac(); say(if (on) "공조 꺼짐" else "공조 켜짐") }
        }
        // 아래 바 가운데: 차량 · 내비 · 전화 · 앱 목록 · Pixel TMI · 카메라
        hits += RectF(X(930f), Y(1310f), X(1030f), Y(1436f)) to { say("차량 설정 · 왼쪽 차량 화면 아이콘을 눌러 보세요") }
        hits += RectF(X(1046f), Y(1310f), X(1146f), Y(1436f)) to { if (navi.hasRoute) vm.maps.showMap(true) else vm.openInput("dest") }
        hits += RectF(X(1162f), Y(1310f), X(1262f), Y(1436f)) to { say("전화 · 시연에선 쉬어요") }
        hits += RectF(X(1278f), Y(1310f), X(1378f), Y(1436f)) to { appsOpen = !appsOpen; invalidate() }
        hits += RectF(X(1412f), Y(1310f), X(1512f), Y(1436f)) to { vm.pet.toggleSettings() }
        hits += RectF(X(1528f), Y(1310f), X(1628f), Y(1436f)) to { say("카메라 · 시연에선 쉬어요") }
        hits += RectF(X(950f), Y(10f), X(1050f), Y(80f)) to { vm.openInput("dest") }          // 위쪽 돋보기 = 목적지 찾기
    }

    /** 아래 바에서 반응 없는 곳을 누르면 알려 준다 (고장처럼 보이지 않게) — 맨 마지막에 붙인다 */
    private fun restHint() {
        hits += RectF(X(0f), Y(1300f), X(2560f), Y(1440f)) to { say("이 버튼은 시연에선 쉬어요") }
        hits += RectF(X(852f), Y(0f), X(2560f), Y(110f)) to { say("이 아이콘은 시연에선 쉬어요") }
        hits += RectF(X(0f), Y(110f), X(852f), Y(1300f)) to { say("이 아이콘은 시연에선 쉬어요") }
    }

    /** 앱 목록 (아래 바 ▦): Pixel TMI · 네이버 지도 · 카카오맵 · 티맵 */
    private fun drawApps(c: Canvas) {
        val l = X(1000f); val t = Y(470f); val r = X(1720f); val b = Y(880f)   // 고양이 길(아래 띠) 위로 띄운다
        fill.color = 0xF2FFFFFF.toInt()
        c.drawRoundRect(l, t, r, b, 28f * scale, 28f * scale, fill)
        fill.style = Paint.Style.STROKE; fill.strokeWidth = 3f * scale; fill.color = 0xFF1E1E1E.toInt()
        c.drawRoundRect(l, t, r, b, 28f * scale, 28f * scale, fill)
        fill.style = Paint.Style.FILL
        label(c, "앱", l + 36f * scale, t + 62f * scale, 32f, 0xFF1E1E1E.toInt())
        val apps = listOf(
            Triple("Pixel TMI", 0xFF1E1E1E.toInt(), "T") to { appsOpen = false; vm.pet.toggleSettings() },
        ) + kr.incar.base.nav.MapApp.entries.map { a ->
            Triple(a.label, a.color, a.badge) to { appsOpen = false; vm.maps.app = a; vm.maps.showMap(true); invalidate() }
        }
        val cell = (r - l - 72f * scale) / 4
        val popup = ArrayList<Pair<RectF, () -> Unit>>()
        apps.forEachIndexed { i, (info, act) ->
            val (name, color, badge) = info
            val cx = l + 36f * scale + cell * i + cell / 2
            val cy = t + 200f * scale
            fill.color = color
            c.drawRoundRect(cx - 60f * scale, cy - 60f * scale, cx + 60f * scale, cy + 60f * scale, 26f * scale, 26f * scale, fill)
            label(c, if (i == 0) "TMI" else badge, cx, cy + 18f * scale, if (i == 0) 40f else 56f,
                if (i == 0) 0xFFFFFFFF.toInt() else kr.incar.base.nav.MapApp.entries[i - 1].badgeInk, Paint.Align.CENTER)
            label(c, name, cx, cy + 112f * scale, 26f, 0xFF1E1E1E.toInt(), Paint.Align.CENTER)
            popup += RectF(cx - cell / 2, cy - 80f * scale, cx + cell / 2, cy + 130f * scale) to act
        }
        // 펼친 목록이 맨 먼저 눌린다 (아이콘 → 목록 빈 곳은 그냥 무시), 바깥을 누르면 닫힘
        popup += RectF(l, t, r, b) to {}
        hits.addAll(0, popup)
        hits += RectF(0f, 0f, width.toFloat(), height.toFloat()) to { appsOpen = false; invalidate() }
    }

    /** 가운데 내비 칸 전체(852~2560 × 92~1300): 그린 내비 지도 + 회전 안내 + 남은 거리 + 모의 주행 */
    private fun drawNaviMap(c: Canvas): Boolean {
        val now = android.os.SystemClock.uptimeMillis()
        val dt = if (lastDrawAt == 0L) 0f else ((now - lastDrawAt) / 1000f).coerceAtMost(0.1f)
        lastDrawAt = now
        val area = RectF(X(852f), Y(92f), X(2560f), Y(1300f))
        val e = vm.engine
        if (!navi.hasRoute) {
            routeName = null; naviMap.clearRoute()
            naviMap.draw(c, area, scale, emptyList(), now)
            return false
        }
        val remain = e.remainingM().toFloat()
        val name = navi.destinationName ?: "목적지"
        if (name != routeName) { routeName = name; routeTotal = remain.coerceAtLeast(300f) }
        if (remain > routeTotal) routeTotal = remain
        naviMap.setRoute(name, routeTotal)
        naviMap.update(routeTotal - remain, kmh, dt)
        val ui = e.ui.value
        val traveled = routeTotal - remain
        val haz = ui.hazards.filter { it.type !in kr.incar.base.tmi.HazardType.DRIVING_ONLY || it.atM - ui.posM <= 1000 }
            .map { (traveled + (it.atM - ui.posM)).toFloat() to it.type }
        naviMap.draw(c, area, scale, haz, now)
        if (kmh > 0.5f) postInvalidateOnAnimation()

        // 회전 안내 (왼쪽 위 초록 상자)
        val (turn, toward, right) = naviMap.nextTurn()
        val bl = X(876f); val bt = Y(116f); val br = X(1458f)
        fill.color = 0xF2128A4E.toInt()
        c.drawRoundRect(bl, bt, br, Y(330f), 26f * scale, 26f * scale, fill)
        naviMap.drawTurnArrow(c, bl + 100f * scale, Y(222f), 120f * scale, right)
        label(c, turn, bl + 190f * scale, Y(212f), 50f, 0xFFFFFFFF.toInt())
        label(c, if (toward.isNotEmpty()) toward else "${naviMap.roadNow} 따라", bl + 190f * scale, Y(272f), 30f, 0xFFD9F7E5.toInt())
        // 남은 거리 · 시간 · 도착 예정 + 버튼 (고양이 길보다 위에 — 길 위 표지·글씨와 겹치지 않게)
        val it2 = Y(700f)
        fill.color = 0xF7FFFFFF.toInt()
        c.drawRoundRect(bl, it2, br, Y(966f), 26f * scale, 26f * scale, fill)
        val app = vm.maps.routeApp
        label(c, name, bl + 34f * scale, it2 + 62f * scale, 40f, 0xFF1E1E1E.toInt())
        val mps = maxOf(kmh / 3.6f, 8.3f)
        val min = (naviMap.remaining / mps / 60f).toInt().coerceAtLeast(if (naviMap.remaining > 30f) 1 else 0)
        val eta = java.util.Calendar.getInstance().apply { add(java.util.Calendar.MINUTE, min) }
        label(c, "${StageNavi.distText(naviMap.remaining)} · ${min}분 · 도착 %d:%02d".format(eta.get(java.util.Calendar.HOUR_OF_DAY), eta.get(java.util.Calendar.MINUTE)),
            bl + 34f * scale, it2 + 116f * scale, 34f, 0xFF128A4E.toInt())
        val live = vm.live
        val gap = 18f * scale
        val bw = (br - bl - 34f * scale * 2 - gap * 2) / 3
        val by = it2 + 146f * scale
        if (live.controllable && vm.mode.value == Mode.LIVE) {
            val moving = car.gear == Gear.D
            smallButton(c, if (moving) "■ 멈춤" else "▶ 모의 주행", bl + 34f * scale, by, bw, true, if (moving) 0xFFE5484D.toInt() else 0xFF2F80ED.toInt()) {
                if (moving) { live.setGear(Gear.P); say("P · 멈춤") } else { live.setGear(Gear.D); say("모의 주행 시작") }
            }
        }
        if (vm.mode.value == Mode.DEMO) label(c, "출근길 시연 중", bl + 34f * scale + bw + gap + 20f * scale, by + 60f * scale, 30f, 0xFF1E1E1E.toInt())
        else if (live.controllable && car.gear == Gear.D) smallButton(c, if (live.simBoost) "정속 주행" else "과속 상황 보기", bl + 34f * scale + bw + gap, by, bw,
            live.simBoost, 0xFFFF8F00.toInt()) { live.toggleBoost(); say(if (live.simBoost) "과속 상황 · 시속 약 90km" else "정속 주행 · 시속 50km대") }
        else smallButton(c, "${app.label} 열기", bl + 34f * scale + bw + gap, by, bw, false, app.color) { vm.maps.showMap(true) }
        val armed = android.os.SystemClock.uptimeMillis() - endArmedAt < 3000
        smallButton(c, if (armed) "한 번 더 = 종료" else "안내 종료", bl + 34f * scale + (bw + gap) * 2, by, bw, armed, 0xFFE5484D.toInt()) {
            if (android.os.SystemClock.uptimeMillis() - endArmedAt >= 3000) {    // 잘못 누름 방지: 3초 안에 한 번 더
                endArmedAt = android.os.SystemClock.uptimeMillis(); say("한 번 더 누르면 길안내를 끝내요"); postDelayed({ invalidate() }, 3100)
                return@smallButton
            }
            endArmedAt = 0L
            if (vm.mode.value == Mode.DEMO) { vm.setMode(Mode.LIVE); say("출근길 시연을 멈췄어요") }   // 시연 경로는 시연을 멈춰야 사라진다
            else { vm.maps.cancel(); say("길안내를 끝냈어요") }
            if (car.gear == Gear.D && live.controllable) live.setGear(Gear.P)
        }
        return true
    }

    private var endArmedAt = 0L

    private fun smallButton(c: Canvas, s: String, x: Float, y: Float, w: Float, filled: Boolean, color: Int, onTap: () -> Unit) {
        val h = 96f * scale
        fill.color = if (filled) color else 0xFFF1F3F5.toInt()
        c.drawRoundRect(x, y, x + w, y + h, 16f * scale, 16f * scale, fill)
        label(c, s, x + w / 2, y + h / 2 + 11f * scale, 30f, if (filled) 0xFFFFFFFF.toInt() else 0xFF1E1E1E.toInt(), Paint.Align.CENTER)
        hits += RectF(x, y, x + w, y + h) to onTap
    }

    /** 가운데 내비 자리(그림 속 검색 창 876~1458 × 126~1276)를 길안내 카드로 (경로가 있으면 그린 내비) */
    private fun drawNaviCard(c: Canvas) {
        if (drawNaviMap(c)) return
        val l = X(876f); val t = Y(126f); val r = X(1458f); val b = Y(1276f)
        fill.style = Paint.Style.FILL; fill.color = 0xFFFFFFFF.toInt()
        c.drawRect(l, t, r, b, fill)
        fill.style = Paint.Style.STROKE; fill.strokeWidth = 2f * scale; fill.color = 0xFFDADADA.toInt()
        c.drawRect(l, t, r, b, fill)
        fill.style = Paint.Style.FILL
        val pad = 34f * scale
        var y = t + pad
        // 머리: 길안내 앱 배지(네이버 N · 카카오 K · 티맵 T) + 제목
        val app = if (navi.hasRoute) vm.maps.routeApp else vm.maps.app
        fill.color = app.color
        c.drawRoundRect(l + pad, y, l + pad + 56f * scale, y + 56f * scale, 12f * scale, 12f * scale, fill)
        label(c, app.badge, l + pad + 28f * scale, y + 44f * scale, 40f, app.badgeInk, Paint.Align.CENTER)
        label(c, app.label + if (navi.hasRoute) " 길안내 중" else " 길안내", l + pad + 76f * scale, y + 42f * scale, 30f, 0xFF1E1E1E.toInt())
        label(c, "앱 바꾸기 ▸", r - pad, y + 42f * scale, 28f, 0xFF1E1E1E.toInt(), Paint.Align.RIGHT)
        hits += RectF(r - pad - 170f * scale, y, r - pad, y + 56f * scale) to { vm.openInput("dest") }
        y += 120f * scale
        if (navi.hasRoute) {
            label(c, navi.destinationName ?: "목적지", l + pad, y, 54f, 0xFF1E1E1E.toInt())
            y += 90f * scale
            val km = (navi.remainM ?: 0) / 1000f
            val dist = if (km >= 1f) "%.1fkm".format(km) else "${navi.remainM ?: 0}m"
            val min = (navi.remainSec ?: 0) / 60
            label(c, dist + if (min > 0) "  ·  ${min}분" else "", l + pad, y, 44f, 0xFF03A04A.toInt())
            y += 60f * scale
            if (min > 0) {
                val eta = java.util.Calendar.getInstance().apply { add(java.util.Calendar.MINUTE, min) }
                label(c, "도착 예정 %d:%02d".format(eta.get(java.util.Calendar.HOUR_OF_DAY), eta.get(java.util.Calendar.MINUTE)), l + pad, y, 28f, 0xFF1E1E1E.toInt())
            }
            y += 70f * scale
            label(c, "가는 길 위험은 펫이 깃발까지 달리며 알려 드려요", l + pad, y, 28f, 0xFF1E1E1E.toInt())
            button(c, "지도 보기", l + pad, b - pad - 96f * scale, (r - l) / 2 - pad * 1.25f, true, app.color, app.badgeInk) { vm.maps.showMap(true) }
            button(c, "목적지 바꾸기", (l + r) / 2 + pad * 0.25f, b - pad - 96f * scale, (r - l) / 2 - pad * 1.25f, false) { vm.openInput("dest") }
        } else {
            label(c, "어디로 갈까요?", l + pad, y, 54f, 0xFF1E1E1E.toInt())
            y += 64f * scale
            label(c, "말로: \"TMI, 잠실역 가자\"", l + pad, y, 28f, 0xFF1E1E1E.toInt())
            y += 50f * scale
            button(c, "목적지 입력", l + pad, y, r - l - pad * 2, true, app.color, app.badgeInk) { vm.openInput("dest") }
            y += 140f * scale
            val recent = vm.maps.recent().take(4)
            if (recent.isNotEmpty()) {
                label(c, "최근 목적지", l + pad, y, 28f, 0xFF1E1E1E.toInt())
                y += 24f * scale
                recent.forEach { place ->
                    val rowT = y
                    y += 84f * scale
                    fill.color = 0xFFEDEDED.toInt()
                    c.drawRect(l + pad, y - 2f * scale, r - pad, y, fill)
                    label(c, "⌖  $place", l + pad + 8f * scale, y - 28f * scale, 32f, 0xFF1E1E1E.toInt())
                    hits += RectF(l + pad, rowT, r - pad, y) to { vm.navigateTo(place) }
                }
            }
        }
    }

    private fun label(c: Canvas, s: String, x: Float, y: Float, size: Float, color: Int, align: Paint.Align = Paint.Align.LEFT) {
        text.typeface = bold; text.textSize = size * scale; text.color = color; text.textAlign = align
        c.drawText(s, x, y, text)
    }

    private fun button(c: Canvas, s: String, x: Float, y: Float, w: Float, filled: Boolean, color: Int = 0xFF03C75A.toInt(), ink: Int = 0xFFFFFFFF.toInt(), onTap: () -> Unit) {
        val h = 96f * scale
        fill.color = if (filled) color else 0xFFF1F3F5.toInt()
        c.drawRoundRect(x, y, x + w, y + h, 18f * scale, 18f * scale, fill)
        label(c, s, x + w / 2, y + h / 2 + 12f * scale, 34f, if (filled) ink else 0xFF1E1E1E.toInt(), Paint.Align.CENTER)
        hits += RectF(x, y, x + w, y + h) to onTap
    }

    // 달리는 동안엔 매 프레임 다시 그려 눌리는 곳 목록이 새로 만들어진다 → '같은 칸을 누르고 뗐나'를 자리로 판단
    private var downX = -1f
    private var downY = -1f

    @android.annotation.SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(e: MotionEvent): Boolean {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                if (hits.none { it.first.contains(e.x, e.y) }) return false
                downX = e.x; downY = e.y
                return true
            }
            MotionEvent.ACTION_UP -> {
                tapX = e.x; tapY = e.y
                val h = hits.firstOrNull { it.first.contains(e.x, e.y) && it.first.contains(downX, downY) }?.second
                if (h != null) { performClick(); h() }
                downX = -1f
            }
            MotionEvent.ACTION_CANCEL -> downX = -1f
        }
        return downX >= 0
    }

    override fun performClick(): Boolean { super.performClick(); return true }
}
