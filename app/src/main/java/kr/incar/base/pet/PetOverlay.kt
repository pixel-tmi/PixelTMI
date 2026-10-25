package kr.incar.base.pet

import android.content.Context
import android.graphics.PixelFormat
import android.widget.FrameLayout
import android.provider.Settings
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import kr.incar.base.car.CarState
import kr.incar.base.car.Gear
import kr.incar.base.tmi.Fx
import kr.incar.base.tmi.TmiEngine
import kr.incar.base.tmi.TmiKind
import kr.incar.base.ui.pixel.Icons
import kr.incar.base.voice.Voice

/** 설정 말풍선에서 고르는 일들 */
interface PetActions {
    fun talk()
    /** 내 위치로: 펫이 내 차 자리로 돌아와 지금 위치 TMI를 알려 준다 */
    fun locate()
    fun settingsRows(): List<Pair<String, () -> Unit>>
    /** 톱니로 새로 열 때 (첫 화면 메뉴로) */
    fun settingsOpened() {}
}

/**
 * 펫을 Pleos 메인 화면 위에 얹는 창들.
 * - Pleos 차량: 다른 앱 위 시스템 창(어느 화면에서든 보임).
 * - 갤럭시 탭: 'Pleos 전용 앱'(StageActivity) 화면 안에만 붙인다 → 앱 밖 탭 화면엔 아무것도 안 뜬다.
 * - 펫 띠: 배경 없음, 하단 버튼 줄 바로 위. 터치는 전부 통과 → 가려도 뒤 버튼이 눌린다.
 * - 오른쪽 끝: 마이크 · 톱니(설정) 버튼 고정. 톱니를 누르면 말풍선 설정이 올라온다.
 * "다른 앱 위에 표시" 권한(SYSTEM_ALERT_WINDOW)이 필요하다.
 */
class PetOverlay(
    private val context: Context,
    private val scope: CoroutineScope,
    private val engine: TmiEngine,
    private val voice: Voice,
    private val car: StateFlow<CarState>,
    private val destLabel: StateFlow<String?>,
    private val listening: StateFlow<Boolean>,
    private val character: StateFlow<String>,
    private val actions: PetActions,
    /** 배경 테마 id ("auto" = 사계절) */
    private val theme: StateFlow<String>,
    /** 기상청 예보 (비·눈·안개 배경) */
    private val weather: StateFlow<kr.incar.base.tmi.Weather>,
) {
    private val wm = context.getSystemService(WindowManager::class.java)
    /** 크기 기준 — 탭 Pleos 앱은 그림 배율을 따르므로 그때그때 계산 */
    private val dp: Float get() = PetScale.dp(context)
    /** 펫을 붙일 앱 화면 (탭). null이면 시스템 창 (Pleos 차량) */
    private var host: FrameLayout? = null
    /** 탭처럼 차가 아닌 기기: 앱 화면 안에서만 */
    private val inAppOnly: Boolean get() = !kr.incar.base.car.CarSpeedSource.available
    private val prefs = context.getSharedPreferences("Pixel TMI_pet", Context.MODE_PRIVATE)
    /** 버튼 묶음을 끌어 옮긴 거리 (기본 자리에서 왼쪽·위로 +) */
    private var groupDx = prefs.getInt("btn_dx", 0)
    private var groupDy = prefs.getInt("btn_dy", 0)
    private var dragStartDx = 0
    private var dragStartDy = 0
    private val buttons = mutableListOf<Pair<PetButton, Int>>()   // 버튼, 기본 x(오른쪽 끝에서)
    private var view: PetView? = null
    private val extras = mutableListOf<View>()
    private var bubble: SettingsBubble? = null
    private val jobs = mutableListOf<Job>()

    private val _shown = MutableStateFlow(false)
    val shown: StateFlow<Boolean> = _shown.asStateFlow()

    fun canShow() = inAppOnly || Settings.canDrawOverlays(context)

    /** 탭: 우리가 띄운 길안내 앱이 앞에 있을 때만 지도 위로 따라 나온다 (시스템 창) */
    private var overApps = false
    val isOverApps: Boolean get() = overApps && view != null

    fun showOverApps(): Boolean {
        if (host != null) return false
        if (overApps && view != null) return true
        overApps = true
        PetScale.stageGroundLift = 150 * dp
        return show().also { if (!it) overApps = false }
    }

    /** 탭 Pleos 앱 화면에 붙이기 (화면이 보일 때) */
    fun attach(container: FrameLayout) {
        if (host === container && view != null) return
        hide()
        host = container
        show()
    }

    /** 탭 Pleos 앱 화면에서 떼기 (화면이 가려질 때) */
    fun detach(container: FrameLayout) {
        if (host !== container) return
        hide()
        host = null
    }

    fun show(): Boolean {
        if (view != null) return true
        if (inAppOnly && host == null && !overApps) return false        // 탭: 앱 밖에는 띄우지 않는다 (지도 위 따라 나오기만 예외)
        if (!canShow()) {
            Log.i(TAG, "다른 앱 위에 표시 권한 없음")
            return false
        }
        val v = PetView(context)
        v.onActSound = { mood -> voice.say("", emptyList(), happy = mood == "happy", mood = mood) }   // 동작마다 그 캐릭터 울음
        v.rightReserved = BUTTONS_DP * dp
        // 화면 전체(하단 바 위까지) — 고양이가 벽·천장까지 돌아다닌다. 하단 바는 시스템 영역이라 창이 알아서 그 위에서 끝난다.
        val ok = add(v, WindowManager.LayoutParams.MATCH_PARENT, WindowManager.LayoutParams.MATCH_PARENT, touchable = false, gravity = Gravity.TOP or Gravity.START, x = 0, y = 0, title = "PixelTMI Pet")
        Log.i(TAG, "펫 창 추가: $ok")
        if (!ok) return false
        view = v
        _shown.value = true
        bind(v)
        val size = (92 * dp).toInt()
        val baseY = (GAP_DP * dp).toInt() + PetScale.stageGroundLift.toInt()
        // 꾹 누르고 있으면(홀드) 묶음째 옮기기 — 짧게 누르면 원래 기능
        val canMove = { !buttonsLocked }
        val gear = PetButton(context, Icons.SETTINGS_COG, onTap = { toggleSettings() }, canMove, ::liftGroup, ::dragGroup, ::dropGroup, "설정")
        val mic = PetButton(context, Icons.MIC, onTap = { actions.talk() }, canMove, ::liftGroup, ::dragGroup, ::dropGroup, "말하기")
        val here = PetButton(context, Icons.MAP_PIN, onTap = { actions.locate() }, canMove, ::liftGroup, ::dragGroup, ::dropGroup, "브리핑")
        // 볼륨: 누를 때마다 100% → 70% → 40% → 음소거 → 100%, 그림도 물결 수가 바뀐다
        lateinit var vol: PetButton
        vol = PetButton(context, speakerGlyph(volumeLevel()), onTap = {
            when {
                voice.muted -> { voice.muted = false; voice.volume = 1f }
                voice.volume > 0.85f -> voice.volume = 0.7f
                voice.volume > 0.55f -> voice.volume = 0.4f
                else -> { voice.stop(); voice.muted = true }
            }
            vol.glyph = speakerGlyph(volumeLevel())
            if (!voice.muted) voice.say("", listOf("sfx_pop"), cry = false)   // 바뀐 크기를 바로 들려준다
        }, canMove, ::liftGroup, ::dragGroup, ::dropGroup, "소리")
        buttons.clear()
        val step = size + (12 * dp).toInt()
        clampGroup()
        listOf(gear to "Gear", mic to "Mic", here to "Here", vol to "Volume").forEachIndexed { i, (b, name) ->
            val bx = (18 * dp).toInt() + i * step
            if (add(b, size, size, touchable = true, gravity = Gravity.BOTTOM or Gravity.END, x = bx + groupDx, y = baseY + groupDy, title = "PixelTMI $name")) {
                extras += b
                buttons += b to bx
            }
        }
        jobs += scope.launch { listening.collect { mic.listening = it; mic.invalidate() } }
        volumeButton = vol
        return true
    }

    // ── 버튼 묶음 옮기기: 아무 버튼이나 꾹(0.45초) 누르고 있다가 끌면 넷이 같이 움직인다 (자리는 기억) ──
    /** 버튼 위치 고정 (설정) — 켜면 홀드해도 안 움직인다 */
    var buttonsLocked: Boolean = prefs.getBoolean("btn_locked", true)
        set(v) { field = v; prefs.edit().putBoolean("btn_locked", v).apply() }

    private fun liftGroup() {
        dragging = true
        dragStartDx = groupDx
        dragStartDy = groupDy
        closeSettings()
        buttons.forEach { it.first.lifted = true }
    }
    private fun screenW(): Int = host?.width?.takeIf { it > 0 } ?: context.resources.displayMetrics.widthPixels
    private fun screenH(): Int = host?.height?.takeIf { it > 0 } ?: context.resources.displayMetrics.heightPixels
    private fun baseY(): Int = (GAP_DP * dp).toInt() + PetScale.stageGroundLift.toInt()

    private fun clampGroup() {
        val size = (92 * dp).toInt()
        val groupW = 4 * size + 3 * (12 * dp).toInt()
        val right = (18 * dp).toInt()
        groupDx = groupDx.coerceIn(-right, (screenW() - groupW - right).coerceAtLeast(-right))
        groupDy = groupDy.coerceIn(-baseY(), (screenH() - size - baseY()).coerceAtLeast(-baseY()))
    }

    private fun dragGroup(dx: Float, dy: Float) {
        if (!dragging) return
        groupDx = dragStartDx - dx.toInt()      // 오른쪽 끝 기준이라 오른쪽으로 끌면 줄어든다
        groupDy = dragStartDy - dy.toInt()      // 아래쪽 끝 기준이라 아래로 끌면 줄어든다
        clampGroup()
        buttons.forEach { (b, bx) -> place(b, bx + groupDx, baseY() + groupDy) }
    }

    private var dragging = false

    private fun dropGroup() {
        dragging = false
        buttons.forEach { it.first.lifted = false }
        prefs.edit().putInt("btn_dx", groupDx).putInt("btn_dy", groupDy).apply()
    }

    /** 버튼 묶음을 원래 자리로 */
    fun resetButtons() {
        groupDx = 0; groupDy = 0
        prefs.edit().putInt("btn_dx", 0).putInt("btn_dy", 0).apply()
        buttons.forEach { (b, bx) -> place(b, bx, baseY()) }
    }

    /** 창(또는 앱 화면 안 조각)의 자리만 옮긴다 — gravity BOTTOM|END 기준 */
    private fun place(v: View, x: Int, y: Int) {
        val h = host
        if (h != null) {
            (v.layoutParams as? FrameLayout.LayoutParams)?.let { lp -> lp.rightMargin = x; lp.bottomMargin = y; v.layoutParams = lp }
        } else {
            (v.layoutParams as? WindowManager.LayoutParams)?.let { lp -> lp.x = x; lp.y = y; runCatching { wm.updateViewLayout(v, lp) } }
        }
    }

    private fun add(v: View, w: Int, h: Int, touchable: Boolean, gravity: Int, x: Int, y: Int, title: String): Boolean {
        host?.let { box ->
            // 탭 Pleos 앱: 화면 안 조각으로. 펫 띠는 클릭을 받지 않으니 터치가 아래(Pleos 화면)로 내려간다
            val lp = FrameLayout.LayoutParams(w, h, gravity).apply {
                if (gravity and Gravity.HORIZONTAL_GRAVITY_MASK == Gravity.RIGHT) rightMargin = x else leftMargin = x   // END = RIGHT 비트 포함
                if (gravity and Gravity.VERTICAL_GRAVITY_MASK == Gravity.BOTTOM) bottomMargin = y else topMargin = y
            }
            if (!touchable) { v.isClickable = false; v.isFocusable = false }
            return runCatching { box.addView(v, lp) }.onFailure { Log.w(TAG, "화면 조각 추가 실패 $title", it) }.isSuccess
        }
        val flags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
            WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
            (if (touchable) 0 else WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE)
        val lp = WindowManager.LayoutParams(w, h, WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY, flags, PixelFormat.TRANSLUCENT).apply {
            this.gravity = gravity
            this.x = x
            this.y = y
            this.title = title
            // 터치를 통과시키는 큰 창은 0.8 이하여야 아래 앱이 터치를 받는다 (넘으면 안드로이드가 '믿을 수 없는 터치'로 버림)
            if (!touchable) alpha = 0.8f
        }
        return runCatching { wm.addView(v, lp) }.onFailure { Log.w(TAG, "창 추가 실패 $title", it) }.isSuccess
    }

    private var volumeButton: PetButton? = null

    /** 말로 "음소거"·"소리 크게" 했을 때 볼륨 버튼 그림도 맞춘다 */
    fun refreshVolume() { volumeButton?.glyph = speakerGlyph(volumeLevel()) }

    /** 0 = 음소거, 1~3 = 물결 수 */
    private fun volumeLevel(): Int = when {
        voice.muted -> 0
        voice.volume > 0.85f -> 3
        voice.volume > 0.55f -> 2
        else -> 1
    }

    /** 스피커 도트 그림 (24×24): 몸통 + 물결 n개, 음소거면 X */
    private fun speakerGlyph(level: Int): List<String> {
        val g = Array(24) { CharArray(24) { '.' } }
        fun p(x: Int, y: Int) { if (x in 0..23 && y in 0..23) g[y][x] = 'k' }
        for (y in 9..14) for (x in 3..6) p(x, y)                         // 스피커 몸통
        for (i in 0..4) for (y in 9 - i - 1..14 + i + 1) p(7 + i, y)     // 나팔
        if (level == 0) {
            for (i in 0..6) { p(15 + i, 8 + i); p(16 + i, 8 + i); p(21 - i, 8 + i); p(22 - i, 8 + i) }   // X
        } else {
            for (w in 1..level) {
                val r = 2.5 + w * 3.0
                for (y in 0..23) for (x in 13..23) {
                    val dist = kotlin.math.hypot((x - 11.5), (y - 11.5))
                    if (kotlin.math.abs(dist - r) < 0.8 && kotlin.math.abs(y - 11.5) < r * 0.75) p(x, y)
                }
            }
        }
        return g.map { String(it) }
    }

    /** 도착 세레모니 (폭죽 + 동물별 장기 + 코인) */
    fun celebrate(coins: Int, freezeAtMs: Long = -1L, kind: String? = null) {
        view?.celebrate(coins, freezeAtMs, kind)
        voice.say("", listOf("sfx_firework"), cry = false)
    }

    fun debugClimb() { view?.debugClimb() }
    fun debugAct(name: String) { view?.debugAct(name) }
    fun debugMoveTo(f: Float) { view?.debugMoveTo(f) }
    fun debugFx(kind: String, freezeAtMs: Long) { view?.debugFx(kind, freezeAtMs) }

    /** 내 위치로 버튼: 펫을 불러온다 */
    fun callHome() { view?.comeHome() }

    /** 톱니 → 말풍선 설정 열고 닫기 */
    fun toggleSettings(fresh: Boolean = true) {
        bubble?.let { closeSettings(); return }
        if (fresh) actions.settingsOpened()
        val b = SettingsBubble(context, rows = { actions.settingsRows() }, onClose = { closeSettings() })
        val w = (560 * dp).toInt()
        val bh = b.wantedHeight()
        val bx = ((12 * dp).toInt() + groupDx).coerceIn(0, (screenW() - w).coerceAtLeast(0))
        var by = ((GAP_DP + 100) * dp).toInt() + PetScale.stageGroundLift.toInt() + groupDy
        if (by + bh > screenH()) by = (baseY() + groupDy - bh).coerceAtLeast(0)   // 버튼을 위로 올렸으면 말풍선은 아래로
        if (add(b, w, bh, touchable = true, gravity = Gravity.BOTTOM or Gravity.END, x = bx, y = by, title = "PixelTMI Settings")) {
            bubble = b
        }
    }

    /** 메뉴를 바꿨을 때: 새 줄 수에 맞춰 다시 연다 */
    fun reopenSettings() {
        closeSettings()
        toggleSettings(fresh = false)
    }

    val settingsOpen: Boolean get() = bubble != null || shop != null

    private var shop: ShopBubble? = null

    /** 캐릭터·배경 고르기 말풍선 (화면을 바꾸지 않고 톱니 위에서) */
    fun openShop(
        owns: (PetChar) -> Boolean, ownsTheme: (Theme) -> Boolean, currentTheme: () -> String,
        pick: (PetChar) -> String, pickTheme: (Theme) -> String,
        startTab: Int = 0,
    ) {
        closeSettings()
        closeShop()
        val b = ShopBubble(context, { character.value }, currentTheme, owns, ownsTheme, { engine.ui.value.rewards.coins },
            pick = { ch -> pick(ch).also { view?.showcase() } },          // 바뀐 캐릭터가 그 자리에서 장기를 선보인다
            pickTheme = pickTheme, onClose = { closeShop() },
            history = { engine.ui.value.history }, startTab = startTab)
        val w = b.wantedWidth()
        val bh = b.wantedHeight()
        val bx = ((12 * dp).toInt() + groupDx).coerceIn(0, (screenW() - w).coerceAtLeast(0))
        var by = ((GAP_DP + 100) * dp).toInt() + PetScale.stageGroundLift.toInt() + groupDy
        if (by + bh > screenH()) by = (screenH() - bh).coerceAtLeast(0)
        if (add(b, w, bh, touchable = true, gravity = Gravity.BOTTOM or Gravity.END, x = bx, y = by, title = "PixelTMI Shop")) shop = b
    }

    fun closeShop() {
        shop?.let { remove(it) }
        shop = null
    }

    fun closeSettings() {
        bubble?.let { remove(it) }
        bubble = null
        closeShop()
    }

    private fun remove(v: View) {
        val h = host
        if (h != null) runCatching { h.removeView(v) } else runCatching { wm.removeView(v) }
    }

    private fun bind(v: PetView) {
        jobs += scope.launch { character.collect { v.setCharacter(it) } }
        jobs += scope.launch { theme.collect { v.theme = it; v.invalidate() } }
        jobs += scope.launch {
            var last: String? = null
            engine.ui.collect { u -> val h = u.heard; if (h != null && h != last) { last = h; v.showHeard(h) } }
        }
        jobs += scope.launch { weather.collect { w -> v.snowing = w.ok && w.snowing; v.foggy = w.ok && w.foggy; v.weatherRain = w.ok && w.raining } }
        jobs += scope.launch {
            combine(engine.ui, car, voice.speaking, destLabel) { ui, c, talking, dest -> listOf(ui, c, talking, dest) }.collect { (u, c, t, d) ->
                val ui = u as kr.incar.base.tmi.TmiUi
                val cs = c as CarState
                val dest = d as String?
                // 차가 서 있어도 내비가 모의 주행 중이면 그 속도로 달린다
                v.speedKmh = maxOf(cs.speedKmh ?: 0f, ui.naviSpeedKmh)
                v.raining = v.weatherRain || v.reportRain   // 비 = 그날 기상청 예보 · 비/소나기 제보 (와이퍼는 안 침, 겨울엔 눈)
                // 주행 중 = 기어가 P가 아님 (기어를 모르면 속도로). 신호 대기로 서도 주행 중 → 고양이는 길 위에서 기다린다
                v.driving = ui.naviMoving || (cs.gear?.let { it != Gear.P } ?: ((cs.speedKmh ?: 0f) > 1f))
                v.talking = t as Boolean
                v.destLabel = dest
                updateTrack(ui.posM, dest != null)
                v.posM = ui.posM
                v.trackStartM = trackStart
                v.trackLenM = trackLen
                v.hazards = ui.hazards
                v.chaser = ui.chaser
                v.speedLimit = engine.speedLimit(ui.posM)
                // 내가 제보한(또는 바로 근처의) 비·우박·눈 → 배경에도 비·눈
                val near = (ui.mine + ui.hazards).filter { kotlin.math.abs(it.atM - ui.posM) < 400 }
                v.reportRain = near.any { it.type == kr.incar.base.tmi.HazardType.RAIN || it.type == kr.incar.base.tmi.HazardType.HAIL }
                v.reportSnow = near.any { it.type == kr.incar.base.tmi.HazardType.SNOW || it.type == kr.incar.base.tmi.HazardType.AVALANCHE }
                v.neededReports = engine.neededReports
                v.myReport = ui.myReport
                v.mine = ui.mine
                v.focusId = ui.approach?.hazard?.id
                v.alert = ui.approach?.let { it.distanceM <= 500 && !it.hazard.type.fixed } ?: false
            }
        }
        jobs += scope.launch {
            var lastAt = 0L
            engine.ui.collect { ui ->
                val l = ui.feed.firstOrNull() ?: return@collect
                if (l.atMillis == lastAt) return@collect
                lastAt = l.atMillis
                val txt = if ('\n' in l.text) l.text else l.text.replace(" · ", "\n")   // 줄을 직접 나눈 문장은 그대로
                val mine = ui.myReport
                if (l.kind == TmiKind.MINE && mine != null) v.reportSay(txt, mine.atM)   // 내 제보 소식은 제보한 자리 위에 따로 (겹쳐도 안 묻힘)
                else v.say(
                    tag = if (l.kind == TmiKind.SYSTEM) "알림" else l.kind.label,
                    text = txt,
                    danger = l.kind == TmiKind.DANGER,
                )
            }
        }
        jobs += scope.launch {
            engine.fx.collect { f ->
                when (f) {
                    is Fx.Danger -> v.cutIn(f.hazard.type)
                    is Fx.Coins -> v.coin(f.amount)
                    is Fx.LevelUp -> Unit
                    is Fx.Expired -> v.poof(f.hazard.atM)
                    is Fx.Arrived -> celebrate(f.coins)
                }
            }
        }
    }

    // ── 화면 위 길: 왼쪽 출발점 → 오른쪽 목적지 깃발. 목적지가 없으면 앞길 2km를 한 구간으로 ──
    private var trackStart = 0.0
    private var trackLen = AROUND_M
    private var trackIsRoute = false

    private fun updateTrack(pos: Double, route: Boolean) {
        if (route) {
            if (!trackIsRoute || pos < trackStart) { trackStart = pos; trackIsRoute = true }
            trackLen = maxOf(100.0, (pos - trackStart) + engine.remainingM())   // 간 거리 + 남은 거리 = 전체 길
        } else {
            if (trackIsRoute || pos < trackStart || pos >= trackStart + AROUND_M) { trackStart = pos; trackIsRoute = false }
            trackLen = AROUND_M
        }
    }

    /** 크기 기준이 바뀌었을 때(탭 Pleos 화면 모드 켜고 끔) 창을 새로 만든다 */
    fun restart() {
        if (view == null) return
        hide()
        show()
    }

    fun hide() {
        if (overApps && !PetScale.stage) PetScale.stageGroundLift = 0f
        overApps = false
        jobs.forEach { it.cancel() }
        jobs.clear()
        closeSettings()
        (listOfNotNull(view) + extras).forEach { remove(it) }
        extras.clear()
        buttons.clear()
        view = null
        _shown.value = false
    }

    companion object {
        private const val TAG = "PetOverlay"
        /** 하단 바 윗선과 오른쪽 버튼 사이 띄움 */
        const val GAP_DP = 10
        /** 목적지가 없을 때 한 구간 = 앞길 2km */
        const val AROUND_M = 2000.0
        /** 오른쪽 끝 버튼 네 개(볼륨·내 위치로·마이크·톱니)가 차지하는 폭 */
        const val BUTTONS_DP = 438
    }
}
