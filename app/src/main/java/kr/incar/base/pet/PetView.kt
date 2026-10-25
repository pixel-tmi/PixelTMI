package kr.incar.base.pet

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.os.SystemClock
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import android.view.View
import kr.incar.base.tmi.Hazard
import kr.incar.base.tmi.HazardType
import kr.incar.base.tmi.ReportStage
import kr.incar.base.tmi.Source
import kr.incar.base.tmi.agoText
import kr.incar.base.tmi.clockText
import kr.incar.base.ui.pixel.Icons
import kr.incar.base.ui.pixel.Sprites
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.sin
import kotlin.math.min
import kotlin.random.Random

/**
 * 바탕화면 펫 — Pleos 화면 전체에 얹힌 투명한 판. 땅 = 하단 버튼 바 윗선.
 * - 바닥은 길: 왼쪽 출발점 → 오른쪽 목적지 깃발(목적지가 없으면 앞길 2km). 위험 표시는 길 위 제자리에 고정.
 * - 서 있을 때(P): 고양이처럼 제멋대로 — 바닥을 걷고, 벽(화면 양끝·왼쪽 차량 판 경계)을 타고, 천장을 거꾸로 걷다 뛰어내린다.
 *   커튼(왼쪽 판 뒤·화면 밖)으로 쏙 들어가 꼬리만 남겼다가 다시 나온다.
 * - 달릴 때: 돌아다니지 않고 내려와서 간 거리만큼 깃발 쪽으로 뛰어간다. 신호 대기면 길 위에 앉아 기다린다.
 * - 모든 아이콘은 같은 도트 크기(캐릭터 = 카메라 크기).
 * - 이 창은 터치를 받지 않는다 → 가려도 뒤 버튼이 눌린다.
 */
class PetView(context: Context) : View(context) {

    // ── 바깥에서 넣어 주는 상태 ──
    var alert = false
    var speedKmh = 0f
    /** 주행 중(기어가 P가 아님) — 목적지로 뛰어가는 모드 */
    var driving = false
    var hazards: List<Hazard> = emptyList()
    /** 내 음성 제보(또는 내 차가 감지한 것) — 접수→공유→확인 단계를 길 위에 보여 준다 */
    var myReport: Hazard? = null
    /** 이번 주행의 내 제보 모두 (최신이 앞) */
    var mine: List<Hazard> = emptyList()
    var posM = 0.0
    var trackStartM = 0.0
    var trackLenM = 2000.0
    var focusId: String? = null
    var destLabel: String? = null
    /** 오른쪽 끝 버튼(톱니·마이크)이 차지하는 폭 — 바닥 배경·말풍선은 그 앞까지만 쓴다 */
    var rightReserved = 0f

    /** 캐릭터 그림 시트: assets/pet/<이름>_walk.png(4프레임), <이름>_idle.png(2프레임: 기본·깜빡) */
    private var walkSheet: Bitmap? = null
    private var runSheet: Bitmap? = null
    private var idleSheet: Bitmap? = null
    private var faceSheet: Bitmap? = null
    private var climbSheet: Bitmap? = null
    private var punchSheet: Bitmap? = null
    private var sneakSheet: Bitmap? = null
    private var pilotSheet: Bitmap? = null
    private var robotTransform: Bitmap? = null
    /** 에어쇼 중 되돌아오는 구간 (뒤집는 대신 좌우만 바꿈) */
    private var planeBack = false
    private var robotFlex: Bitmap? = null
    private var pilotGoggle: android.graphics.RectF? = null
    /** 지금 위험 바로 앞(140m 안)이라 살금살금 지나가는 중 */
    private var sneaking = false
    private val actSheets = HashMap<String, Bitmap>()
    /** 같은 지점 제보가 몇 건 모여야 공유되나 (내 제보 '확인 대기 n/기준' 표시용) */
    var neededReports = 2
    var talking = false
    /** 세레모니·울음을 고르는 기본 이름 (흰 고양이도 "cat") */
    private var charName = "cat"
    private var mobility = Mobility.WALKER
    private fun load(p: String) = runCatching { context.assets.open(p).use { android.graphics.BitmapFactory.decodeStream(it) } }.getOrNull()
    /** 길 위 위험 표시 컬러 도트 (assets/pet/haz_<종류>.png, 24x24 프레임) — 없으면 예전 선 그림 */
    private val hazArt = HashMap<HazardType, Bitmap?>()
    private fun hazBitmap(t: HazardType): Bitmap? = hazArt.getOrPut(t) { load("pet/haz_${t.name.lowercase()}.png") }
    private val raceFlag by lazy { load("pet/flag_race.png") }
    private val coinArt by lazy { load("pet/coin_spin.png") }

    /** 정사각 프레임을 가로로 이어 붙인 시트에서 한 장을 (x, y)부터 높이 h로 그린다 */
    private fun frame(c: Canvas, b: Bitmap, idx: Int, x: Float, y: Float, h: Float) {
        val n = (b.width / b.height).coerceAtLeast(1)
        val i = ((idx % n) + n) % n
        srcRect.set(i * b.height, 0, (i + 1) * b.height, b.height)
        dst.set(x, y, x + h, y + h)
        c.drawBitmap(b, srcRect, dst, bmpPaint)
    }

    /**
     * 상황마다 길 위 연출 — 가까워질수록 보인다.
     * 긴급차량 = 화면 테두리 빨강·파랑 번쩍 + "삐뽀삐뽀 · 길 터 주세요", 화재·산불 = 피어오르는 연기,
     * 안개 = 그 구간을 덮는 흰 안개, 폭설·눈사태 = 함박눈, 우박 = 튀는 얼음알, 강풍 = 바람 줄기,
     * 침수·해일 = 출렁이는 물결, 정체 = 앞차들 브레이크등.
     */
    private fun hazardFx(c: Canvas, t: HazardType, hx: Float, hy: Float, d: Double, now: Long, groundY: Float) {
        if (d > 900) return
        val cx = hx + icon / 2
        val a = ((900 - d) / 900).toFloat().coerceIn(0.25f, 1f)     // 가까울수록 진하게
        fun alpha(color: Int, k: Float) = ((((color ushr 24) and 0xFF) * k).toInt().coerceIn(0, 255) shl 24) or (color and 0xFFFFFF)
        when (t) {
            HazardType.EMERGENCY -> if (driving && d < 500) {
                val red = (now / 220) % 2 == 0L
                fill.color = alpha(if (red) 0xCCFF2D2D.toInt() else 0xCC2D7BFF.toInt(), a)
                val e = 14 * dpx
                c.drawRect(0f, 0f, width.toFloat(), e, fill)
                c.drawRect(0f, height - e, width.toFloat(), height.toFloat(), fill)
                c.drawRect(0f, 0f, e, height.toFloat(), fill)
                c.drawRect(width - e, 0f, width.toFloat(), height.toFloat(), fill)
                outlined(c, "삐뽀삐뽀 · 길 터 주세요", hx - 60 * dpx, hy - 56 * dpx, if (red) RED else 0xFF2D7BFF.toInt(), 20f)
            }
            HazardType.FIRE, HazardType.WILDFIRE -> {
                val big = if (t == HazardType.WILDFIRE) 1.8f else 1f
                // 넘실대는 불꽃 (불 마크) — 바깥 빨강 · 가운데 주황 · 속 노랑
                for (k in 0 until 3) {
                    val fxp = cx - 22 * dpx * big + k * 22 * dpx * big
                    val fl = (30 + 14 * abs(sin(now / 110.0 + k * 1.7)).toFloat()) * dpx * big
                    flame(c, fxp, hy + icon * 0.35f, 16 * dpx * big, fl, 0xFFE53935.toInt())
                    flame(c, fxp, hy + icon * 0.35f, 10 * dpx * big, fl * 0.7f, 0xFFFF9800.toInt())
                    flame(c, fxp, hy + icon * 0.35f, 5 * dpx * big, fl * 0.4f, 0xFFFFEB3B.toInt())
                }
                for (i in 0 until 6) {
                    val ph = (((now / 16) + i * 23) % 100) / 100f
                    val r = (10 + ph * 26) * dpx * big
                    fill.color = alpha(0x99707070.toInt(), (1 - ph) * a)
                    c.drawRect(cx - r + sin((ph * 6 + i).toDouble()).toFloat() * 14 * dpx, hy - ph * 190 * dpx * big - r, cx + r, hy - ph * 190 * dpx * big + r, fill)
                }
                if ((now / 90) % 3 == 0L) { fill.color = 0xFFFFC107.toInt(); c.drawRect(cx + 10 * dpx, hy - 20 * dpx, cx + 14 * dpx, hy - 16 * dpx, fill) }
            }
            HazardType.FOG -> {
                // 달리는 도로 위에 진한 뭉게구름 (천천히 흘러감)
                val drift = (now / 40 % 200).toFloat() * dpx * 0.3f
                for (i in 0 until 9) {
                    val px = cx - 260 * dpx + i * 65 * dpx + drift - 30 * dpx
                    val r = (34 + (i * 13) % 22) * dpx
                    val py = groundY - r * 0.55f - (i % 3) * 10 * dpx
                    fill.color = alpha(0xDDDCE2EA.toInt(), a); c.drawCircle(px, py, r, fill)
                    fill.color = alpha(0xEEF4F6F9.toInt(), a); c.drawCircle(px - r * 0.25f, py - r * 0.25f, r * 0.6f, fill)
                }
                outlined(c, "짙은 안개 · 천천히", cx - 60 * dpx, groundY - 110 * dpx, 0xFF5A6B7C.toInt(), 18f)
            }
            HazardType.SNOW, HazardType.AVALANCHE -> {
                for (i in 0 until 18) {
                    val ph = (((now / 22) + i * 17) % 100) / 100f
                    val x = cx + ((i * 53) % 420 - 210) * dpx + sin((ph * 8 + i).toDouble()).toFloat() * 10 * dpx
                    val y = groundY - 300 * dpx + ph * 300 * dpx
                    fill.color = INK; c.drawRect(x - 4 * dpx, y - 4 * dpx, x + 4 * dpx, y + 4 * dpx, fill)
                    fill.color = PAPER; c.drawRect(x - 3 * dpx, y - 3 * dpx, x + 3 * dpx, y + 3 * dpx, fill)
                }
            }
            HazardType.HAIL -> {
                for (i in 0 until 12) {
                    val ph = (((now / 12) + i * 31) % 100) / 100f
                    val x = cx + ((i * 67) % 360 - 180) * dpx
                    val y = if (ph < 0.8f) groundY - 280 * dpx + ph / 0.8f * 280 * dpx else groundY - sin(((ph - 0.8f) / 0.2f) * Math.PI).toFloat() * 24 * dpx
                    fill.color = 0xFF4FC3F7.toInt(); c.drawRect(x - 5 * dpx, y - 5 * dpx, x + 5 * dpx, y + 5 * dpx, fill)
                    fill.color = PAPER; c.drawRect(x - 3 * dpx, y - 3 * dpx, x, y, fill)
                }
            }
            HazardType.WIND -> {
                fill.color = alpha(0xAA4A90A4.toInt(), a)
                for (i in 0 until 6) {
                    val ph = (((now / 10) + i * 29) % 100) / 100f
                    val x = cx + 300 * dpx - ph * 600 * dpx
                    val y = groundY - (40 + (i * 37) % 220) * dpx
                    c.drawRect(x, y, x + 70 * dpx, y + 4 * dpx, fill)
                }
            }
            HazardType.FLOOD, HazardType.TSUNAMI -> {
                val tall = if (t == HazardType.TSUNAMI) 3f else 1f
                fill.color = alpha(0x993C8DFF.toInt(), a)
                var x = cx - 260 * dpx
                while (x < cx + 260 * dpx) {
                    val w = sin((x / (40 * dpx) + now / 180.0)).toFloat() * 6 * dpx * tall
                    c.drawRect(x, groundY - (14 * dpx + w) * tall, x + 12 * dpx, groundY, fill)
                    x += 12 * dpx
                }
            }
            HazardType.JAM -> if ((now / 400) % 2 == 0L) {
                fill.color = alpha(0x66FF1744, a)
                for (i in 0 until 3) c.drawRect(cx - (60 - i * 50) * dpx, groundY - 26 * dpx, cx - (48 - i * 50) * dpx, groundY - 18 * dpx, fill)
            }
            else -> Unit
        }
    }

    /** 불꽃 한 혀 (아래가 넓고 위로 뾰족) */
    private fun flame(c: Canvas, x: Float, base: Float, halfW: Float, h: Float, color: Int) {
        val p = android.graphics.Path().apply {
            moveTo(x - halfW, base)
            quadTo(x - halfW * 1.1f, base - h * 0.5f, x, base - h)
            quadTo(x + halfW * 1.1f, base - h * 0.5f, x + halfW, base)
            close()
        }
        fill.color = color
        c.drawPath(p, fill)
    }

    /** 위험 하나 그리기 (컬러 도트 우선, 2프레임 깜빡·움직임) */
    private fun drawHazard(c: Canvas, t: HazardType, x: Float, y: Float, now: Long) {
        val b = hazBitmap(t)
        if (b != null) {
            val period = when (t) { HazardType.CAMERA -> 700L; HazardType.ICE -> 650L; HazardType.RAIN -> 260L; else -> 380L }
            frame(c, b, ((now / period) % 2).toInt(), x, y, icon)
        } else {
            val pic = pictogram(t)
            sprite(c, pic, x, y, icon / pic.size, false)
        }
    }

    /** 금화 (빙글 도는 4프레임) — 없으면 예전 동전 그림 */
    private fun drawCoin(c: Canvas, x: Float, y: Float, size: Float, now: Long, seed: Int = 0) {
        val b = coinArt
        if (b != null) frame(c, b, (((now / 110) + seed) % 4).toInt(), x, y, size)
        else sprite(c, Icons.COINS, x, y, size / 24f, false)
    }

    /** 걷기·달리기 시트의 프레임 수 = 시트 폭 ÷ 한 장 폭(34x24 비율). 동물마다 4~8장 */
    private fun frameCount(b: Bitmap): Int = Math.round(b.width / (b.height * 34f / 24f)).coerceAtLeast(1)

    /** 동물마다 달리는 박자 (고양이 기준 1.0 — 작을수록 다리가 빠르다) */
    private fun runBeat(): Float = when (charName) { "dog" -> 0.8f; "lion" -> 1.15f; "horse" -> 0.85f; else -> 1f }

    /** UFO가 납치하는 고양이 · 헬기에서 내리는 강아지 */
    private val miniCat by lazy { load("pet/cat_idle.png") }
    private val miniDog by lazy { load("pet/dog_idle.png") }
    fun setCharacter(name: String) {
        val info = Catalog.get(name)
        charName = info.base
        mobility = info.mobility
        if (mobility != Mobility.WALKER && act == Act.ROAM && surf != Surf.FLOOR) startFall()
        if (mobility == Mobility.FLYER && (act == Act.HIDE || act == Act.PEEK)) act = Act.ROAM
        walkSheet = load("pet/${name}_walk.png")
        runSheet = load("pet/${name}_run.png")     // 전력질주 4프레임 (없으면 걷기로)
        idleSheet = load("pet/${name}_idle.png")
        faceSheet = load("pet/${name}_face.png")   // 말하기·놀람·웃음 (없으면 생략)
        climbSheet = load("pet/${name}_climb.png") // 벽 타기 大자 2장 + 철푸덕 1장 (없으면 옆모습을 돌려서)
        punchSheet = load("pet/${name}_punch.png") // 냥냥 펀치 준비·강타
        sneakSheet = load("pet/${name}_sneak.png") // 위험 근처에서 두 발로 서서 살금살금
        pilotSheet = load("pet/pilot_${info.base}.png")   // 기계: 위험 컷인에 나오는 조종사 (없으면 얼굴)
        robotTransform = if (info.base == "car") load("pet/car_transform.png") else null   // 스포츠카 도착 세레모니: 로봇 변신
        robotFlex = if (info.base == "car") load("pet/car_flex.png") else null           //  → 근육 자랑
        pilotGoggle = runCatching {
            val j = org.json.JSONObject(context.assets.open("pet/pilots.json").bufferedReader().readText()).getJSONObject(info.base)
            android.graphics.RectF(j.getDouble("x").toFloat(), j.getDouble("y").toFloat(),
                (j.getDouble("x") + j.getDouble("w")).toFloat(), (j.getDouble("y") + j.getDouble("h")).toFloat())
        }.getOrNull()
        actSheets.clear()
        for (k in IDLE_ACTS.keys) load("pet/${name}_$k.png")?.let { actSheets[k] = it }   // 세수·기지개·밥·잠·손 흔들기·덮치기
        procSheets.clear()
        PROC_ACTS[info.base]?.forEach { (k, _) -> load("pet/${name}_$k.png")?.let { procSheets[k] = it } }   // 공룡 습성 동작 그림 (있으면 그걸로)
        invalidate()
    }

    private var bubbleText: String? = null
    private var bubbleTag = ""
    private var bubbleDanger = false
    private var bubbleAt = 0L
    private var bubbleUntil = 0L
    private var cutInAt = 0L
    private var cutInType: HazardType? = null
    private var coinAt = 0L
    private var coinAmount = 0

    fun say(tag: String, text: String, danger: Boolean) {
        bubbleTag = tag
        bubbleText = text
        bubbleDanger = danger
        bubbleAt = SystemClock.uptimeMillis()
        bubbleUntil = bubbleAt + (3200 + text.length * 95L).coerceAtMost(12_000)
        layoutCache = null
        if (act == Act.HIDE) comeOut()            // 숨어 있다가도 말할 땐 나온다
        invalidate()
    }

    /** 점검용: 펀치·컷인 장면을 freezeMs 시점에 멈춰 세운다 */
    private var fxFreeze = -1L
    private var fxFreezeKind = ""
    fun debugFx(kind: String, freezeAtMs: Long) {
        fxFreezeKind = kind
        fxFreeze = freezeAtMs
        freezeMs = -1L                             // 세레모니 멈춤은 풀고
        freezeUntil = SystemClock.uptimeMillis() + 15_000
        if (kind == "cutin") cutIn(HazardType.DEBRIS)
        if (kind == "punch") flyers += Flyer(Icons.CAMERA, width * 0.2f, height - icon, 620 * dpx, -900 * dpx, SystemClock.uptimeMillis(), type = HazardType.CAMERA)
        invalidate()
    }

    /** 점검용: 주차 중 동작을 바로 (groom·stretch·eat·sleep·wave·pounce·land) */
    fun debugAct(name: String) {
        val now = SystemClock.uptimeMillis()
        if (name == "land") { landedAt = now; invalidate(); return }
        if (name.startsWith("p_")) {                                     // 습성 동작 바로 (시연 영상 녹화용) + 고증 한 줄
            val k = name.removePrefix("p_")
            val dur = PROC_ACTS[charName]?.firstOrNull { it.first == k }?.second ?: return
            act = Act.ROAM; surf = Surf.FLOOR; speed = 0f
            idleAct = name; idleActAt = now; idleUntil = now + dur
            nextDecision = idleUntil
            lastFactAt = -60_000L; bubbleUntil = 0L
            maybeFact(k, now, 1f)
            actSound(k, now)
            invalidate()
            return
        }
        if (name !in actSheets) return
        act = Act.ROAM; surf = Surf.FLOOR; speed = 0f
        idleAct = name; idleActAt = now; idleUntil = now + (IDLE_ACTS[name]?.second ?: 3000L)
        nextDecision = idleUntil
        invalidate()
    }

    /** 녹화용: 펫을 화면 가로 f(0~1) 자리 바닥으로 데려와 잠깐 머물게 한다 (버튼 뒤에 가리지 않게) */
    fun debugMoveTo(f: Float) {
        if (act == Act.FALL || surf != Surf.FLOOR) { act = Act.ROAM; surf = Surf.FLOOR }
        px = (width * f.coerceIn(0.05f, 0.95f))
        speed = 0f; dir = 1
        nextDecision = SystemClock.uptimeMillis() + 20_000
        invalidate()
    }

    /** 점검용: 지금 바로 왼쪽 판 경계(없으면 화면 왼쪽 끝) 벽에 철푸덕 붙어 오르기 */
    fun debugClimb() {
        if (mobility != Mobility.WALKER) return
        act = Act.ROAM
        surf = Surf.FLOOR
        val div = divider()
        climb(if (div > 0) div else 0f, -1)
        nextDecision = SystemClock.uptimeMillis() + 3500
        invalidate()
    }

    /** 내 위치로: 어디서 놀고 있든 내 차 자리(길 위)로 돌아와 몇 초 기다린다 */
    private var homeUntil = 0L
    fun comeHome() {
        if (act == Act.HIDE || act == Act.PEEK) act = Act.ROAM
        if (act == Act.ROAM && surf != Surf.FLOOR) startFall()
        homeUntil = SystemClock.uptimeMillis() + 5000
        invalidate()
    }

    fun cutIn(type: HazardType) {
        cutInAt = SystemClock.uptimeMillis()
        cutInType = type
        invalidate()
    }

    fun coin(n: Int) {
        coinAt = SystemClock.uptimeMillis()
        coinAmount = n
        invalidate()
    }

    // ── 제보 소멸: 그 자리에서 펑 (먼지) ──
    private val poofs = ArrayList<Pair<Double, Long>>()
    fun poof(atM: Double) {
        poofs += atM to SystemClock.uptimeMillis()
        invalidate()
    }

    // ── 도착 세레모니: 폭죽 팡팡 + 코인 ──
    private class Spark(var x: Float, var y: Float, var vx: Float, var vy: Float, val color: Int, var life: Float)
    private val sparks = ArrayList<Spark>()
    private var partyAt = -100_000L
    private var partyCoins = 0
    private var burstsLeft = 0
    private var nextBurstAt = 0L
    /** 점검용: 세레모니를 freezeMs 시점에 멈춰 세운다 (화면 캡처가 느린 에뮬레이터에서 확인용) */
    private var freezeMs = -1L
    private var freezeUntil = 0L
    fun celebrate(coins: Int, freezeAtMs: Long = -1L, kind: String? = null) {
        fxFreeze = -1L                             // 점검용 펀치·컷인 멈춤은 풀고
        freezeMs = freezeAtMs
        freezeUntil = SystemClock.uptimeMillis() + 15_000
        partyAt = SystemClock.uptimeMillis()
        partyCoins = coins
        pickPartyKind()
        if (kind != null) { partyKind = kind.removeSuffix("+egg"); if (kind.endsWith("+egg")) partyCameo = true }   // 점검용: 세레모니 종류 지정 (+egg = 아기 용)
        trail.clear()
        burstsLeft = 7
        nextBurstAt = partyAt
        if (act != Act.FALL) { act = Act.ROAM; speed = 0f }
        invalidate()
    }

    // ── 크기 기준: 한 도트 = 4dp, 아이콘 24도트 = 96dp ──
    private val dpx = PetScale.dp(context)   // 차 화면 기준 크기 (갤럭시 탭에선 알맞게 줄임)
    private val dot = 4f * dpx
    private val icon = 24 * dot

    private val font: Typeface = Typeface.createFromAsset(context.assets, "fonts/galmuri11_bold.ttf")
    private val fill = Paint().apply { isAntiAlias = false }
    private val bodyText = TextPaint(Paint.ANTI_ALIAS_FLAG).apply { typeface = font; textSize = 26f * dpx; color = INK }
    private val label = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = font; textSize = 18f * dpx }
    private var layoutCache: StaticLayout? = null

    // ── 고양이 움직임 ──
    /** 붙어 있는 면. angle = 그림을 돌리는 각도 (발이 면을 향하게) */
    private enum class Surf(val angle: Float) { FLOOR(0f), LEFT(90f), RIGHT(-90f), CEIL(180f) }
    private enum class Act { ROAM, FALL, HIDE, PEEK }
    private var surf = Surf.FLOOR
    private var act = Act.ROAM
    private var px = -1f                 // 발이 면에 닿은 점(몸 길이 방향의 가운데)
    /** 처음 한 번만 자리에 놓는다 (화면 밖 커튼 뒤에 숨으면 px가 음수가 되므로 px로 판단하면 순간이동한다) */
    private var placed = false
    private var py = 0f
    private var dir = 1                  // +1 그림 그대로, -1 좌우 뒤집기 (= 몸 앞쪽)
    private var speed = 0f
    private var nextDecision = 0L
    private var wallX = 0f
    private var fallX = 0f
    private var fallY = 0f
    private var fallVy = 0f
    private var fallAngle = 0f
    private var curtainX = 0f
    private var curtainSide = 0          // 커튼이 있는 쪽: -1 왼쪽, +1 오른쪽
    private var hideUntil = 0L
    private var lastFrame = 0L

    override fun onDraw(c: Canvas) {
        val now = SystemClock.uptimeMillis()
        c.save()
        if (now < shakeUntil) c.translate(((now / 30) % 3 - 1) * 4 * dpx, ((now / 45) % 3 - 1) * 3 * dpx)   // 펀치 순간 화면 흔들
        val wall = System.currentTimeMillis()      // 제보 시각 계산용 벽시계
        val dt = if (lastFrame == 0L) 0f else ((now - lastFrame) / 1000f).coerceAtMost(0.1f)
        lastFrame = now
        val groundY = height - 4f * dpx - PetScale.stageGroundLift   // 하단 바 윗선 = 땅 (Pleos 화면 모드면 그림 속 바 위)
        val originX = 40f * dpx                     // 출발점 (길의 왼쪽 끝, 고정)
        val endX = width - rightReserved - 200f * dpx
        val flagX = endX + 60 * dpx                 // 목적지 깃발 (길의 오른쪽 끝, 고정)

        // 고정 배경: 계절별 산·나무 + 날씨 (옅게 깔아서 앞의 정보를 가리지 않는다)
        backdrop(c, groundY, dt)

        // 길: 왼쪽 START → 오른쪽 F(목적지 깃발). 위험은 길 위 제자리에 고정, 고양이가 간 거리만큼 F로 계속 달려간다.
        // 목적지가 없으면(안전운전 모드) F 없이 앞길 2km를 한 구간으로 — 다음 위험까지 좁혀 간다.
        val half = bodyW() * sizeK / 2
        val route = destLabel != null
        val trackL = originX + half
        val trackR = flagX + icon / 2
        val lenM = if (route) trackLenM.coerceAtLeast(100.0) else AHEAD_M
        fun trackX(m: Double): Float = trackL + (trackR - trackL) * ((m - trackStartM) / lenM).coerceIn(0.0, 1.0).toFloat()
        fun aheadX(d: Double): Float = trackX(posM + d)
        val catX = trackX(posM)
        val remainM = (trackStartM + lenM - posM).coerceAtLeast(0.0)
        fun onTrack(m: Double) = m in trackStartM..(trackStartM + lenM)
        val nextHazard = hazards.filter { it.atM >= posM && onTrack(it.atM) && showNow(it) }.minByOrNull { it.atM }
        // 과속이 이어지면 사색이 된다
        if (driving && speedKmh > speedLimit + 5) { if (overSince == 0L) overSince = now } else overSince = 0L
        scared = overSince != 0L && now - overSince > 2500
        sneaking = driving && nextHazard != null && nextHazard.type !in PUNCHABLE && nextHazard.atM - posM in 0.0..140.0

        // START 표시 (길 왼쪽 끝, 고정)
        outlined(c, "출발", originX, groundY - 8 * dpx, INK, 24f)

        // 남은 거리 막대 (내비 미리보기처럼 줄어든다): 고양이 앞 → F, 목적지가 없으면 → 다음 위험
        val gaugeStart = catX + half + 12 * dpx
        val gaugeEnd = if (route) trackR - icon / 2 else nextHazard?.let { trackX(it.atM) - icon / 2 }
        if (gaugeEnd != null && gaugeEnd > gaugeStart + 8 * dpx) {
            fill.color = INK
            var x = gaugeStart
            while (x < gaugeEnd - 6 * dpx) {
                c.drawRect(x, groundY - 3 * dpx, min(x + 14 * dpx, gaugeEnd), groundY, fill)
                x += 24 * dpx
            }
            val gd = if (route) remainM else (nextHazard!!.atM - posM)
            val gtxt = (if (route) "" else "다음 위험 ") + if (gd >= 1000) "%.1fkm".format(gd / 1000) else "${gd.toInt()}m"
            outlined(c, gtxt, (gaugeStart + gaugeEnd) / 2 - 30 * dpx, groundY - 10 * dpx, INK, 24f)
        } else if (!route && driving) {
            outlined(c, "안전운전 모드 · 앞길 2km 평온", gaugeStart, groundY - 10 * dpx, INK, 24f)
        }

        // F: 목적지 깃발 (길 오른쪽 끝, 고정)
        if (route) {
            val rf = raceFlag
            val fh = icon * 1.6f
            if (rf != null) frame(c, rf, ((now / 120) % 4).toInt(), flagX + icon / 2 - fh * 2.5f / 32f, groundY - fh, fh)
            else sprite(c, Icons.FLAG, flagX, groundY - icon, dot, false)
            outlined(c, destLabel ?: "", (flagX - 10 * dpx).coerceAtMost(width - rightReserved - 260 * dpx), groundY - (if (rf != null) fh else icon) - 6 * dpx, INK)
        }

        // 필살기: 카메라·방지턱이 다가오면 캐릭터마다 다른 기술로 날려 버린다
        // (고양이 냥냥 펀치 · 강아지 핥기 · 말 뒷발차기 · 비행접시 메테오 · 헬기 사다리 · 비행기 미사일 …)
        val style = ATTACKS[charName] ?: ATTACKS.getValue("cat")
        if (driving && attackId == null) hazards.firstOrNull { it.type in PUNCHABLE && it.id !in punched && it.atM - posM in style.window }?.let { h ->
            attackId = h.id; attackM = h.atM; attackAt = now; attackKind = style.kind
            if (style.kind == "punch") punchAt = now
        }
        attackId?.let { id ->
            val pe = now - attackAt
            val hx = trackX(attackM)
            attackFx(c, attackKind, pe, style.impact, hx, groundY, catX)
            if (pe >= style.impact && id !in punched) {
                punched += id
                shakeUntil = now + 240
                hitAt = now; hitWord = style.word; hitX = hx; hitY = groundY - icon * 0.7f
                val t = hazards.firstOrNull { it.id == id }?.type ?: HazardType.CAMERA
                val back = if (attackKind == "kick") -1 else 1
                flyers += Flyer(pictogram(t), hx - icon / 2, groundY - icon, back * 620 * dpx, -900 * dpx, now, type = t)
            }
            if (pe > style.impact + 500) attackId = null
        }
        // 위험: 길 위 제자리에 고정. 고양이가 지나가면 사라진다
        // 제보 설명 글씨는 가까운 3곳만 (길이 길어 표지가 많을 때 글씨가 겹치지 않게)
        val labelIds = hazards.filter { it.atM >= posM && onTrack(it.atM) && showNow(it) }.sortedBy { it.atM }.take(3).map { it.id }.toSet()
        val labelBoxes = ArrayList<RectF>()                                  // 이번 장면에 쓴 설명 글씨 자리 (겹치면 건너뜀)
        hazards.filter { it.atM >= posM - (if (it.type in HazardType.FLOATING) 250 else 30) && onTrack(it.atM) && it.id !in punched && showNow(it) }.forEach { h ->
            var hx = trackX(h.atM) - icon / 2
            var hy = if (h.type in HazardType.FLOATING) groundY - icon - 120 * dpx else groundY - icon
            val d = (h.atM - posM).coerceAtLeast(0.0)
            // 동물: 고양이가 코앞(60m)에 오면 펄쩍 뛰어 길 밖으로 달아난다
            if (h.type == HazardType.ANIMAL && driving && d < 60) {
                val k = ((60 - d) / 60).toFloat()
                hx += k * 260 * dpx
                hy -= sin(k * Math.PI).toFloat() * 150 * dpx
            }
            hazardFx(c, h.type, hx, hy, d, now, groundY)
            drawHazard(c, h.type, hx, hy, now)
            outlined(c, if (d >= 1000) "%.1fkm".format(d / 1000) else "${d.toInt()}m", hx, hy - 8 * dpx, if (h.id == focusId) RED else INK)
            if (h.source != Source.NAVI && !h.type.fixed && h.id in labelIds) {
                // 사람·차가 올린 제보: 언제 올라왔고 얼마나 지났는지, 곧 사라질지
                val left = h.lifeLeftMin(wall)
                val soon = left != null && left <= 5
                val s = reportLabel(h, wall) + if (soon) " · 곧 사라짐" else ""
                val box = RectF(hx, hy - 60 * dpx, hx + s.length * 21 * dpx, hy - 30 * dpx)
                if (labelBoxes.none { RectF.intersects(it, box) }) {
                    labelBoxes += box
                    outlined(c, s, hx, hy - 36 * dpx, if (soon) RED else INK, 22f)
                }
            }
        }

        // 내 음성 제보: 새로 제보해도 앞의 것이 남아 제자리에서 계속 움직인다 (같은 자리면 옆으로 나란히)
        // 고양이 뒤로 흘러가며 접수 → 공유 → 확인을 보여 주고, 350m 넘게 멀어지면 사라진다
        mine.forEachIndexed { i, m ->
            if (!onTrack(m.atM) || posM - m.atM > 350 || i == 0) return@forEachIndexed
            val same = mine.take(i).count { abs(it.atM - m.atM) < 25 }
            val hx = trackX(m.atM) - icon / 2 + same * icon * 1.15f
            val hy = if (m.type in HazardType.FLOATING) groundY - icon - 120 * dpx else groundY - icon
            drawHazard(c, m.type, hx, hy, now)
            if (m.type != HazardType.EMERGENCY) hazardFx(c, m.type, hx, hy, 0.0, now, groundY)
            outlined(c, "내 제보 · ${m.stage.label}", hx, hy - 8 * dpx, MINE, 18f)
        }
        (mine.firstOrNull() ?: myReport)?.let { m ->
            val hx = trackX(m.atM) - icon / 2
            if (onTrack(m.atM)) {
                val hy = if (m.type in HazardType.FLOATING) groundY - icon - 120 * dpx else groundY - icon   // 비구름은 다른 구름과 같은 높이
                drawHazard(c, m.type, hx, hy, now)
                if (m.type != HazardType.EMERGENCY) hazardFx(c, m.type, hx, hy, 0.0, now, groundY)
                val step = when (m.stage) {
                    ReportStage.RECEIVED -> if (neededReports > 1) "확인 대기 ${m.reports}/$neededReports" else "접수 ${clockText(m.reportedAt)}"
                    ReportStage.SHARED -> "${m.sharedTo}대에 공유 ${clockText(m.sharedAt ?: m.reportedAt)}"
                    ReportStage.CONFIRMED -> "${m.confirms}대 확인 ${clockText(m.lastSeenAt)}"
                    ReportStage.RESOLVED -> "해결"
                }
                outlined(c, if (m.source == Source.MINE) "내 음성 제보" else "내 차 감지", hx, hy - 36 * dpx, MINE, 22f)
                outlined(c, step, hx, hy - 8 * dpx, INK)
            }
        }

        // 뒤에서 오는 긴급차량: 길 위를 나보다 조금 빠르게 달려 앞질러 간다 + 화면 테두리 빨강·파랑
        chaser?.let { ch ->
            val k = ((System.currentTimeMillis() - ch.reportedAt) / 5500f).coerceIn(0f, 1f)
            val cxh = -icon * 1.5f + (width + icon * 3f) * k                 // 왼쪽 밖 → 고양이를 앞질러 → 오른쪽 밖
            val bounce = -abs(sin(now / 70.0)).toFloat() * 4 * dpx
            drawHazard(c, HazardType.EMERGENCY, cxh, groundY - icon + bounce, now)
            // 속도선
            fill.color = 0x88FF3B3B.toInt()
            for (i in 0 until 3) c.drawRect(cxh - (40 + i * 26) * dpx, groundY - icon * (0.3f + i * 0.2f), cxh - (12 + i * 26) * dpx, groundY - icon * (0.3f + i * 0.2f) + 3 * dpx, fill)
            outlined(c, if (cxh < catX) "뒤에서 긴급차량!" else "휙! 앞질러 가요", cxh - 30 * dpx, groundY - icon - 10 * dpx, RED, 20f)
            if (abs(cxh - catX) < 500 * dpx) hazardFx(c, HazardType.EMERGENCY, cxh, groundY - icon, 0.0, now, groundY)
        }
        // 내 제보 소식: 제보한 자리 위에 오래 떠 있고, 멀어지면 사라진다
        if (reportText.isNotEmpty() && now < reportUntil && posM - reportAnchor < 350 && onTrack(reportAnchor)) {
            val rx = trackX(reportAnchor)
            val lines = reportText.split('\n')
            label.textSize = 20f * dpx
            val w = lines.maxOf { label.measureText(it) } + 28 * dpx
            val lh = 26 * dpx
            val top = groundY - icon - 70 * dpx - lines.size * lh
            val catNow = trackX(posM)
            val shift = if (abs(rx - catNow) < 380 * dpx) -(380 * dpx) else 0f     // 펫 말풍선과 같은 자리면 뒤쪽(왼쪽)으로
            val left = (rx - w / 2 + shift).coerceIn(4 * dpx, width - w - 4 * dpx)
            fill.color = PAPER
            c.drawRect(left, top, left + w, top + lines.size * lh + 16 * dpx, fill)
            fill.color = MINE
            c.drawRect(left, top, left + w, top + 4 * dpx, fill)
            c.drawRect(left, top, left + 3 * dpx, top + lines.size * lh + 16 * dpx, fill)
            c.drawRect(left + w - 3 * dpx, top, left + w, top + lines.size * lh + 16 * dpx, fill)
            c.drawRect(left, top + lines.size * lh + 13 * dpx, left + w, top + lines.size * lh + 16 * dpx, fill)
            lines.forEachIndexed { i, ln -> outlined(c, ln, left + 14 * dpx, top + 8 * dpx + (i + 1) * lh - 6 * dpx, INK, 20f) }
            label.textSize = 18f * dpx
        }

        // 제보 소멸: 그 자리에서 펑 하고 먼지
        poofs.removeAll { now - it.second > 900 }
        poofs.forEach { (atM, at) ->
            val p = (now - at) / 900f
            val x = trackX(atM)
            val y = groundY - icon / 2
            fill.color = HILL
            for (i in 0 until 10) {
                val a = i * (Math.PI * 2 / 10)
                val r = (20 + 70 * p) * dpx
                val sz = dot * (1.6f - p)
                val ox = x + (cos(a) * r).toFloat()
                val oy = y + (sin(a) * r).toFloat()
                c.drawRect(ox, oy, ox + sz, oy + sz, fill)
            }
            if (p < 0.8f) outlined(c, "소멸", x - 20 * dpx, y - (40 + 30 * p) * dpx, INK)
        }

        // 위험 경고면 벽·천장에 있다가도 바닥으로 뛰어내린다
        if (alert && act == Act.ROAM && surf != Surf.FLOOR) startFall()
        runTarget = catX
        if (freezeMs >= 0 && now < freezeUntil) partyAt = now - freezeMs   // 점검용 멈춤
        if (fxFreeze >= 0 && now < freezeUntil) {
            if (fxFreezeKind == "punch") punchAt = now - fxFreeze
            if (fxFreezeKind == "cutin") cutInAt = now - fxFreeze
        }
        val pa = now - partyAt
        val party = pa in 0..PARTY_MS
        // 세레모니: 깃발 앞 무대로 가서 살짝 클로즈업 (톡 커졌다가 마지막에 돌아온다)
        val zoom = when {
            !party -> 1f
            pa < 450 -> 1f + (ZOOM - 1f) * easeOutBack(pa / 450f)
            pa > PARTY_MS - 500 -> 1f + (ZOOM - 1f) * ((PARTY_MS - pa) / 500f)
            else -> ZOOM
        }
        if (party) {
            if (act == Act.FALL || surf != Surf.FLOOR) { act = Act.ROAM; surf = Surf.FLOOR }
            val stageX = (trackR - 300 * dpx).coerceAtLeast(width * 0.3f)   // F(깃발) 앞에서 클로즈업
            px += (stageX - px) * min(1f, dt * 8f)
            py = groundY
            dir = 1
            speed = 0f
        } else {
            move(now, dt, groundY)
        }

        // 나는 캐릭터: 달릴 땐 낮게(살짝), 쉴 땐 마음대로 오르내리며 떠다닌다
        if (mobility == Mobility.FLYER) {
            if (now > nextLiftAt) {
                liftGoal = if (driving || now < homeUntil || party) 34 * dpx else (50 + Random.nextFloat() * 300) * dpx
                nextLiftAt = now + 2200 + Random.nextLong(2600)
            }
            if (driving || now < homeUntil) liftGoal = 34 * dpx
            if (party) liftGoal = when {
                partyKind == "helipad" -> 8 * dpx                                        // 헬기장에 내려앉기
                charName == "ufo" || charName == "heli" -> 150 * dpx                     // 빔·밧줄이 보이게 높이
                partyKind == "balloons" -> 60 * dpx + min(1f, pa / 4000f) * 90 * dpx     // 풍선 들고 둥실
                else -> 60 * dpx
            }
            lift += (liftGoal - lift) * min(1f, dt * (if (party) 5f else 1.6f))
        } else lift = 0f
        val bob = if (mobility == Mobility.FLYER) sin(now / 320.0).toFloat() * 5 * dpx else 0f

        chasing = false
        partyFlip = false
        partyAct = null
        if (driving || act != Act.ROAM || surf != Surf.FLOOR || party) idleAct = null
        val walking = act == Act.FALL || speed > 0f || mobility == Mobility.FLYER
        val hop = if (party) partyHop(pa) else 0f
        if (idleAct == "pounce") {
            val ta = now - idleActAt
            if (ta in 600..1150) {
                px += (if (dir >= 0) 1 else -1) * 300 * dpx * dt
                px = px.coerceIn(bodyW() / 2, width - bodyW() / 2)
            }
        }
        val leap = if (idleAct == "pounce" && (now - idleActAt) in 600..1150) -sin((now - idleActAt - 600) / 550.0 * Math.PI).toFloat() * 40 * dpx else 0f
        val wiggle = if (idleAct == "pounce" && (now - idleActAt) < 600) ((now / 60) % 2 - 0.5f) * 2 * dpx else 0f   // 엉덩이 씰룩
        val bump = hop + leap + if (walking && act != Act.FALL && (now / 140) % 2 == 0L) -dpx * 2 else 0f
        val shake = if (alert) ((now / 40) % 3 - 1) * 2 * dpx else 0f
        var (cx, cy) = center()
        cy -= lift + bob
        var angle = if (act == Act.FALL) fallAngle else surf.angle
        // 세레모니 중 몸 움직임: 스포츠카 드리프트 회전 · 비행기 공중 한 바퀴
        planeBack = false
        if (party) { partyX0 = cx; partyY0 = cy }
        if (party && pa in 450..(PARTY_MS - 500)) {
            val u = (pa - 450f) / (PARTY_MS - 950f)
            val tt = pa - 450L
            when (partyKind) {
                "yarn" -> {
                    // 손 흔들기 → 공 쫓기 → 공 덮치기 → 생선 냠냠
                    val tt = pa - 450L
                    partyAct = when {
                        tt < 1100 -> "wave"
                        tt < 2500 -> "chase"
                        tt < 3300 -> "pounce"
                        else -> "eat"
                    }
                    when (partyAct) {
                        "chase" -> {
                            val ph = (tt - 1100) / 1400.0 * Math.PI * 2
                            cx += (sin(ph) * 80 * dpx).toFloat()
                            partyFlip = kotlin.math.cos(ph) < 0
                            chasing = true
                        }
                        "pounce" -> {
                            val k = (tt - 2500) / 800f
                            if (k > 0.45f) {
                                val j = (k - 0.45f) / 0.55f
                                cx += j * 70 * dpx
                                cy -= (sin(j * Math.PI) * 45 * dpx).toFloat()
                            }
                        }
                        "eat" -> cx += 70 * dpx
                    }
                }
                "hay", "carrot" -> cy += abs(sin(pa / 1000.0 * Math.PI * 4)).toFloat() * 4 * dpx   // 고개 숙여 우물우물
                "drift" -> if (u < 0.55f) angle = (u / 0.55f) * 720f
                "box" -> {                                     // 상자로 폴짝 → 쏙 들어갔다 빼꼼빼꼼
                    val sink = icon * zoom * 0.42f
                    if (tt < 600) partyAct = "wave"
                    else if (tt < 1300) {
                        val j = (tt - 600) / 700f
                        cx += j * BOX_DX * dpx
                        cy -= (sin(j * Math.PI) * 90 * dpx).toFloat()
                        if (j > 0.7f) cy += sink * (j - 0.7f) / 0.3f
                    } else {
                        cx += BOX_DX * dpx
                        cy += sink - abs(sin((tt - 1300) / 1000.0 * Math.PI * 1.4)).toFloat() * icon * zoom * 0.2f
                    }
                }
                "podium" -> {                                  // 시상대 1등 칸으로 폴짝
                    val up = PODIUM_TOP * dot * zoom * 0.85f
                    if (tt < 500) {
                        val j = tt / 500f
                        cy -= up * j + (sin(j * Math.PI) * 40 * dpx).toFloat()
                    } else cy -= up
                    if (tt in 500..1300) partyAct = "wave"
                }
                "frisbee" -> if (tt in 700..1400) {            // 날아오는 원반을 점프해서 덥석
                    val j = (tt - 700) / 700f
                    cy -= (sin(j * Math.PI) * 120 * dpx).toFloat()
                    angle = -18f * sin(j * Math.PI).toFloat()
                }
                "pinata" -> if (tt in 1100..1500) {            // 피냐타를 머리로 꽝!
                    val j = (tt - 1100) / 400f
                    cx += (sin(j * Math.PI) * 50 * dpx).toFloat()
                    cy -= (sin(j * Math.PI) * 50 * dpx).toFloat()
                }
                "fossil" -> if (tt < 1200) cx += sin(tt / 40.0).toFloat() * 3 * dpx   // 발로 파바박
                "fish" -> if (tt in 300..1500) {               // 땅까지 급강하해 물고기를 낚아채고 올라간다
                    val j = (tt - 300) / 1200f
                    cy += (sin(j * Math.PI) * (lift + icon * 0.15f)).toFloat()
                    angle = (kotlin.math.cos(j * Math.PI) * 25).toFloat()
                }
                "heart" -> {
                    // 하늘에 연기로 하트: 위로 솟았다가 하트를 그리고 내려온다 (뒤집지 않는다)
                    val rise = if (u < 0.15f) smooth(u / 0.15f) else if (u > 0.9f) smooth((1f - u) / 0.1f) else 1f
                    val v = ((u - 0.15f) / 0.75f).coerceIn(0f, 1f)
                    val th = v * Math.PI * 2
                    val sn = sin(th)
                    val hx = 16 * sn * sn * sn
                    val hy = 13 * kotlin.math.cos(th) - 5 * kotlin.math.cos(2 * th) - 2 * kotlin.math.cos(3 * th) - kotlin.math.cos(4 * th)
                    cx += (hx * HEART_S * dpx).toFloat()
                    cy -= rise * HEART_RISE * dpx + ((hy - 5) * HEART_S * dpx).toFloat()
                    planeBack = v in 0.001f..0.999f && sn * sn * kotlin.math.cos(th) < 0
                    trail += Triple(cx, cy + 6 * dpx, now)
                }
                "airshow" -> {
                    // 에어쇼: 큰 타원을 그리며 한 바퀴 — 뒤집지 않고, 돌아오는 쪽에선 방향만 바꾼다
                    val th = u * Math.PI * 2
                    val r = 140 * dpx
                    cx += (sin(th) * r).toFloat()
                    cy -= ((1 - kotlin.math.cos(th)) * r * 0.55f).toFloat()
                    planeBack = kotlin.math.cos(th) < 0
                    angle = (sin(th) * 12).toFloat() * (if (planeBack) -1f else 1f)
                    trail += Triple(cx - (if (planeBack) -1 else 1) * bodyW() * zoom * 0.45f, cy, now)
                }
            }
        }
        val sideways = abs(abs(angle) - 90f) < 45f
        val halfW = if (sideways) icon / 2 else bodyW() / 2
        val halfH = if (sideways) bodyW() / 2 else icon / 2
        val top = if (party || sizeK != 1f) cy + icon / 2 - icon * zoom * sizeK else cy - halfH   // 발밑 기준으로 커지니 머리 위는 그만큼 올라간다
        val bottom = cy + halfH

        // 컷인: 집중선 + 표지판 확대
        val cut = now - cutInAt
        if (cut in 0..1000) speedLines(c, cut / 1000f, groundY)

        c.save()
        if (act == Act.HIDE || act == Act.PEEK) {
            // 커튼 뒤로 들어간 부분은 안 보이게
            if (curtainSide < 0) c.clipRect(curtainX, 0f, width.toFloat(), height.toFloat())
            else c.clipRect(0f, 0f, curtainX, height.toFloat())
        }
        if (party) smokeTrail(c, now)
        // 벽에서 내려온 자리에 남은 할퀸 자국
        drawScratches(c, now)
        val pe = now - punchAt
        val z = zoom * sizeK
        if (party) ceremonyBack(c, pa, groundY, z)
        if (z != 1f) c.scale(z, z, cx, cy + icon / 2)
        val cl = climbSheet
        if (cl != null && act == Act.ROAM && (surf == Surf.LEFT || surf == Surf.RIGHT)) drawClimb(c, cl, now)
        else if (party && partyKind == "robot" && robotTransform != null && robotFlex != null && pa in 450..(PARTY_MS - 200)) drawRobot(c, pa - 450, cx, groundY, now)
        else {
            val pp = if (idleAct?.startsWith("p_") == true && !driving && !party) procPose(idleAct!!.removePrefix("p_"), ((now - idleActAt).toFloat() / (idleUntil - idleActAt).coerceAtLeast(1)).coerceIn(0f, 1f), now)
                .let { q ->
                    val k = idleAct!!.removePrefix("p_")
                    if (procSheets.containsKey(k) && k in POSTURE_ACTS) ProcPose(dx = q.dx, dy = q.dy, moving = q.moving) else q   // 자세는 그림이, 움직임(공중제비·드리프트)은 그대로
                } else null
            if (pp != null) {
                c.save()
                c.translate(pp.dx * (if (dir < 0) -1 else 1), pp.dy)
                c.scale(pp.sx, pp.sy, cx, cy + icon / 2)
                drawCharacter(c, cx + shake + wiggle, cy, angle + pp.rot * (if (dir < 0) -1 else 1), dir < 0, pp.moving, now, bump, false)
                c.restore()
            } else drawCharacter(c, cx + shake + wiggle, cy, angle, if (chasing) partyFlip else if (party && planeBack) dir >= 0 else dir < 0, walking || chasing, now, bump, party && !chasing)
        }
        c.restore()
        if (idleAct?.startsWith("p_") == true && !driving && !party)
            procFx(c, idleAct!!.removePrefix("p_"), ((now - idleActAt).toFloat() / (idleUntil - idleActAt).coerceAtLeast(1)).coerceIn(0f, 1f), now, cx, cy, groundY)
        if (sneaking) outlined(c, "살금살금…", cx - 50 * dpx, cy - icon * 0.95f, INK, 18f)
        if (pe in 0..360 && attackKind == "punch") hitSpark(c, pe, cx + bodyW() * 0.55f * z, cy - icon * 0.05f, z)
        val he = now - hitAt
        if (he in 0..420 && hitWord.isNotEmpty() && attackKind != "punch") hitSpark(c, he * 360 / 420, hitX, hitY, 1f, hitWord)
        flyAway(c, now, dt)
        if (party) ceremony(c, pa, cx, cy, groundY, zoom * sizeK)
        idleProps(c, now, cx, cy, groundY)

        // 코인
        val ce = now - coinAt
        if (ce in 0..1000) {
            val coinY = top - 20 * dpx - (ce / 1000f) * 70 * dpx - 60 * dpx
            drawCoin(c, cx - halfW * 0.4f, coinY.coerceAtLeast(8 * dpx), icon * 0.7f, now)
            outlined(c, "+$coinAmount", cx - halfW * 0.4f + 60 * dpx, coinY.coerceAtLeast(8 * dpx) + 36 * dpx, INK)
        }

        if (cut in 0..1000) cutInSign(c, cut / 1000f, groundY, cx.coerceIn(originX, width - rightReserved - 520 * dpx))
        if (cut in 0..950) faceCutIn(c, cut, groundY)

        if (party || sparks.isNotEmpty()) fireworks(c, now, dt, groundY, flagX)

        bubble(c, now, cx, top - icon * 0.5f * (sizeK - 1f), bottom)   // 큰 캐릭터(브라키오)는 고개를 들어도 말풍선에 머리가 안 가리게 더 위로
        // 사색: 식은땀 방울 + 덜덜 + 비명 (과속이 이어질 때)
        if (scared && driving) {
            val (sx0, sy0) = center()
            for (i in 0 until 3) {
                val ph = (((now / 14) + i * 33) % 100) / 100f
                val dx = (if (i % 2 == 0) -1 else 1) * (bodyW() * 0.35f + ph * 18 * dpx)
                val dy = -icon * 0.45f + ph * 40 * dpx
                fill.color = 0xFF7EC8FF.toInt()
                c.drawRect(sx0 + dx - 3 * dpx, sy0 + dy - 6 * dpx, sx0 + dx + 3 * dpx, sy0 + dy + 4 * dpx, fill)
                fill.color = PAPER
                c.drawRect(sx0 + dx - 1 * dpx, sy0 + dy - 4 * dpx, sx0 + dx + 1 * dpx, sy0 + dy - 1 * dpx, fill)
            }
            val tx = sx0 + bodyW() * 0.6f
            if (now > bubbleUntil && cut !in 0..1000) {                   // 말풍선·위험 컷인이 떠 있을 땐 숨긴다 (글씨 겹침 방지)
                outlined(c, if ((now / 300) % 2 == 0L) "으아아 너무 빨라요!" else "덜덜덜…", tx, sy0 - icon * 0.05f, 0xFF2D7BFF.toInt(), 22f)
                outlined(c, "과속 · 제한 ${speedLimit}km/h", tx, sy0 + icon * 0.3f, RED, 20f)
            }
        }
        // 들은 말 (마이크로 받아 적은 그대로 3초) — 어떤 말이 먹고 안 먹는지 바로 보인다
        if (heardText.isNotEmpty() && now - heardAt < 3000) {
            val s = "🎤 들은 말: “$heardText”"
            label.textSize = 24f * dpx
            val w = label.measureText(s) + 32 * dpx
            val hx = (width - w - 20 * dpx).coerceAtLeast(10 * dpx)
            val hy = groundY - icon - 150 * dpx
            fill.color = INK
            c.drawRect(hx - 3 * dpx, hy - 36 * dpx, hx + w + 3 * dpx, hy + 15 * dpx, fill)
            fill.color = PAPER
            c.drawRect(hx, hy - 33 * dpx, hx + w, hy + 12 * dpx, fill)
            label.style = Paint.Style.FILL
            label.color = INK
            c.drawText(s, hx + 16 * dpx, hy, label)
            label.textSize = 18f * dpx
        }

        // 차량 PC 부담을 줄이려고 움직일 때 초당 25장, 쉴 때 7장
        val busy = walking || now < bubbleUntil + 300 || cut < 1100 || ce < 1100 || alert || talking || party || sparks.isNotEmpty() || poofs.isNotEmpty() || raining || idleAct == "pounce" || now - landedAt < 500
        c.restore()
        postInvalidateDelayed(if (busy) 40 else 150)
    }

    /** "08:38 제보 · 4분 전" (확인으로 수명이 늘었으면 "확인 08:52 · 방금") — 분이 바뀔 때만 다시 만든다 */
    private val labelCache = HashMap<String, Pair<Long, String>>()
    private fun reportLabel(h: Hazard, wall: Long): String {
        val key = "${h.id}:${h.lastSeenAt}:${h.reports}"
        val minute = wall / 60_000L
        labelCache[key]?.let { if (it.first == minute) return it.second }
        val txt = "제보 ${h.reports}건 · " + if (h.lastSeenAt > h.reportedAt + 60_000L) "${agoText(h.lastSeenAt, wall)} 확인"
            else agoText(h.reportedAt, wall)
        labelCache[key] = minute to txt
        return txt
    }

    // ── 벽 타기: 등판 大자로 오르내리기 · 붙는 순간 철푸덕 ──
    private var climbStartAt = 0L
    private fun clingX(w: Float): Float = if (surf == Surf.LEFT) wallX + w * 0.5f - 6 * dpx else wallX - w * 0.5f + 6 * dpx

    private fun drawClimb(c: Canvas, cl: Bitmap, now: Long) {
        val fw = cl.width / 3
        val sc = icon / 24f                                        // 한 칸 = 24도트 기준 (꼬리용으로 아래가 더 긴 시트도 몸 크기는 같게)
        val w = fw * sc
        val x = clingX(w)
        val since = now - climbStartAt
        val idx = when {
            since < 260 -> 2                                       // 철푸덕: 쫙 붙은 순간
            speed > 0f -> ((now / 180) % 2).toInt()                // 팔다리 번갈아
            else -> 0
        }
        c.save()
        if (since < 160) c.scale(1.18f, 0.82f, x, py)             // 납작하게 붙었다가
        srcRect.set(idx * fw, 0, idx * fw + fw, cl.height)
        dst.set(x - w / 2, py - icon / 2, x + w / 2, py - icon / 2 + cl.height * sc)   // 몸은 그대로, 남는 줄(꼬리)은 아래로
        c.drawBitmap(cl, srcRect, dst, bmpPaint)
        c.restore()
        if (since < 600) outlined(c, "철푸덕!", x - 40 * dpx, py - icon * 0.7f, INK, 15f)
    }

    // ── 할퀸 자국: 벽을 타고 내려온 길에 발톱 세 줄 → 6초 뒤 사라짐 ──
    private class Scratch(val x: Float, val y0: Float, var y1: Float, var t: Long)
    private val scratches = ArrayList<Scratch>()
    private var lastPy = 0f

    // 티라노 발자국 (x, y, 위로 향하나, 찍은 시각) · 호박 잭이 뿌린 사탕
    private class Print(val x: Float, val y: Float, val up: Boolean, val t: Long)
    private val prints = ArrayList<Print>()
    private var lastPrintY = 0f
    private var printSide = 1
    private class Candy(var x: Float, var y: Float, var vy: Float, val color: Int, val t: Long, var landed: Boolean = false)
    private val candies = ArrayList<Candy>()
    private var lastCandyAt = 0L
    private var lastMarkFrame = 0L

    private fun drawScratches(c: Canvas, now: Long) {
        val cl = climbSheet
        val onWall = act == Act.ROAM && (surf == Surf.LEFT || surf == Surf.RIGHT)
        val dt = ((now - lastMarkFrame).coerceIn(0, 100)) / 1000f
        lastMarkFrame = now
        if (charName == "trex" || charName == "pumpkin") {
            val w = cl?.let { (it.width / 3) * (icon / 24f) } ?: icon
            if (onWall && charName == "trex" && abs(py - lastPrintY) > 30 * dpx) {           // 쿵쿵: 한 발씩 번갈아 찍힌다
                printSide = -printSide
                prints += Print(clingX(w) + printSide * 11 * dpx, py + icon * 0.3f, py < lastPrintY, now)
                lastPrintY = py
            }
            if (onWall && charName == "pumpkin" && speed > 0f && now - lastCandyAt > 220) {   // 오르며 사탕 뿌리기
                lastCandyAt = now
                candies += Candy(clingX(w) + (Random.nextFloat() - 0.5f) * 30 * dpx, py, -80 * dpx, CANDY[Random.nextInt(CANDY.size)], now)
            }
            if (!onWall) lastPrintY = py
            prints.removeAll { now - it.t > 6000 }
            for (pr in prints) {
                val a = (1f - (now - pr.t) / 6000f).coerceIn(0f, 1f)
                fill.color = 0xFF3E4A3A.toInt()
                fill.alpha = (a * 200).toInt()
                val sg = if (pr.up) -1f else 1f                   // 발가락이 가는 쪽으로
                val u = 1.3f * dpx
                c.drawRect(pr.x - 3 * u, pr.y - 2 * u, pr.x + 3 * u, pr.y + 3 * u, fill)                       // 뒤꿈치
                c.drawRect(pr.x - u, minOf(pr.y, pr.y + sg * 11 * u), pr.x + u, maxOf(pr.y, pr.y + sg * 11 * u), fill)   // 가운데 발가락
                for (k in 0..3) for (side in intArrayOf(-1, 1)) {                                              // 양옆 발가락 (벌어지게)
                    val x0 = pr.x + side * (2 + k * 1.6f) * u
                    val y0 = pr.y + sg * (2 + k * 2) * u
                    c.drawRect(minOf(x0, x0 + side * 2 * u), minOf(y0, y0 + sg * 2 * u), maxOf(x0, x0 + side * 2 * u), maxOf(y0, y0 + sg * 2 * u), fill)
                }
                fill.alpha = 255
            }
            val ground = height - 4f * dpx - PetScale.stageGroundLift
            candies.removeAll { now - it.t > 6000 }
            for (cd in candies) {
                if (!cd.landed) {
                    cd.vy += 1400 * dpx * dt
                    cd.y += cd.vy * dt
                    if (cd.y >= ground - 4 * dpx) { cd.y = ground - 4 * dpx; cd.landed = true }
                }
                val a = (1f - (now - cd.t) / 6000f).coerceIn(0f, 1f)
                fill.color = cd.color; fill.alpha = (a * 255).toInt()
                c.drawRect(cd.x - 4 * dpx, cd.y - 3 * dpx, cd.x + 4 * dpx, cd.y + 3 * dpx, fill)
                fill.color = 0xFFFFE0B2.toInt(); fill.alpha = (a * 255).toInt()
                c.drawRect(cd.x - 7 * dpx, cd.y - 2 * dpx, cd.x - 4 * dpx, cd.y + 2 * dpx, fill)
                c.drawRect(cd.x + 4 * dpx, cd.y - 2 * dpx, cd.x + 7 * dpx, cd.y + 2 * dpx, fill)
                fill.alpha = 255
            }
            lastPy = py
            return
        }
        if (onWall && py > lastPy + 0.3f) {                       // 내려가는 중
            val w = cl?.let { (it.width / 3) * (icon / 24f) } ?: icon
            val sx = clingX(w)
            val open = scratches.lastOrNull()?.takeIf { now - it.t < 300 && abs(it.x - sx) < 4 * dpx }
            if (open != null) { open.y1 = py + icon * 0.3f; open.t = now } else scratches += Scratch(sx, lastPy + icon * 0.3f, py + icon * 0.3f, now)
        }
        lastPy = py
        scratches.removeAll { now - it.t > 6000 }
        for (sc in scratches) {
            val a = (1f - (now - sc.t) / 6000f).coerceIn(0f, 1f)
            fill.color = 0xFF4A4A52.toInt()
            fill.alpha = (a * 210).toInt()
            // 두 앞발이 나란히: 발마다 발톱 세 줄 (가운데 줄이 조금 더 길고, 왼발·오른발 높이가 살짝 어긋남)
            for ((paw, lag) in listOf(-16f to 0f, 16f to 10f)) {
                for (k in -1..1) {
                    val x = sc.x + paw * dpx + k * 5 * dpx
                    val top = sc.y0 + (abs(k) * 5 + lag) * dpx
                    c.drawRect(x, top, x + 2 * dpx, sc.y1 - abs(k) * 4 * dpx + lag * dpx * 0.5f, fill)
                }
            }
            fill.alpha = 255
        }
    }

    // ── 냥냥 펀치: 맞는 순간 도트 불꽃 + "퍽!" (킹오파 히트 스파크처럼) ──
    private val punched = HashSet<String>()
    private var punchAt = -10_000L
    private var shakeUntil = 0L

    private fun hitSpark(c: Canvas, pe: Long, x: Float, y: Float, z: Float, word: String = "퍽!") {
        val p = pe / 360f
        val r = (14 + 70 * p) * dpx * z.coerceAtMost(1.6f)
        for (k in 0 until 8) {
            val a = k * Math.PI / 4 + 0.3
            val sz = dot * (2.2f - 1.6f * p)
            fill.color = if (k % 2 == 0) PAPER else GOLD
            val ox = x + (cos(a) * r).toFloat()
            val oy = y + (sin(a) * r).toFloat()
            c.drawRect(ox - sz / 2, oy - sz / 2, ox + sz / 2, oy + sz / 2, fill)
        }
        if (p < 0.35f) {                                           // 한가운데 번쩍
            fill.color = PAPER
            c.drawRect(x - 10 * dpx, y - 10 * dpx, x + 10 * dpx, y + 10 * dpx, fill)
        }
        val pop = if (p < 0.25f) 0.6f + p / 0.25f * 0.6f else 1.2f - (p - 0.25f) * 0.25f
        c.save()
        c.scale(pop, pop, x, y - 60 * dpx)
        outlined(c, word, x - 24 * dpx, y - 60 * dpx, RED, 36f)
        c.restore()
    }

    // ── 필살기 상태 ──
    private var attackId: String? = null
    private var attackM = 0.0
    private var attackAt = 0L
    private var attackKind = "punch"
    private var hitAt = 0L
    private var hitWord = ""
    private var hitX = 0f
    private var hitY = 0f

    /** 기술별 연출 (pe = 시작 뒤 ms, impact = 맞는 순간) */
    private fun attackFx(c: Canvas, kind: String, pe: Long, impact: Long, hx: Float, groundY: Float, catX: Float) {
        val k = (pe.toFloat() / impact).coerceIn(0f, 1f)
        val cy = groundY - icon / 2
        val tx = hx; val ty = groundY - icon * 0.55f
        fun boom(x: Float, y: Float) {
            val q = ((pe - impact) / 400f).coerceIn(0f, 1f)
            if (pe < impact || q >= 1f) return
            for (i in 0 until 10) {
                val a = i * Math.PI / 5
                val r = (20 + q * 90) * dpx
                fill.color = if (i % 2 == 0) 0xFFFF6A00.toInt() else 0xFFFFC107.toInt()
                val sz = (14 - q * 10) * dpx
                c.drawRect(x + (cos(a) * r).toFloat() - sz / 2, y + (sin(a) * r).toFloat() - sz / 2, x + (cos(a) * r).toFloat() + sz / 2, y + (sin(a) * r).toFloat() + sz / 2, fill)
            }
        }
        when (kind) {
            "lick" -> if (pe < impact + 150) {                       // 강아지: 혀가 쭉 → 할짝
                val mx = catX + bodyW() * 0.45f
                val len = (tx - mx) * (if (pe < impact) k else 1f - ((pe - impact) / 150f))
                fill.color = 0xFFFF7A9A.toInt()
                c.drawRoundRect(mx, cy - 2 * dpx, mx + len, cy + 8 * dpx, 6 * dpx, 6 * dpx, fill)
                if (pe > impact - 100) outlined(c, "♥", tx, ty - 40 * dpx, 0xFFFF4F7A.toInt(), 28f)
            }
            "kick" -> {                                                // 말: 지나간 뒤 뒷발로 뻥 (먼지 줄)
                fill.color = 0x99A08060.toInt()
                for (i in 0 until 4) c.drawRect(catX - bodyW() * 0.6f - i * 18 * dpx, groundY - (10 + i * 8) * dpx, catX - bodyW() * 0.6f - i * 18 * dpx + 12 * dpx, groundY - (6 + i * 8) * dpx, fill)
                if (pe < impact + 200) outlined(c, "뒷발 차기!", catX - bodyW(), groundY - icon * 1.2f, 0xFFA0522D.toInt(), 20f)
            }
            "roar" -> {                                                // 사자: 어흥 충격파 동그라미
                fill.style = Paint.Style.STROKE; fill.strokeWidth = 5 * dpx; fill.color = 0xAAE0A030.toInt()
                for (i in 0 until 3) {
                    val r = ((k * 1.2f - i * 0.25f).coerceIn(0f, 1f)) * (tx - catX)
                    if (r > 0) c.drawArc(catX - r, cy - r, catX + r, cy + r, -40f, 80f, false, fill)
                }
                fill.style = Paint.Style.FILL
                if (pe < impact) outlined(c, "어흥!", catX, cy - icon, 0xFFB8561A.toInt(), 24f)
            }
            "meteor" -> {                                              // 비행접시: 하늘에서 메테오 쾅
                if (pe < impact) {
                    val mx = tx + (1 - k) * 260 * dpx
                    val my = ty - (1 - k) * 600 * dpx
                    for (i in 1..6) {
                        fill.color = if (i % 2 == 0) 0x88FF6A00.toInt() else 0x88FFC107.toInt()
                        val r = (16 - i * 2) * dpx
                        c.drawCircle(mx + i * 18 * dpx, my - i * 40 * dpx, r, fill)
                    }
                    fill.color = 0xFF6D4C41.toInt(); c.drawCircle(mx, my, 18 * dpx, fill)
                    fill.color = 0xFFFF7043.toInt(); c.drawCircle(mx - 4 * dpx, my - 4 * dpx, 8 * dpx, fill)
                    outlined(c, "메테오!", catX - 40 * dpx, cy - icon * 1.1f, 0xFF5FBF7A.toInt(), 22f)
                }
                boom(tx, ty)
            }
            "ladder" -> if (pe < impact + 300) {                       // 헬기: 줄사다리를 휙 휘둘러 철썩
                val top = catX to (cy + 10 * dpx)
                val swing = if (pe < impact) -50f + 65f * k else 15f - 15f * ((pe - impact) / 300f)
                val len = hypot(tx - top.first, ty - top.second)
                c.save(); c.rotate(-90f + swing, top.first, top.second)
                fill.color = 0xFF8D6E63.toInt()
                c.drawRect(top.first - 10 * dpx, top.second, top.first - 7 * dpx, top.second + len, fill)
                c.drawRect(top.first + 7 * dpx, top.second, top.first + 10 * dpx, top.second + len, fill)
                var yy = top.second + 14 * dpx
                while (yy < top.second + len) { c.drawRect(top.first - 10 * dpx, yy, top.first + 10 * dpx, yy + 3 * dpx, fill); yy += 18 * dpx }
                c.restore()
            }
            "missile" -> {                                             // 비행기: 미사일 슈웅 → 펑
                if (pe < impact) {
                    val sx = catX + bodyW() * 0.3f
                    val mx = sx + (tx - sx) * k
                    val my = cy - 20 * dpx + (ty - cy + 20 * dpx) * k - sin(k * Math.PI).toFloat() * 60 * dpx
                    fill.color = 0x88DDDDDD.toInt()
                    for (i in 1..6) c.drawCircle(mx - i * 16 * dpx, my + i * 2 * dpx, (10 - i) * dpx, fill)
                    fill.color = 0xFF90A4AE.toInt(); c.drawRect(mx - 22 * dpx, my - 5 * dpx, mx + 8 * dpx, my + 5 * dpx, fill)
                    fill.color = 0xFFE53935.toInt(); c.drawRect(mx + 8 * dpx, my - 4 * dpx, mx + 16 * dpx, my + 4 * dpx, fill)
                    outlined(c, "슈웅~", sx, cy - icon, 0xFF2F80ED.toInt(), 20f)
                }
                boom(tx, ty)
            }
            "fire" -> if (pe < impact + 200) {                         // 용: 불꽃 브레스
                for (i in 0 until 10) {
                    val ph = ((pe / 14 + i * 11) % 100) / 100f * k.coerceAtLeast(0.2f)
                    fill.color = if (i % 3 == 0) 0xFFFFC107.toInt() else 0xFFFF5722.toInt()
                    val x = catX + bodyW() * 0.4f + (tx - catX) * ph
                    val sz = (6 + ph * 16) * dpx
                    c.drawRect(x - sz / 2, cy - 10 * dpx - sz / 2, x + sz / 2, cy - 10 * dpx + sz / 2, fill)
                }
            }
            "possess" -> if (pe < impact + 200) {                      // 유령: 카메라에 쏙 빙의
                fill.color = 0x669E8CE0.toInt()
                c.drawCircle(catX + (tx - catX) * k, cy, 30 * dpx, fill)
                outlined(c, "빙의~", tx - 20 * dpx, ty - 50 * dpx, 0xFF6A5ACD.toInt(), 20f)
            }
            "spell" -> {                                               // 마녀: 별 마법 → 개구리로!
                if (pe < impact) {
                    val x = catX + (tx - catX) * k
                    val y = cy - sin(k * Math.PI).toFloat() * 80 * dpx
                    sparkle(c, x, y, 14 * dpx, 0xFFFFD23F.toInt())
                    outlined(c, "수리수리 마수리!", catX - 40 * dpx, cy - icon * 1.1f, 0xFF7B3FC4.toInt(), 20f)
                } else if (pe < impact + 450) outlined(c, "🐸 개구리로 변해라!", tx - 60 * dpx, ty - 60 * dpx, 0xFF43A047.toInt(), 22f)
                boom(tx, ty)
            }
            "ram", "headbutt" -> if (pe < impact) outlined(c, if (kind == "ram") "돌진!" else "통!", catX, cy - icon, RED, 20f)
            "stomp" -> {                                               // 브라키오: 앞발 번쩍 → 쿵! (그림자가 커지다 먼지 고리)
                if (pe < impact) {
                    fill.color = 0x55000000
                    val r = (10 + k * 34) * dpx
                    c.drawOval(tx - r, groundY - r * 0.25f, tx + r, groundY + r * 0.25f, fill)
                    outlined(c, "번쩍~", catX - 10 * dpx, cy - icon * 1.15f, 0xFF6A5ACD.toInt(), 20f)
                } else if (pe < impact + 380) {
                    val q = (pe - impact) / 380f
                    fill.color = 0x99A08060.toInt()
                    for (i in 0 until 10) {
                        val a = i * Math.PI / 9
                        val rr = (30 + q * 110) * dpx
                        c.drawRect(tx + (cos(a) * rr).toFloat() - 5 * dpx, groundY - (sin(a) * rr * 0.35f).toFloat() - 5 * dpx, tx + (cos(a) * rr).toFloat() + 5 * dpx, groundY - (sin(a) * rr * 0.35f).toFloat() + 5 * dpx, fill)
                    }
                }
            }
            "bite" -> if (pe < impact + 150) {                          // 티라노: 큰 입으로 와작
                fill.color = PAPER
                val mx = catX + bodyW() * 0.5f
                for (k in 0 until 4) c.drawRect(mx + k * 10 * dpx, cy - 16 * dpx, mx + k * 10 * dpx + 6 * dpx, cy - 6 * dpx, fill)
                outlined(c, "아~앙", catX, cy - icon, RED, 20f)
            }
            else -> Unit
        }
    }

    /** 충격 별 (뾰족뾰족 8갈래) */
    private fun impactStar(c: Canvas, x: Float, y: Float, r: Float, color: Int) {
        val path = android.graphics.Path()
        for (i in 0 until 16) {
            val a = i * Math.PI / 8
            val rr = if (i % 2 == 0) r else r * 0.45f
            val px2 = x + (cos(a) * rr).toFloat(); val py2 = y + (sin(a) * rr).toFloat()
            if (i == 0) path.moveTo(px2, py2) else path.lineTo(px2, py2)
        }
        path.close()
        fill.color = INK; c.save(); c.scale(1.12f, 1.12f, x, y); c.drawPath(path, fill); c.restore()
        fill.color = color; c.drawPath(path, fill)
        fill.color = PAPER; c.drawCircle(x, y, r * 0.22f, fill)
    }

    /** 박치기 받을 바위 */
    private fun rock(c: Canvas, x: Float, ground: Float, r: Float) {
        fill.color = INK
        c.drawOval(x - r - 3 * dpx, ground - r * 1.4f - 3 * dpx, x + r + 3 * dpx, ground + 1 * dpx, fill)
        fill.color = 0xFF8D8D95.toInt()
        c.drawOval(x - r, ground - r * 1.4f, x + r, ground, fill)
        fill.color = 0xFFB7B7BF.toInt()
        c.drawOval(x - r * 0.6f, ground - r * 1.25f, x - r * 0.05f, ground - r * 0.8f, fill)
    }

    /** 펀치 맞은 표시가 빙글빙글 날아간다 */
    private class Flyer(val pic: List<String>, var x: Float, var y: Float, var vx: Float, var vy: Float, val at: Long, var rot: Float = 0f, val type: HazardType? = null)
    private val flyers = ArrayList<Flyer>()

    private fun flyAway(c: Canvas, now: Long, dt: Float) {
        val it = flyers.iterator()
        while (it.hasNext()) {
            val f = it.next()
            f.vy += 1700 * dpx * dt
            f.x += f.vx * dt
            f.y += f.vy * dt
            f.rot += 900f * dt
            if (now - f.at > 1600 || f.y > height + icon) { it.remove(); continue }
            c.save()
            c.rotate(f.rot, f.x + icon / 2, f.y + icon / 2)
            if (f.type != null) drawHazard(c, f.type, f.x, f.y, now) else sprite(c, f.pic, f.x, f.y, icon / f.pic.size, false)
            c.restore()
        }
    }

    private fun easeOutBack(t: Float): Float {
        val k = 1.70158f
        val u = t - 1f
        return 1f + (k + 1f) * u * u * u + k * u * u
    }

    /** 단속카메라·어린이 보호구역은 평소엔 숨기고, 달리면서 1km 안으로 다가올 때만 보인다 */
    private fun showNow(h: Hazard): Boolean = h.type !in DRIVING_ONLY || (driving && h.atM - posM <= 1000)

    // ── 주차 중 동작: 세수 · 기지개 · 밥 먹기 · 자기 · 손 흔들기 · 덮치기 (+ 착지) ──
    private var idleAct: String? = null
    private var idleActAt = 0L
    private var idleUntil = 0L
    private var landedAt = -10_000L
    private var partyAct: String? = null
    /** 습성 동작 전용 그림 (티라노 고기 삼키기 · 트리케라 박치기 …) — 없으면 몸을 움직이는 동작만 */
    private val procSheets = HashMap<String, Bitmap>()
    /** 쿵! 화면 흔들기는 동작 한 번에 한 번만 */
    private var procHitFor = -1L
    private fun shakeOnce(ms: Long = 240) {
        if (procHitFor == idleActAt) return
        procHitFor = idleActAt
        shakeUntil = SystemClock.uptimeMillis() + ms
    }

    /** 캐릭터를 막 골랐을 때: 그 자리에서 멈춰 장기 하나를 선보인다 */
    fun showcase() {
        val now = SystemClock.uptimeMillis()
        if (driving || act != Act.ROAM || surf != Surf.FLOOR) return
        speed = 0f
        val sheetPool = IDLE_ACTS.keys.filter { it in actSheets && it != "sleep" }
        if (sheetPool.isNotEmpty()) {
            val k = sheetPool.random()
            idleAct = k; idleActAt = now; idleUntil = now + (IDLE_ACTS[k]?.second ?: 2500L).coerceAtMost(3600L)
        } else {
            val acts = procActs() ?: return
            val sig = SIGNATURE[charName]
            val (name, dur) = if (sig != null && Random.nextFloat() < 0.65f) (acts.firstOrNull { it.first == sig } ?: acts.random()) else acts.random()
            idleAct = "p_$name"; idleActAt = now; idleUntil = now + dur
            maybeFact(name, now, 0.6f)
            actSound(name, now)
        }
        nextDecision = idleUntil
        invalidate()
    }

    private var lastFactAt = -60_000L

    /** 고를 수 있는 습성 동작 — 공룡의 눕기·고개 숙이기 같은 자세는 그림이 있을 때만 (몸 기울이기로 흉내 내지 않는다) */
    private fun procActs(): List<Pair<String, Long>>? =
        PROC_ACTS[charName]?.filter { (k, _) -> charName !in DINOS || k !in NEEDS_SHEET || procSheets.containsKey(k) }?.ifEmpty { null }
    /** 동작 소리를 낼 때 (기분: talk·alert·happy) — PetOverlay가 그 캐릭터 울음으로 낸다 */
    var onActSound: ((String) -> Unit)? = null
    private var lastActSoundAt = -60_000L
    private fun actSound(act: String, now: Long) {
        val mood = ACT_SOUND[act] ?: return
        if (driving || now - lastActSoundAt < 6000) return
        lastActSoundAt = now
        onActSound?.invoke(mood)
    }

    /** 동작에 맞는 고증 한 줄 — 공룡은 '공룡 TMI', 가끔은 아이들 안전 TMI */
    private fun maybeFact(act: String, now: Long, chance: Float) {
        if (driving || now - lastFactAt < 20_000 || now < bubbleUntil) return
        val actFact = ACT_FACTS["$charName:$act"]
        val (tag, fact) = when {
            actFact != null && Random.nextFloat() < chance + 0.35f -> (if (charName in DINOS) "공룡 TMI" else "TMI 한 줄") to actFact
            Random.nextFloat() < chance * 0.4f -> "안전 TMI" to SAFETY.random()
            else -> return
        }
        lastFactAt = now
        say(tag, fact, false)
    }

    private fun startIdle(now: Long) {
        val pool = IDLE_ACTS.filterKeys { it in actSheets }
        if (pool.isEmpty()) {
            // 그림 시트가 없는 캐릭터: 동물 습성·기계 특기대로 몸을 움직이는 동작
            val acts = procActs()
            if (acts == null || Random.nextFloat() < 0.12f) { idleAct = null; return }
            val sig = SIGNATURE[charName]
            val (name, dur) = if (sig != null && Random.nextFloat() < 0.3f) (acts.firstOrNull { it.first == sig } ?: acts.random()) else acts.random()
            idleAct = "p_$name"; idleActAt = now; idleUntil = now + dur
            maybeFact(name, now, 0.25f)
            actSound(name, now)
            return
        }
        if (Random.nextFloat() < 0.15f) { idleAct = null; return }   // 가끔은 그냥 앉아 있기
        var r = Random.nextFloat() * pool.values.sumOf { it.first.toDouble() }.toFloat()
        val pick = pool.entries.first { r -= it.value.first; r <= 0f }
        idleAct = pick.key
        idleActAt = now
        idleUntil = now + pick.value.second
        maybeFact(pick.key, now, 0.25f)
        actSound(pick.key, now)
    }

    /** 동작 중 몸 자세: 옮김(dx,dy) · 회전(도) · 늘림(sx,sy) · 다리 움직임 */
    private class ProcPose(val dx: Float = 0f, val dy: Float = 0f, val rot: Float = 0f, val sx: Float = 1f, val sy: Float = 1f, val moving: Boolean = false)

    private fun procPose(a: String, p: Float, now: Long): ProcPose {
        val pi = Math.PI.toFloat()
        val wave = sin(p * pi)                                       // 0 → 1 → 0
        return when (a) {
            // 강아지
            "chase" -> ProcPose(rot = p * 720f, moving = true)                        // 제 꼬리 쫓아 빙글빙글
            "wag" -> ProcPose(rot = sin(now / 60.0).toFloat() * 4f, dy = -abs(sin(now / 120.0)).toFloat() * 4 * dpx)
            "dig" -> ProcPose(rot = 14f, dy = 4 * dpx, moving = true)                  // 앞으로 숙여 파기
            "sniff" -> ProcPose(rot = 10f + sin(now / 90.0).toFloat() * 3f, dx = p * 30 * dpx, moving = true)
            "scratch" -> ProcPose(rot = -6f + sin(now / 40.0).toFloat() * 3f)         // 뒷발로 귀 긁기
            "bow" -> ProcPose(rot = 16f * wave, sx = 1f + 0.06f * wave)                // 놀자! 엎드려 절하기
            "howl" -> ProcPose(rot = -22f * wave, sy = 1f + 0.08f * wave)
            "rollover" -> ProcPose(rot = 180f * wave, dy = -10 * dpx * wave)
            // 사자
            "roar" -> ProcPose(sx = 1f + 0.1f * wave, sy = 1f + 0.1f * wave, dx = sin(now / 30.0).toFloat() * 2 * dpx)
            "yawn" -> ProcPose(rot = -10f * wave, sy = 1f + 0.12f * wave)
            "nap" -> ProcPose(sy = 0.78f, dy = 6 * dpx)                                // 하루 20시간 자는 사자
            "stalk" -> ProcPose(sy = 0.82f, sx = 1.08f, dy = 5 * dpx, dx = p * 60 * dpx, moving = true)
            "mane" -> ProcPose(rot = sin(now / 35.0).toFloat() * 6f)
            "claws" -> ProcPose(rot = -18f, sy = 1.06f, dx = sin(now / 50.0).toFloat() * 3 * dpx)
            // 말
            "rear" -> ProcPose(rot = -28f * wave, dy = -18 * dpx * wave)               // 앞발 들고 히잉
            "graze" -> ProcPose(rot = 16f, dy = 3 * dpx + sin(now / 300.0).toFloat() * 2 * dpx)
            "swish" -> ProcPose(rot = sin(now / 140.0).toFloat() * 2f)
            "dustroll" -> ProcPose(rot = 200f * wave, dy = 6 * dpx)
            "stomp" -> ProcPose(dy = -abs(sin(now / 70.0)).toFloat() * 6 * dpx)
            "doze" -> ProcPose(rot = 7f, sy = 0.97f)                                   // 선 채로 졸기
            // 스포츠카
            "drift" -> ProcPose(rot = p * 360f, dx = wave * 40 * dpx)
            "honk" -> ProcPose(sx = 1f + 0.08f * abs(sin(now / 60.0)).toFloat(), sy = 1f + 0.08f * abs(sin(now / 60.0)).toFloat())
            "flash" -> ProcPose(dy = -abs(sin(now / 200.0)).toFloat() * 2 * dpx)
            "hop" -> ProcPose(dy = -60 * dpx * wave, sy = if (p > 0.9f) 0.85f else 1f)
            "nitro" -> ProcPose(dx = sin(p * pi * 2) * 70 * dpx + sin(now / 25.0).toFloat() * 2 * dpx, moving = true)
            "wheelie" -> ProcPose(rot = -16f * wave, dy = -6 * dpx * wave, moving = true)
            // 비행기
            // 큰 원 그리며 날기 — 뒤집지 않고, 돌아올 땐 방향만 바꾼다
            "loop" -> {
                val back = kotlin.math.cos(p * pi * 2) < 0
                ProcPose(dx = sin(p * pi * 2) * 110 * dpx, dy = -(1 - kotlin.math.cos(p * pi * 2)) * 55 * dpx,
                    rot = (if (back) -1f else 1f) * kotlin.math.cos(p * pi * 2 + pi / 2) * 12f, sx = if (back) -1f else 1f, moving = true)
            }
            // 유턴: 옆으로 슥 돌아선다 (몸이 좁아졌다 반대로 펴짐) → 끝나면 반대 방향
            "uturn" -> ProcPose(dy = -sin(p * pi) * 50 * dpx, sx = kotlin.math.cos(p * pi), moving = true)
            // 8자 비행: 가는 쪽을 보고 살짝만 기울인다 (뒤집지 않음)
            "eight" -> {
                val vx = kotlin.math.cos(p * pi * 2)
                val vy = -kotlin.math.cos(p * pi * 4) * 0.7f
                ProcPose(dx = sin(p * pi * 2) * 100 * dpx, dy = -sin(p * pi * 4) * 35 * dpx - 40 * dpx * sin(p * pi),
                    rot = (vy * 20f).coerceIn(-20f, 20f) * (if (vx < 0) -1f else 1f), sx = if (vx < 0) -1f else 1f, moving = true)
            }
            // 날개 까딱 인사 (배럴 롤 대신)
            "roll" -> ProcPose(rot = sin(now / 120.0).toFloat() * 14f, dy = -sin(p * pi) * 20 * dpx, moving = true)
            "smoke" -> ProcPose(dx = sin(p * pi * 2) * 90 * dpx, dy = -wave * 50 * dpx, moving = true)
            // 헬기
            "spin" -> ProcPose(sx = kotlin.math.cos(p * pi * 4), moving = true)
            "search" -> ProcPose(dy = -40 * dpx * wave, moving = true)
            "hover" -> ProcPose(dy = -70 * dpx * wave + sin(now / 150.0).toFloat() * 6 * dpx, moving = true)
            // 비행접시
            "beam" -> ProcPose(dy = -60 * dpx * wave, moving = true)
            "zigzag" -> ProcPose(dx = sin(p * pi * 6) * 70 * dpx, dy = -abs(sin(p * pi * 3)) * 40 * dpx, moving = true)
            "wobble" -> ProcPose(rot = sin(now / 80.0).toFloat() * 14f, moving = true)
            "alien" -> ProcPose(dy = -30 * dpx * min(1f, wave * 3f) + sin(now / 200.0).toFloat() * 4 * dpx, moving = true)
            "lights" -> ProcPose(dy = sin(now / 220.0).toFloat() * 5 * dpx, moving = true)
            "teleport" -> {                                                              // 슝 사라졌다 저쪽에 나타났다 다시 돌아오기
                val k = when { p < 0.2f -> 1f - p / 0.2f; p < 0.3f -> 0f; p < 0.45f -> (p - 0.3f) / 0.15f; p < 0.55f -> 1f; p < 0.7f -> 1f - (p - 0.55f) / 0.15f; p < 0.8f -> 0f; else -> (p - 0.8f) / 0.2f }
                ProcPose(dx = if (p in 0.25f..0.75f) 160 * dpx else 0f, sx = k, sy = k, moving = true)
            }
            // 비행기: 날개 흔들어 인사 (조종사 신호) · 터치 앤 고 (착륙 연습)
            "rock" -> ProcPose(rot = sin(now / 150.0).toFloat() * 16f * wave, dy = -wave * 30 * dpx, moving = true)
            "touchgo" -> ProcPose(dy = (lift - 6 * dpx) * smooth(1f - abs(p - 0.5f) / 0.3f), rot = if (p < 0.5f) 5f * wave else -9f * wave, moving = true)
            // 헬기: 앞으로 기울여야 앞으로 간다 · 구조 바구니 · 산불 물주머니
            "tilt" -> ProcPose(dx = sin(p * pi) * 100 * dpx, rot = 14f * kotlin.math.cos(p * pi) * min(1f, wave * 3f), moving = true)
            "hoist", "bucket" -> ProcPose(dy = -40 * dpx * min(1f, wave * 3f) + sin(now / 150.0).toFloat() * 4 * dpx, moving = true)
            // 용: 콧김 · 여의주 · 보물 지키며 꾸벅
            "snort" -> ProcPose(rot = -6f * wave)
            "pearl" -> ProcPose(dy = sin(now / 260.0).toFloat() * 8 * dpx, rot = sin(now / 300.0).toFloat() * 5f, moving = true)
            "hoard" -> { val land = smooth(min(1f, p / 0.2f)) * smooth(min(1f, (1f - p) / 0.15f)); ProcPose(dy = (lift - 2 * dpx) * land, sy = 1f - 0.05f * land) }
            // 유령: 유령 떼 소동 · 도깨비불 · 까꿍 · 으스스 입김
            "swarm" -> ProcPose(dy = -30 * dpx * wave, sx = 1f + 0.1f * wave, sy = 1f + 0.1f * wave, moving = true)
            "wisp" -> ProcPose(dy = sin(now / 300.0).toFloat() * 6 * dpx, moving = true)
            "peekaboo" -> {
                val k = when { p < 0.3f -> 1f - 0.9f * smooth(p / 0.3f); p < 0.7f -> 0.1f; p < 0.8f -> 0.1f + 1.2f * smooth((p - 0.7f) / 0.1f); else -> 1.3f - 0.3f * smooth((p - 0.8f) / 0.2f) }
                ProcPose(dx = if (p in 0.3f..0.75f) 70 * dpx else if (p > 0.75f) 70 * dpx * (1f - smooth((p - 0.75f) / 0.25f)) else 0f, sx = k, sy = k, moving = true)
            }
            "chill" -> ProcPose(sx = 1f + 0.06f * wave, moving = true)
            // 호박: 데굴데굴 · 호박씨 퉤 · 촛불 깜빡 웃음
            "tumble" -> ProcPose(rot = p * 720f, dx = sin(p * pi) * 120 * dpx, moving = true)
            "seeds" -> ProcPose(rot = if ((now / 300) % 2 == 0L) -6f else 2f)
            "grin" -> ProcPose(sx = 1f + 0.06f * abs(sin(now / 150.0)).toFloat(), sy = 1f + 0.06f * abs(sin(now / 150.0)).toFloat())
            // 마녀 고양이: 빗자루 청소 · 물약 · 보름달 산책 · 모자 인사
            "sweep" -> { val land = smooth(min(1f, p / 0.15f)) * smooth(min(1f, (1f - p) / 0.15f)); ProcPose(dy = (lift - 2 * dpx) * land, dx = sin(now / 200.0).toFloat() * 10 * dpx * land, rot = sin(now / 200.0).toFloat() * 10f * land, moving = true) }
            "potion" -> ProcPose(dy = sin(now / 250.0).toFloat() * 5 * dpx, rot = sin(now / 180.0).toFloat() * 6f, moving = true)
            "moon" -> ProcPose(dx = (p - 0.5f) * 300 * dpx * min(1f, wave * 2.5f), dy = -140 * dpx * min(1f, wave * 2f), moving = true)
            "hattip" -> ProcPose(rot = 14f * wave)
            // 용
            "fire" -> ProcPose(rot = -8f * wave, sx = 1f + 0.05f * wave, moving = true)
            "flap" -> ProcPose(dy = -80 * dpx * wave, moving = true)
            // 할로윈
            // 공룡
            "chomp" -> ProcPose(rot = if ((now / 120) % 2 == 0L) -10f else 4f, sx = 1.05f)              // 와작와작
            "charge" -> ProcPose(dx = sin(p * pi) * 90 * dpx, rot = 8f * wave, moving = true)            // 머리 숙여 돌진했다 돌아오기
            "headshake" -> ProcPose(rot = sin(now / 60.0).toFloat() * 8f)
            "shortarms" -> ProcPose(rot = sin(now / 90.0).toFloat() * 3f, dy = -abs(sin(now / 160.0)).toFloat() * 3 * dpx)
            "meat" -> when {
                p < 0.18f -> ProcPose()
                p < 0.7f -> ProcPose(rot = if ((now / 160) % 2 == 0L) -6f else 3f, dx = if ((now / 160) % 2 == 0L) 4 * dpx else 0f)   // 우걱우걱 고개 흔들며 뜯기
                p < 0.82f -> ProcPose(rot = -14f * sin(((p - 0.7f) / 0.12f) * pi))                                                   // 고개 젖혀 꿀꺽
                else -> ProcPose(sy = 1f + 0.04f * sin(((p - 0.82f) / 0.18f) * pi))
            }
            "headbutt" -> when {                                                        // 뒤로 힘 모으기 → 돌진 → 쾅 → 돌아오기
                p < 0.35f -> { val k = p / 0.35f; ProcPose(dx = -22 * dpx * k, rot = -14f * k) }
                p < 0.5f -> { val k = (p - 0.35f) / 0.15f; ProcPose(dx = (-22 + 92 * k) * dpx, rot = -14f + 24f * k, moving = true) }
                p < 0.62f -> ProcPose(dx = 70 * dpx, rot = 10f, sx = 0.9f, sy = 1.06f)
                else -> { val k = (p - 0.62f) / 0.38f; ProcPose(dx = 70 * dpx * (1 - k), rot = 10f * (1 - k), moving = true) }
            }
            "wallow" -> ProcPose(sy = 0.86f, dy = 5 * dpx, rot = sin(now / 200.0).toFloat() * 6f)     // 진흙 목욕
            "sunbask" -> ProcPose(sy = 1f + 0.02f * sin(now / 400.0).toFloat())                       // 등판에 햇볕
            "drink" -> ProcPose(rot = 6f * wave)
            "fisheat" -> ProcPose(dy = -24 * dpx * wave, rot = -8f * wave)
            "perch" -> {                                                                 // 내려앉아 네 발로 뒤뚱 (익룡의 실제 걸음)
                val land = smooth(min(1f, p / 0.2f)) * smooth(min(1f, (1f - p) / 0.2f))
                ProcPose(dy = (lift - 4 * dpx) * land, dx = p * 40 * dpx, moving = land > 0.95f)
            }
            "reach" -> ProcPose(rot = -12f * wave, sy = 1f + 0.18f * wave, dy = -4 * dpx * wave)       // 목을 쭉 빼서 높은 잎
            "bellow" -> ProcPose(rot = -18f * wave, sy = 1f + 0.06f * wave)                              // 고개 들고 뿌우~
            "tailswing" -> ProcPose(rot = sin(now / 110.0).toFloat() * 12f, dx = sin(now / 110.0).toFloat() * 4 * dpx)
            "dive" -> ProcPose(dy = -120 * dpx + (1 - kotlin.math.cos(p * pi * 2)) * 60 * dpx, rot = sin(p * pi * 2) * 30f, moving = true)
            "glide" -> ProcPose(dx = sin(p * pi * 2) * 120 * dpx, dy = -60 * dpx - sin(p * pi * 4) * 20 * dpx, rot = kotlin.math.cos(p * pi * 2) * 10f, moving = true)
            "boo" -> ProcPose(sx = 1f + 0.25f * wave, sy = 1f + 0.25f * wave, dy = -20 * dpx * wave, moving = true)
            "fade" -> ProcPose(dx = sin(p * pi * 2) * 50 * dpx, moving = true)
            "glow" -> ProcPose(sy = 1f + 0.05f * sin(now / 120.0).toFloat())
            "bounce" -> ProcPose(dy = -abs(sin(p * pi * 3)) * 50 * dpx, sy = 1f - 0.1f * abs(kotlin.math.cos(p * pi * 3)))
            "sparkle" -> ProcPose(dx = sin(p * pi * 2) * 80 * dpx, dy = -wave * 60 * dpx, moving = true)
            else -> ProcPose()
        }
    }

    /** 동작 효과: 소리 글자 · 흙먼지 · 풀 · Zzz · 불꽃 · 광선 · 연기 · 반짝이 */
    private fun procFx(c: Canvas, a: String, p: Float, now: Long, cx: Float, cy: Float, groundY: Float) {
        val front = if (dir >= 0) 1f else -1f
        val pose = procPose(a, p, now)
        val ox = pose.dx * front * sizeK                       // 몸이 움직인 만큼 효과도 따라간다
        val oy = pose.dy * sizeK
        val fx = cx + front * bodyW() * sizeK * 0.55f
        val top = cy + icon / 2 - icon * 1.4f * sizeK
        fun word(s: String, color: Int = INK) = outlined(c, s, cx - 30 * dpx, top, color, 20f)
        fun dust(n: Int, x: Float, spread: Float) {
            fill.color = 0x99A08060.toInt()
            for (i in 0 until n) {
                val ph = (((now / 18) + i * 29) % 100) / 100f
                val px = x + ((i * 37) % 100 - 50) / 50f * spread * dpx
                val py = groundY - ph * 34 * dpx
                c.drawRect(px, py, px + 6 * dpx * (1 - ph), py + 6 * dpx * (1 - ph), fill)
            }
        }
        when (a) {
            "wag" -> word("살랑살랑")
            "dig" -> { dust(10, fx, 30f); word("파바박") }
            "sniff" -> word("킁킁")
            "scratch" -> word("벅벅")
            "bow" -> word("놀자!", RED)
            "howl" -> word("아우우~")
            "chase" -> word("빙글빙글")
            "rollover" -> word("배 만져 줘")
            "roar" -> {                                               // 어흥: 머리에서 머리가 향한 쪽으로 퍼지는 충격파
                val hx = cx + ox + front * bodyW() * sizeK * 0.38f
                val hy = cy + oy - icon * sizeK * 0.22f
                val start = if (front > 0) -45f else 135f
                fill.color = 0x44FFB020
                val rf = (30 + p * 90) * dpx * sizeK
                c.drawArc(hx - rf, hy - rf, hx + rf, hy + rf, start, 90f, true, fill)
                fill.style = Paint.Style.STROKE; fill.strokeWidth = 5 * dpx; fill.color = 0xAAE0A030.toInt()
                for (i in 0 until 3) {
                    val r = ((p * 1.4f - i * 0.22f).coerceIn(0f, 1f)) * 130 * dpx * sizeK
                    if (r > 0) c.drawArc(hx - r, hy - r, hx + r, hy + r, start + 10f, 70f, false, fill)
                }
                fill.style = Paint.Style.FILL
                outlined(c, "어흥!", hx + front * 20 * dpx - (if (front < 0) 60 * dpx else 0f), hy - 40 * dpx, RED, 26f)
            }
            "yawn" -> word("하암~")
            "nap", "doze" -> outlined(c, if ((now / 600) % 2 == 0L) "Z z" else "z Z", cx + 10 * dpx, top, 0xFF5A6B9C.toInt(), 22f)
            "stalk" -> word("슬금슬금")
            "mane" -> word("부르르")
            "claws" -> { word("드드득"); fill.color = INK; for (k in 0 until 3) c.drawRect(fx + k * 6 * dpx, cy - 20 * dpx, fx + k * 6 * dpx + 2 * dpx, cy + 10 * dpx, fill) }
            "rear" -> word("히이잉!", RED)
            "graze" -> {                                              // 풀이 그려진 그림이 있으면 앱 풀은 생략 (겹침 방지)
                if (!procSheets.containsKey("graze")) { fill.color = 0xFF58A848.toInt(); for (k in 0 until 4) c.drawRect(fx - 10 * dpx + k * 7 * dpx, groundY - (8 + k % 2 * 6) * dpx, fx - 6 * dpx + k * 7 * dpx, groundY, fill) }
                word("냠냠")
            }
            "swish" -> word("휙휙")
            "dustroll" -> { dust(14, cx, 50f); word("뒹굴뒹굴") }
            "stomp" -> { dust(8, cx, 30f); word("쿵쿵") }
            "drift" -> { dust(16, cx, 70f); fill.color = 0xAA333333.toInt(); c.drawRect(cx - 60 * dpx, groundY - 3 * dpx, cx + 60 * dpx, groundY, fill); word("끼이익!", RED) }
            "honk" -> word("빵빵!", RED)
            "flash" -> if ((now / 160) % 2 == 0L) {
                fill.color = 0x66FFF59D
                val path = android.graphics.Path().apply { moveTo(fx, cy); lineTo(fx + front * 260 * dpx, cy - 60 * dpx); lineTo(fx + front * 260 * dpx, cy + 50 * dpx); close() }
                c.drawPath(path, fill); word("번쩍!", 0xFFF8B800.toInt())
            }
            "hop" -> if (p > 0.85f) dust(8, cx, 40f)
            "nitro" -> { fill.color = if ((now / 50) % 2 == 0L) 0xFFFF6A00.toInt() else 0xFFFFC107.toInt(); val bx = cx - front * bodyW() * 0.55f; c.drawRect(bx - front * 30 * dpx, cy - 4 * dpx, bx, cy + 6 * dpx, fill); word("부아앙!", RED) }
            "wheelie" -> word("부릉~")
            "loop", "smoke", "sparkle" -> {
                val colors = intArrayOf(0xCCF8A4C0.toInt(), 0xCC3CBCFC.toInt(), 0xCCFFFFFF.toInt(), 0xCCF8D030.toInt())
                for (i in 0 until 10) {
                    val q = p - i * 0.03f
                    if (q < 0) break
                    val pose = procPose(a, q, now)
                    fill.color = colors[i % colors.size]
                    val r = (8 - i * 0.6f) * dpx
                    c.drawCircle(cx + pose.dx * front - front * bodyW() * 0.4f, cy + pose.dy, r, fill)
                }
                if (a == "sparkle") word("수리수리 마수리~", 0xFF9B59B6.toInt())
            }
            "roll" -> word("슝~")
            "spin" -> word("빙그르르")
            "search" -> {
                val ang = sin(now / 500.0).toFloat() * 0.5f
                fill.color = 0x55FFF59D
                val path = android.graphics.Path().apply {
                    moveTo(cx, cy + 10 * dpx); lineTo(cx + (ang - 0.35f) * 300 * dpx, groundY); lineTo(cx + (ang + 0.35f) * 300 * dpx, groundY); close()
                }
                c.drawPath(path, fill)
            }
            "hover" -> dust(12, cx, 80f)
            "beam" -> {
                fill.color = 0x5539D353
                val path = android.graphics.Path().apply { moveTo(cx - 20 * dpx, cy + 14 * dpx); lineTo(cx + 20 * dpx, cy + 14 * dpx); lineTo(cx + 70 * dpx, groundY); lineTo(cx - 70 * dpx, groundY); close() }
                c.drawPath(path, fill)
                fill.color = PAPER
                for (i in 0 until 6) { val ph = (((now / 15) + i * 17) % 100) / 100f; c.drawRect(cx + ((i * 23) % 60 - 30) * dpx, groundY - ph * (groundY - cy), cx + ((i * 23) % 60 - 26) * dpx, groundY - ph * (groundY - cy) + 4 * dpx, fill) }
                word("삐용삐용", 0xFF1E8C5A.toInt())
            }
            "zigzag" -> word("슝슝")
            "wobble" -> word("우웅~")
            "alien" -> {                                              // 외계인이 빔 타고 내려와 둠칫둠칫 춤추고 다시 올라간다
                val bx = cx + ox
                val beamTop = cy + oy + icon * 0.3f
                if (p < 0.25f || p > 0.78f) {
                    fill.color = 0x5539D353
                    val path = android.graphics.Path().apply { moveTo(bx - 20 * dpx, beamTop); lineTo(bx + 20 * dpx, beamTop); lineTo(bx + 60 * dpx, groundY); lineTo(bx - 60 * dpx, groundY); close() }
                    c.drawPath(path, fill)
                }
                val k = when { p < 0.22f -> p / 0.22f; p > 0.8f -> 1f - (p - 0.8f) / 0.2f; else -> 1f }
                val ap = dot * 1.1f
                val dance = p in 0.22f..0.8f
                val hop = if (dance) abs(sin(now / 160.0)).toFloat() * 14 * dpx else 0f
                val ay = beamTop + (groundY - 12 * ap - beamTop) * k - hop
                val ax = bx + if (dance) sin(now / 300.0).toFloat() * 40 * dpx else 0f
                sprite(c, if (dance && (now / 220) % 2 == 0L) ALIEN_B else ALIEN_A, ax - 4.5f * ap, ay, ap, false)
                if (dance) outlined(c, if ((now / 400) % 2 == 0L) "둠칫" else "둠칫둠칫!", ax - 30 * dpx, ay - 20 * dpx, 0xFF2E7D32.toInt(), 20f)
                word(if (p < 0.22f) "누가 내려와요…?" else if (dance) "외계인 댄스 타임!" else "안녕~ 다음에 또!", 0xFF1E8C5A.toInt())
            }
            "lights" -> {                                             // 미지와의 조우: 다섯 음 불빛 신호
                val notes = arrayOf("레", "미", "도", "도", "솔")
                val cols = intArrayOf(0xFFFF5252.toInt(), 0xFFFFD740.toInt(), 0xFF69F0AE.toInt(), 0xFF40C4FF.toInt(), 0xFFE040FB.toInt())
                val step = (p * 6).toInt().coerceAtMost(4)
                val bx = cx + ox
                val ly = cy + oy + icon * 0.25f
                for (i in 0 until 5) {
                    fill.color = if (i == step) cols[i] else (cols[i] and 0x00FFFFFF) or 0x55000000
                    c.drawCircle(bx + (i - 2) * 16 * dpx, ly, (if (i == step) 7 else 5) * dpx, fill)
                }
                outlined(c, notes.take(step + 1).joinToString(" "), bx - 50 * dpx, ly + 40 * dpx, cols[step], 22f)
            }
            "teleport" -> {
                if (p in 0.15f..0.35f || p in 0.5f..0.85f) for (i in 0 until 4)
                    sparkle(c, cx + ox + (i - 1.5f) * 18 * dpx, cy - (i % 2) * 20 * dpx, (4 + 6 * abs(sin(now / 60.0 + i))).toFloat() * dpx, 0xFF69F0AE.toInt())
                word("슝! 순간이동", 0xFF1E8C5A.toInt())
            }
            "rock" -> word("날개 흔들어 인사~")
            "touchgo" -> {
                if (p in 0.42f..0.62f) {
                    fill.color = 0xAA9E9E9E.toInt()
                    for (i in 0 until 4) { val q = ((now / 25 + i * 9) % 30) / 30f; c.drawCircle(cx - front * (20 + q * 60) * dpx, groundY - 6 * dpx - q * 20 * dpx, (5 + q * 10) * dpx, fill) }
                }
                word(if (p < 0.42f) "착륙 접근…" else if (p < 0.62f) "끼익! 터치!" else "다시 이륙~ 부웅", if (p in 0.42f..0.62f) RED else INK)
            }
            "tilt" -> word(if (p < 0.5f) "앞으로 숙여서 전진!" else "뒤로 젖혀서 멈춤")
            "hoist" -> {                                              // 구조 바구니: 내려가서 고양이를 태우고 올라온다
                val k = if (p < 0.45f) p / 0.45f else if (p < 0.55f) 1f else 1f - (p - 0.55f) / 0.45f
                val bx = cx + ox
                val topY = cy + oy + icon * 0.35f
                val by = topY + (groundY - 16 * dpx - topY) * k
                fill.color = 0xFF555555.toInt(); c.drawRect(bx - 1.5f * dpx, topY, bx + 1.5f * dpx, by, fill)
                if (p > 0.5f) mini(c, miniCat, bx, by + icon * 0.2f, icon * 0.5f)
                fill.color = 0xFFE53935.toInt(); c.drawRect(bx - 22 * dpx, by, bx + 22 * dpx, by + 16 * dpx, fill)
                fill.color = 0xFFFFCDD2.toInt(); for (i in 0 until 4) c.drawRect(bx - 20 * dpx + i * 11 * dpx, by + 3 * dpx, bx - 16 * dpx + i * 11 * dpx, by + 13 * dpx, fill)
                word(if (p < 0.5f) "구조 바구니 내려요!" else "구조 완료! 올라갑니다", 0xFFE53935.toInt())
            }
            "bucket" -> {                                             // 산불 헬기: 물주머니로 촤아 → 불이 꺼지고 연기만
                val bx = cx + ox
                val topY = cy + oy + icon * 0.35f
                val drawnBucket = procSheets.containsKey("bucket")             // 헬기 그림에 물주머니가 달려 있으면 그쪽에서 물이 떨어진다
                val by = if (drawnBucket) cy + oy + icon * 0.4f - 20 * dpx else topY + 90 * dpx
                if (!drawnBucket) {
                    fill.color = 0xFF555555.toInt(); c.drawRect(bx - 1.5f * dpx, topY, bx + 1.5f * dpx, by, fill)
                    fill.color = 0xFFFF8F00.toInt(); c.drawRect(bx - 14 * dpx, by, bx + 14 * dpx, by + 20 * dpx, fill)
                }
                val fireX = bx + 10 * dpx
                val fireK = if (p < 0.45f) 1f else (1f - (p - 0.45f) / 0.35f).coerceAtLeast(0f)
                if (fireK > 0f) {
                    flame(c, fireX, groundY, 26 * dpx * fireK, 60 * dpx * fireK, 0xFFFF5722.toInt())
                    flame(c, fireX, groundY, 14 * dpx * fireK, 34 * dpx * fireK, 0xFFFFC107.toInt())
                }
                if (p in 0.4f..0.85f) {
                    fill.color = 0xFF4FC3F7.toInt()
                    for (i in 0 until 10) {
                        val q = ((now / 18 + i * 11) % 40) / 40f
                        val y = by + 20 * dpx + q * (groundY - by - 20 * dpx)
                        c.drawRect(bx - 12 * dpx + (i % 5) * 6 * dpx, y, bx - 9 * dpx + (i % 5) * 6 * dpx, y + 6 * dpx, fill)
                    }
                }
                if (fireK <= 0f) {
                    fill.color = 0xAA9E9E9E.toInt()
                    for (i in 0 until 3) { val q = ((now / 30 + i * 13) % 40) / 40f; c.drawCircle(fireX + (i - 1) * 12 * dpx, groundY - q * 60 * dpx, (6 + q * 10) * dpx, fill) }
                }
                word(when { p < 0.4f -> "산불 발견! 물 퍼 왔어요"; fireK > 0f -> "촤아아 물 폭탄!"; else -> "불 껐어요!" }, 0xFFE65100.toInt())
            }
            "snort" -> {
                for (i in 0 until 3) {
                    val q = ((now / 25 + i * 11) % 30) / 30f
                    sprite(c, CLOUD_GRAY, fx + front * (6 + q * 60) * dpx, cy - 30 * dpx - q * 30 * dpx, dot * (0.25f + q * 0.3f), false)
                }
                word("푸쉭! 콧김")
            }
            "pearl" -> {                                              // 여의주
                val px2 = cx + ox + front * bodyW() * 0.35f
                val py2 = cy + oy - icon * 0.55f + sin(now / 200.0).toFloat() * 10 * dpx
                if (!procSheets.containsKey("pearl")) {                          // 여의주를 든 그림이 있으면 따로 그리지 않는다
                    fill.color = 0x55FFF59D; c.drawCircle(px2, py2, 22 * dpx, fill)
                    fill.color = 0xFFFFE082.toInt(); c.drawCircle(px2, py2, 12 * dpx, fill)
                    fill.color = PAPER; c.drawCircle(px2 - 4 * dpx, py2 - 4 * dpx, 3 * dpx, fill)
                }
                sparkle(c, px2 + 18 * dpx, py2 - 14 * dpx, (3 + 5 * abs(sin(now / 90.0))).toFloat() * dpx, GOLD)
                word("여의주 데굴데굴~", 0xFFE65100.toInt())
            }
            "hoard" -> {
                for (i in 0 until 7) drawCoin(c, cx + (i - 3) * 22 * dpx, groundY - 10 * dpx - (if (i % 2 == 0) 0 else 10) * dpx, icon * 0.35f, now, i)
                if (p in 0.25f..0.9f) outlined(c, if ((now / 600) % 2 == 0L) "Z z" else "z Z", cx + 10 * dpx, top - 26 * dpx, 0xFF5A6B9C.toInt(), 22f)
                word("내 보물이야… 지켜야지")
            }
            "swarm" -> {                                              // 고스트버스터즈처럼: 유령 떼가 화면을 제멋대로 날다 혼비백산 도망
                val sheet = idleSheet ?: walkSheet
                val flee = ((p - 0.62f) / 0.38f).coerceIn(0f, 1f)
                val t = now / 1000f
                for (i in 0 until 28) {
                    val r1 = ((i * 7919 + 13) % 1000) / 1000f
                    val r2 = ((i * 104729 + 7) % 1000) / 1000f
                    val r3 = ((i * 1299709 + 3) % 1000) / 1000f
                    val ph = t * (0.6f + r1) + r2 * 6.28f
                    var x = width * (0.5f + 0.45f * sin(ph))
                    var y = height * (0.45f + 0.36f * sin(t * (0.8f + r2) * 1.3f + r3 * 6.28f))
                    val appear = ((p - r3 * 0.25f) / 0.08f).coerceIn(0f, 1f)
                    if (appear <= 0f) continue
                    var flip = kotlin.math.cos(ph) < 0
                    if (flee > 0f) {
                        val ex = if (x < width / 2) -200 * dpx else width + 200 * dpx
                        x += (ex - x) * flee * flee
                        y -= flee * 120 * dpx * r1
                        flip = ex < x
                    }
                    val h = icon * (0.35f + r1 * 0.35f)
                    bmpPaint.alpha = (210 * appear).toInt()
                    mini(c, sheet, x, y + h / 2, h, flip)
                    if (flee > 0.05f && i % 4 == 0) outlined(c, arrayOf("으악!", "살려줘~", "도망쳐!", "히이익")[(i / 4) % 4], x - 30 * dpx, y - h * 0.7f, RED, 16f)
                }
                bmpPaint.alpha = 255
                word(if (flee > 0f) "혼비백산!" else "유령 소동!", 0xFF6A5ACD.toInt())
            }
            "wisp" -> {                                               // 도깨비불이 빙글빙글
                for (i in 0 until 3) {
                    val a = now / 400.0 + i * 2.094
                    val wx = cx + ox + (cos(a) * 70 * dpx).toFloat()
                    val wy = cy + oy - icon * 0.2f + (sin(a) * 26 * dpx).toFloat()
                    flame(c, wx, wy, 9 * dpx, 26 * dpx, 0xFF4DD0E1.toInt())
                    flame(c, wx, wy, 5 * dpx, 15 * dpx, 0xFFE0F7FA.toInt())
                }
                word("도깨비불~", 0xFF00838F.toInt())
            }
            "peekaboo" -> if (p in 0.72f..0.95f) outlined(c, "까꿍!", cx + ox - 30 * dpx, top - 10 * dpx, RED, 30f) else if (p in 0.3f..0.7f) word("어디 갔게~?")
            "chill" -> {
                fill.color = 0x99B3E5FC.toInt()
                for (i in 0 until 6) {
                    val q = ((now / 22 + i * 9) % 36) / 36f
                    c.drawCircle(fx + front * q * 120 * dpx, cy - 10 * dpx + sin((q * 8 + i).toDouble()).toFloat() * 10 * dpx, (5 + q * 12) * dpx, fill)
                }
                fill.color = 0xFF81D4FA.toInt()
                for (i in 0 until 5) {
                    val q = ((now / 30 + i * 13) % 40) / 40f
                    val x = fx + front * (20 + i * 20) * dpx
                    c.drawRect(x, cy - 30 * dpx + q * 50 * dpx, x + 4 * dpx, cy - 26 * dpx + q * 50 * dpx, fill)
                }
                word("후우~ 으스스 차갑지?", 0xFF0277BD.toInt())
            }
            "tumble" -> word("데굴데굴~")
            "seeds" -> {
                fill.color = 0xFFE6C66A.toInt()
                for (i in 0 until 6) {
                    val q = ((now / 20 + i * 7) % 42) / 42f
                    val sx2 = fx + front * q * 150 * dpx
                    val sy2 = cy - 4 * dpx - sin(q * Math.PI).toFloat() * 50 * dpx + q * q * 30 * dpx
                    c.drawRect(sx2, sy2, sx2 + 5 * dpx, sy2 + 3 * dpx, fill)
                }
                word("퉤! 퉤! 호박씨", 0xFFF57C00.toInt())
            }
            "grin" -> {
                fill.color = if ((now / 140) % 3 == 0L) 0x66FFB300 else 0x44FF6F00
                c.drawCircle(cx + ox, cy + oy, icon * 0.55f, fill)
                word("히히히… 촛불 깜빡", 0xFFF57C00.toInt())
            }
            "sweep" -> { dust(10, cx + ox, 50f); word("싹싹 빗자루 청소 중") }
            "potion" -> {
                val kx = cx + ox
                if (procSheets["potion"] == null) drawProp(c, "cauldron", ((now / 260) % 2).toInt(), kx, groundY, dot * 0.9f)   // 물약병 그림이 있으면 가마솥은 생략
                for (i in 0 until 4) {
                    val q = ((now / 30 + i * 10) % 40) / 40f
                    fill.color = if (i % 2 == 0) 0xFF7CFC6A.toInt() else 0xFFB388FF.toInt()
                    c.drawCircle(kx + (i - 1.5f) * 10 * dpx, groundY - 22 * dot * 0.9f - q * 80 * dpx, (3 + 4 * (1 - q)) * dpx, fill)
                }
                word("보글보글 물약 휘휘~", 0xFF7B3FC4.toInt())
            }
            "moon" -> {
                fill.color = 0x55FFF59D; c.drawCircle(cx, cy - 170 * dpx, 70 * dpx, fill)
                fill.color = 0x33FFF59D; c.drawCircle(cx, cy - 170 * dpx, 90 * dpx, fill)
                word("보름달 밤 산책~", 0xFF5E35B1.toInt())
            }
            "hattip" -> word("안녕~ 냥!", 0xFF7B3FC4.toInt())
            "fire" -> {
                for (i in 0 until 9) {
                    val ph = (((now / 14) + i * 13) % 100) / 100f
                    fill.color = if (i % 3 == 0) 0xFFFFC107.toInt() else 0xFFFF5722.toInt()
                    val x = fx + front * ph * 180 * dpx
                    val sz = (6 + ph * 14) * dpx
                    c.drawRect(x - sz / 2, cy - 8 * dpx - sz / 2 + sin((ph * 9 + i).toDouble()).toFloat() * 6 * dpx, x + sz / 2, cy - 8 * dpx + sz / 2, fill)
                }
                word("화르륵!", RED)
            }
            "flap" -> word("펄럭펄럭")
            "chomp" -> word("와작와작!", RED)
            "charge" -> {                                             // 퐈! 파! 팍! 흙먼지 · 속도선 · 반환점 쾅
                val bx = cx + ox
                val rear = bx - front * bodyW() * sizeK * 0.45f
                fill.color = 0xAAB89A70.toInt()
                for (i in 0 until 7) {
                    val q = ((now / 25 + i * 13) % 40) / 40f
                    val r = (6 + q * 16) * dpx
                    c.drawCircle(rear - front * q * 70 * dpx, groundY - r * 0.6f - q * 10 * dpx, r, fill)
                }
                if (p < 0.5f) {
                    fill.color = 0x66333333
                    for (i in 0 until 4) {
                        val ly = cy - icon * 0.4f + i * icon * 0.22f
                        val x0 = rear - front * (24 + i * 16) * dpx
                        c.drawRect(minOf(x0, x0 - front * 46 * dpx), ly, maxOf(x0, x0 - front * 46 * dpx), ly + 3 * dpx, fill)
                    }
                }
                val beat = ((now / 120) % 3).toInt()
                for (k in 0..beat) {
                    val sx = rear - front * (10 + k * 26) * dpx
                    outlined(c, arrayOf("퐈!", "파!", "팍!")[k], sx - 12 * dpx, groundY - icon * 0.75f - k * 12 * dpx, RED, 22f + k * 3)
                }
                if (p in 0.42f..0.62f) {
                    impactStar(c, bx + front * bodyW() * sizeK * 0.6f, cy - icon * 0.1f, (24 + (p - 0.42f) * 200) * dpx, 0xFFFFD23F.toInt())
                    outlined(c, "쾅!", bx + front * bodyW() * sizeK * 0.6f - 20 * dpx, cy - icon * 0.8f, RED, 30f)
                    shakeOnce()
                }
            }
            "headbutt" -> {                                           // 트리케라 박치기: 바위가 쩍 갈라진다
                val rr = 26 * dpx * sizeK
                val rx = cx + front * (bodyW() * sizeK * 0.55f + 70 * dpx * sizeK + rr * 0.7f)
                if (p < 0.5f) {
                    rock(c, rx, groundY, rr)
                    word(if (p < 0.35f) "흐읍…" else "박치기!", if (p < 0.35f) INK else RED)
                } else {
                    val q = (p - 0.5f) / 0.5f
                    fill.color = 0xFF7D7D85.toInt()
                    for (i in 0 until 6) {
                        val px2 = rx + front * (10 + i * 16) * dpx * q * 3f - (if (i % 2 == 0) 0f else front * 30 * dpx * q)
                        val py2 = (groundY - rr * 0.8f - (1.2f * q - q * q * 1.6f) * (120 + i * 20) * dpx).coerceAtMost(groundY - 6 * dpx)
                        val sz = (10 - i) * dpx * sizeK * 0.8f
                        c.drawRect(px2 - sz / 2, py2 - sz / 2, px2 + sz / 2, py2 + sz / 2, fill)
                    }
                    if (q < 0.45f) {
                        impactStar(c, rx - front * rr * 0.6f, groundY - rr, (30 + q * 70) * dpx, 0xFFFFD23F.toInt())
                        outlined(c, "쾅!!", rx - 30 * dpx, groundY - rr * 2.4f, RED, 36f)
                    }
                    dust(12, rx, 60f)
                    shakeOnce(280)
                }
            }
            "shortarms" -> {
                word("팔이… 안 닿아…")
                if (p > 0.4f) { fill.color = 0xFF4FC3F7.toInt(); val dx = fx - front * 6 * dpx; c.drawRect(dx, top + 14 * dpx, dx + 5 * dpx, top + 22 * dpx, fill) }
            }
            "meat" -> {                                               // 티라노 거대 고기: 한 입씩 우걱우걱 → 꿀꺽 → 뼈 휙 → 꺼억
                val mp = dot * 0.95f * sizeK
                val mw = 24 * mp
                val mx = cx + ox + front * bodyW() * sizeK * 0.42f           // 입
                val my = cy - icon * 0.2f
                when {
                    p < 0.18f -> {                                          // 고기가 날아온다
                        val k = p / 0.18f
                        drawProp(c, "meat", 0, mx + front * ((1 - k) * 320 * dpx + mw * 0.3f), my - sin(k * Math.PI).toFloat() * 160 * dpx + 12 * mp, mp, rot = k * 540f)
                        word("거대 고기다!")
                    }
                    p < 0.7f -> {                                           // 한 입씩 줄어든다 (입 쪽부터)
                        val bites = ((p - 0.18f) / 0.065f).toInt()
                        val eaten = (bites * 0.11f).coerceAtMost(0.75f)
                        c.save()
                        if (front > 0) c.clipRect(mx - mw * 0.2f + eaten * mw, my - mw, mx + mw * 1.2f, my + mw)
                        else c.clipRect(mx - mw * 1.2f, my - mw, mx + mw * 0.2f - eaten * mw, my + mw)
                        drawProp(c, "meat", 0, mx + front * mw * 0.3f, my + 12 * mp, mp, rot = sin(now / 90.0).toFloat() * 6f)
                        c.restore()
                        fill.color = 0xFFB5651D.toInt()                       // 고기 부스러기
                        for (i in 0 until 6) {
                            val q = ((now / 18 + i * 9) % 30) / 30f
                            val bx = mx + front * (4 + i * 5) * dpx + (if (i % 2 == 0) 1 else -1) * q * 40 * dpx
                            val by = my - sin(q * Math.PI).toFloat() * 30 * dpx + q * 40 * dpx
                            c.drawRect(bx, by, bx + 4 * dpx, by + 4 * dpx, fill)
                        }
                        val beat = ((now / 260) % 2).toInt()
                        val pop = 1f + 0.25f * abs(sin(now / 130.0)).toFloat()
                        c.save(); c.scale(pop, pop, mx, top - 20 * dpx)
                        outlined(c, if (beat == 0) "우걱!" else "우걱우걱!", mx - 40 * dpx + beat * 30 * dpx, top - 20 * dpx - beat * 14 * dpx, RED, 24f)
                        c.restore()
                    }
                    p < 0.82f -> {                                          // 꿀꺽 — 뼈만 입에 남았다
                        c.save(); c.rotate(-20f, mx, my)
                        sprite(c, BONE, mx - 6 * dot * 0.6f, my - 2 * dot * 0.6f, dot * 0.6f, front < 0)
                        c.restore()
                        word("꿀꺽!", RED)
                        sparkle(c, mx, my - 24 * dpx, (6 + 8 * abs(sin(now / 80.0)).toFloat()) * dpx, GOLD)
                    }
                    else -> {                                               // 뼈를 휙 던지고 꺼억
                        val k = (p - 0.82f) / 0.18f
                        val bx = mx - front * k * 260 * dpx
                        val by = my - sin(k * Math.PI).toFloat() * 120 * dpx + k * 40 * dpx
                        c.save(); c.rotate(k * 720f, bx, by)
                        sprite(c, BONE, bx - 6 * dot * 0.6f, by - 2 * dot * 0.6f, dot * 0.6f, false)
                        c.restore()
                        outlined(c, "꺼억~", mx - 20 * dpx, top - 16 * dpx, 0xFF795548.toInt(), 26f)
                    }
                }
            }
            "wallow" -> {
                fill.color = 0xFF7A5230.toInt()
                c.drawOval(cx - bodyW() * sizeK * 0.7f, groundY - 8 * dpx, cx + bodyW() * sizeK * 0.7f, groundY + 6 * dpx, fill)
                for (i in 0 until 5) {
                    val q = ((now / 30 + i * 9) % 30) / 30f
                    c.drawRect(cx + (i - 2) * 22 * dpx, groundY - 10 * dpx - sin(q * Math.PI).toFloat() * 40 * dpx, cx + (i - 2) * 22 * dpx + 6 * dpx, groundY - 4 * dpx - sin(q * Math.PI).toFloat() * 40 * dpx, fill)
                }
                word("철퍽철퍽 진흙 목욕")
            }
            "sunbask" -> {
                fill.color = 0x66FFD23F
                val sx0 = cx + bodyW() * sizeK; val sy0 = top - 120 * dpx
                for (i in 0 until 4) {
                    val path = android.graphics.Path().apply {
                        moveTo(sx0, sy0); lineTo(cx - (40 - i * 28) * dpx, cy - 10 * dpx); lineTo(cx - (28 - i * 28) * dpx, cy - 10 * dpx); close()
                    }
                    c.drawPath(path, fill)
                }
                sparkle(c, sx0, sy0, (10 + 4 * sin(now / 200.0).toFloat()) * dpx, 0xFFFFC107.toInt())
                word("등판 데우는 중~")
            }
            "drink" -> {
                val wx = fx + front * 20 * dpx * sizeK
                fill.color = 0xFF64B5F6.toInt()
                c.drawOval(wx - 34 * dpx, groundY - 6 * dpx, wx + 34 * dpx, groundY + 6 * dpx, fill)
                fill.style = Paint.Style.STROKE; fill.strokeWidth = 2 * dpx; fill.color = 0xFFE3F2FD.toInt()
                val r = (((now / 20) % 30) / 30f) * 30 * dpx
                c.drawOval(wx - r, groundY - r * 0.2f, wx + r, groundY + r * 0.2f, fill)
                fill.style = Paint.Style.FILL
                word("꿀꺽꿀꺽")
            }
            "fisheat" -> {                                            // 익룡: 물고기를 공중에서 꿀꺽
                val fp = dot * 0.8f
                val bx = cx + ox + front * bodyW() * 0.5f
                val by = cy + oy - icon * 0.15f
                if (p < 0.25f) {
                    val k = p / 0.25f
                    drawProp(c, "fish", ((now / 120) % 2).toInt(), bx, groundY - (groundY - by) * k + 12 * fp, fp, rot = k * 360f)
                    word("물고기다!")
                } else if (procSheets["fisheat"] == null && p < 0.7f) drawProp(c, "fish", 0, bx, by + 10 * fp, fp)
                if (p in 0.45f..0.7f) word("휙~ 하늘로!")
                if (p > 0.7f) { word("공중에서 꿀꺽!", RED); sparkle(c, bx, by - 20 * dpx, (5 + 7 * abs(sin(now / 90.0)).toFloat()) * dpx, GOLD) }
            }
            "perch" -> if (p in 0.25f..0.85f) word("네 발로 뒤뚱뒤뚱")
            "headshake" -> word("도리도리")
            "reach" -> {                                              // 머리 위 나뭇가지 → 잎이 하나둘 떨어진다
                val bx = fx + 6 * dpx; val by = top - 34 * dpx
                fill.color = 0xFF6D4C41.toInt(); c.drawRect(bx - 40 * dpx, by - 2 * dpx, bx + 30 * dpx, by + 3 * dpx, fill)
                fill.color = 0xFF58A848.toInt()
                for (k in 0 until 5) c.drawRect(bx - 34 * dpx + k * 14 * dpx, by - 10 * dpx + (k % 2) * 4 * dpx, bx - 26 * dpx + k * 14 * dpx, by - 2 * dpx + (k % 2) * 4 * dpx, fill)
                for (k in 0 until 3) {
                    val q = ((p * 3 - k * 0.6f) % 1f + 1f) % 1f
                    c.drawRect(bx - 20 * dpx + k * 16 * dpx + sin(q * 9.0).toFloat() * 6 * dpx, by + q * 90 * dpx, bx - 15 * dpx + k * 16 * dpx + sin(q * 9.0).toFloat() * 6 * dpx, by + q * 90 * dpx + 5 * dpx, fill)
                }
                word("냠냠 높은 잎")
            }
            "bellow" -> {
                fill.style = Paint.Style.STROKE; fill.strokeWidth = 4 * dpx; fill.color = 0x998E7CC3.toInt()
                for (i in 0 until 3) {
                    val r = ((p * 1.4f - i * 0.25f).coerceIn(0f, 1f)) * 90 * dpx
                    if (r > 0) c.drawArc(fx - r, top - r, fx + r, top + r, if (front > 0) -75f else 195f, 60f, false, fill)   // 고개 든 쪽(앞 위)으로
                }
                fill.style = Paint.Style.FILL
                word("뿌우우~")
            }
            "tailswing" -> {                                          // 스테고 꼬리 휘두르기: 궤적 + 철썩!
                val tx = cx + ox - front * bodyW() * sizeK * 0.5f
                val ty = cy - icon * 0.1f
                val ph = (p * 2f) % 1f                                 // 두 번 휘두른다
                fill.style = Paint.Style.STROKE; fill.strokeWidth = 5 * dpx; fill.color = 0x88FF8F00.toInt()
                val sweep = (ph.coerceAtMost(0.75f) / 0.75f) * 180f
                for (k in 0 until 3) {
                    val r = (40 + k * 12) * dpx * sizeK
                    c.drawArc(tx - r, ty - r, tx + r, ty + r, 270f, -front * sweep, false, fill)
                }
                fill.style = Paint.Style.FILL
                if (ph in 0.6f..0.85f) {
                    val ix = tx - front * 20 * dpx; val iy = ty + 50 * dpx * sizeK
                    impactStar(c, ix, iy, (22 + (ph - 0.6f) * 120) * dpx, 0xFFFF7043.toInt())
                    outlined(c, "철썩!", ix - 30 * dpx, iy - 30 * dpx, RED, 28f)
                    shakeOnce()
                } else word("휘이익~")
            }
            "dive" -> word("슈우웅~")
            "glide" -> word("바람 타기~")
            "boo" -> word("왁! 놀랐지?", 0xFF6A5ACD.toInt())
            "fade" -> word("스르륵~")
            "glow" -> {
                fill.color = if ((now / 200) % 2 == 0L) 0x55FFB020 else 0x33FF8C00
                c.drawCircle(cx, cy, 50 * dpx, fill)
                // 사탕 뿌리기
                val candy = intArrayOf(0xFFE53935.toInt(), 0xFF8E24AA.toInt(), 0xFF43A047.toInt(), 0xFFFFC107.toInt())
                for (i in 0 until 6) {
                    val ph = (((now / 16) + i * 19) % 100) / 100f
                    fill.color = candy[i % 4]
                    val x = cx + ((i * 41) % 120 - 60) * dpx * ph
                    val y = cy - 40 * dpx + ph * ph * (groundY - cy + 40 * dpx)
                    c.drawRect(x - 4 * dpx, y - 3 * dpx, x + 4 * dpx, y + 3 * dpx, fill)
                }
                word("사탕 안 주면 장난칠 거야!", 0xFFF57C00.toInt())
            }
            "bounce" -> word("통! 통!")
            else -> Unit
        }
    }

    private fun idleProps(c: Canvas, now: Long, cx: Float, cy: Float, groundY: Float) {
        val w = bodyW()
        val faceRight = dir >= 0
        when (idleAct) {
            "eat" -> {
                val bw = 12 * dot * 0.75f
                val bx = if (faceRight) cx + w * 0.42f else cx - w * 0.42f - bw
                sprite(c, FISH_BOWL, bx, groundY - 6 * dot * 0.75f, dot * 0.75f, !faceRight)
                if ((now / 350) % 2 == 1L) outlined(c, "냠", bx + bw * 0.3f, groundY - 60 * dpx, INK, 15f)
            }
            "sleep" -> {
                val k = ((now - idleActAt) % 2400) / 2400f
                for (i in 0..2) {
                    val p = (k + i / 3f) % 1f
                    outlined(c, if (i == 1) "Z" else "z", cx + w * 0.2f + p * 40 * dpx, cy - icon * 0.4f - p * 60 * dpx, INK, 13f + p * 8f)
                }
            }
        }
        // 착지 먼지
        val la = now - landedAt
        if (la in 0..420) {
            val p = la / 420f
            fill.color = HILL
            for (s in intArrayOf(-1, 1)) for (i in 0..2) {
                val x = cx + s * (w * 0.3f + p * (30 + i * 14) * dpx)
                val y = groundY - (4 + i * 5) * dpx * (1 - p)
                val sz = dot * (1.3f - p)
                c.drawRect(x, y - sz, x + sz, y, fill)
            }
            if (p < 0.6f) outlined(c, "탁!", cx - 14 * dpx, groundY - icon - 10 * dpx, INK, 15f)
        }
    }

    /** 세레모니 중 고양이가 공을 쫓는 중 · 그때 바라보는 쪽 */
    private var chasing = false
    private var partyFlip = false

    // 나는 캐릭터 높이 · 비행기 연기 자국
    private var lift = 0f
    private var liftGoal = 0f
    private var nextLiftAt = 0L
    private val trail = ArrayList<Triple<Float, Float, Long>>()

    private fun smokeTrail(c: Canvas, now: Long) {
        val life = if (partyKind == "heart") 3400f else 1600f       // 하트는 다 그릴 때까지 남는다
        trail.removeAll { now - it.third > life }
        trail.forEachIndexed { i, (x, y, at) ->
            val a = 1f - (now - at) / life
            fill.color = if (partyKind == "heart") (if (i % 3 == 0) 0xFFFFB3CF.toInt() else 0xFFFF5C93.toInt()) else SPARK_COLORS[(i / 6) % SPARK_COLORS.size]
            val sz = dot * (1f + 1.2f * a)
            c.drawRect(x, y, x + sz, y + sz, fill)
        }
    }

    /** 미니 캐릭터(시트 첫 칸)를 높이 h로 그린다 */
    private fun mini(c: Canvas, bmp: Bitmap?, x: Float, bottom: Float, h: Float, flip: Boolean = false) {
        bmp ?: return
        val fw = bmp.width / 2
        srcRect.set(0, 0, fw, bmp.height)
        val w = fw * h / bmp.height
        dst.set(x - w / 2, bottom - h, x + w / 2, bottom)
        c.save()
        if (flip) c.scale(-1f, 1f, x, bottom)
        c.drawBitmap(bmp, srcRect, dst, bmpPaint)
        c.restore()
    }

    private val flames = ArrayList<Spark>()

    // ── 세레모니 종류: 캐릭터마다 2~3가지 중 도착할 때마다 하나 (지난번과 겹치지 않게) ──
    private var partyKind = "yarn"
    /** 이스터에그 깜짝 출연 (용 세레모니 때 가끔 아기 용) */
    private var partyCameo = false
    private val sizeK: Float get() = SIZE_K[charName] ?: 1f
    /** 세레모니 기준 자리 (몸이 움직이기 전 가운데) — 소품을 놓는 자리 */
    private var partyX0 = 0f
    private var partyY0 = 0f
    private val propArt = HashMap<String, Bitmap?>()
    private fun propBmp(n: String) = propArt.getOrPut(n) { load("pet/prop_$n.png") }

    private fun pickPartyKind() {
        val kinds = PARTY_KINDS[charName] ?: listOf("plain")
        partyKind = kinds.filter { it != partyKind }.ifEmpty { kinds }.random()
        if (partyKind == "robot" && robotTransform == null) partyKind = "drift"
        partyCameo = charName == "dragon" && Random.nextFloat() < 0.35f
    }

    /** 세레모니 중 폴짝 (강아지·사자·호박) — 머리에 얹은 소품도 같이 뛴다 */
    private fun partyHop(pa: Long): Float =
        if (pa in 450..(PARTY_MS - 500) && charName in HOPPERS) -abs(sin(pa / 1000.0 * Math.PI * 2.2)).toFloat() * 14 * dpx else 0f

    private fun smooth(x: Float): Float { val k = x.coerceIn(0f, 1f); return k * k * (3 - 2 * k) }

    /** 소품 한 칸을 가운데 x · 바닥 bottom 에 그린다 (px = 그림 한 칸 크기) */
    private fun drawProp(c: Canvas, n: String, frame: Int, x: Float, bottom: Float, px: Float, flip: Boolean = false, rot: Float = 0f, alpha: Int = 255) {
        val b = propBmp(n) ?: return
        val frames = PROP_FRAMES[n] ?: 1
        val fw = b.width / frames
        val f = ((frame % frames) + frames) % frames
        srcRect.set(f * fw, 0, f * fw + fw, b.height)
        val w = fw * px
        val h = b.height * px
        dst.set(x - w / 2, bottom - h, x + w / 2, bottom)
        c.save()
        if (rot != 0f) c.rotate(rot, x, bottom - h / 2)
        if (flip) c.scale(-1f, 1f, x, bottom)
        bmpPaint.alpha = alpha.coerceIn(0, 255)
        c.drawBitmap(b, srcRect, dst, bmpPaint)
        bmpPaint.alpha = 255
        c.restore()
    }

    /** 꽃가루가 위에서 팔랑팔랑 */
    private fun confetti(c: Canvas, t: Float, x0: Float, groundY: Float) {
        for (i in 0 until 16) {
            val q = (t * 0.45f + i * 0.0625f) % 1f
            val x = x0 + (((i * 97) % 640) - 320) * dpx + sin((t * 3 + i).toDouble()).toFloat() * 14 * dpx
            drawProp(c, "confetti", i % 4, x, groundY - 520 * dpx + q * 500 * dpx, dot * 0.9f, rot = t * 300f + i * 37f)
        }
    }

    /**
     * 캐릭터별 도착 장기 — 캐릭터마다 2~3가지 중 도착할 때마다 하나 (partyKind)
     * 고양이: 털실·상자·시상대 / 강아지: 뼈다귀·원반·메달 / 사자: 바비큐·왕관·시상대 / 말: 건초·당근·시상대
     * 스포츠카: 로봇 변신·세차·드리프트 / 용: 불꽃·보물상자·생일 케이크 / 비행기: 에어쇼·하트 / 헬기: 강아지 하차·헬기장·선물
     * 비행접시: 고양이 납치·미스터리 서클 / 할로윈: 사탕·선물·케이크·가마솥 / 공룡: 화석·피냐타(·왕관) / 익룡: 물고기·풍선
     */
    private fun ceremony(c: Canvas, pa: Long, cx: Float, cy: Float, groundY: Float, z: Float) {
        if (pa < 350 || pa > PARTY_MS - 350) return
        val t = (pa - 350) / 1000f
        val w = bodyW() * z
        val front = cx + w * 0.55f                 // 캐릭터 앞(오른쪽)
        val d = dot * z * 0.85f                     // 소품 한 칸 (커진 캐릭터에 맞춰)
        val under = cy + icon * z * 0.5f            // 캐릭터 발밑(나는 것은 공중)
        when (partyKind) {
            "robot", "drift" -> {
                // 드리프트: 뒷바퀴 쪽 타이어 연기
                for (i in 0 until 4) {
                    val sp = ((t * 1.4f + i / 4f) % 1f)
                    sprite(c, CLOUD_GRAY, cx - w * 0.5f - sp * 90 * dpx, groundY - 10 * dpx - sp * 70 * dpx, d * (0.4f + sp * 0.5f), false)
                }
                if (partyKind == "drift" && t > 2.4f) {        // 드리프트 끝 → 트로피
                    drawProp(c, "trophy", ((pa / 260) % 2).toInt(), front + 40 * dpx, groundY, d * 0.9f)
                    outlined(c, "드리프트 왕!", cx - 80 * dpx, groundY - icon * 1.7f, RED, 26f)
                }
            }
            "fire" -> {
                // 입에서 불꽃 화르륵
                if (t < 2.6f) repeat(3) {
                    val a = (Random.nextFloat() - 0.5f) * 0.6f
                    val sp = (380 + Random.nextFloat() * 220) * dpx
                    flames += Spark(cx + w * 0.48f, cy - icon * z * 0.1f, kotlin.math.cos(a.toDouble()).toFloat() * sp, sin(a.toDouble()).toFloat() * sp, FLAME[Random.nextInt(FLAME.size)], 1f)
                }
                val it = flames.iterator()
                while (it.hasNext()) {
                    val f = it.next()
                    f.x += f.vx * 0.04f
                    f.y += f.vy * 0.04f - 12 * dpx * 0.04f
                    f.life -= 0.06f
                    if (f.life <= 0f) { it.remove(); continue }
                    fill.color = f.color
                    val sz = dot * z * 0.5f * (0.6f + f.life)
                    c.drawRect(f.x, f.y, f.x + sz, f.y + sz, fill)
                }
            }
            "dogdrop" -> {
                // 밧줄 내리고 강아지가 쭉 미끄러져 하차 → 땅에서 꼬리 흔들기
                val ropeX = cx + w * 0.05f
                val k = (t / 1.6f).coerceAtMost(1f)
                fill.color = 0xFF7C4C1C.toInt()      // 갈색 밧줄
                c.drawRect(ropeX, under, ropeX + 4 * dpx, under + (groundY - under) * min(1f, t / 0.5f), fill)
                if (t > 0.5f) {
                    val dogBottom = under + icon * 0.6f + (groundY - under - icon * 0.6f) * ((t - 0.5f) / 1.1f).coerceIn(0f, 1f)
                    val wag = if (k >= 1f) sin(t * 14.0).toFloat() * 3 * dpx else 0f
                    mini(c, miniDog, ropeX + 30 * dpx + wag, dogBottom, icon)
                }
            }
            "abduct" -> {
                // 초록 빔으로 고양이 납치 (빙글빙글 작아지며 쏙)
                val beamTop = under - 4 * dpx
                fill.color = 0x9958D854.toInt()      // 초록 빔
                val path = android.graphics.Path().apply {
                    moveTo(cx - 18 * dpx * z, beamTop); lineTo(cx + 18 * dpx * z, beamTop)
                    lineTo(cx + 90 * dpx * z, groundY); lineTo(cx - 90 * dpx * z, groundY); close()
                }
                c.drawPath(path, fill)
                val k = ((t - 0.3f) / 2.2f).coerceIn(0f, 1f)
                if (k < 1f) {
                    val catH = icon * (1f - 0.7f * k)
                    val bottomY = groundY - (groundY - beamTop) * k
                    c.save()
                    c.rotate(sin(t * 10.0).toFloat() * 25f * k, cx, bottomY - catH / 2)
                    mini(c, miniCat, cx, bottomY, catH)
                    c.restore()
                } else {
                    sprite(c, Icons.CHECK, cx - 24 * dpx, beamTop - 70 * dpx, dot, false)
                }
            }
            "airshow" -> Unit                          // 몸이 직접 한 바퀴 돈다 (위에서)
            "yarn" -> {
                val tt = pa - 450L
                if (tt >= 3300) {                           // 마지막: 생선 냠냠
                    sprite(c, FISH_BOWL, front, groundY - 6 * d, d, false)
                    return
                }
                if (tt in 2500 until 3300) {                // 덮치기: 공은 앞에 놓여 있다가 눌림
                    val squash = if ((tt - 2500) / 800f > 0.85f) 0.6f else 1f
                    c.save(); c.scale(1f, squash, front + 80 * dpx, groundY)
                    sprite(c, YARN, front + 80 * dpx, groundY - 9 * d, d, false)
                    c.restore()
                    return
                }
                if (tt < 1100) return                       // 손 흔들 땐 소품 없음
                // 털실 공을 톡톡 튀긴다
                val ph = (t * 2.2f) % 1f
                val h = 4f * ph * (1f - ph) * 80 * dpx * z
                val bx = if (partyFlip) cx - w * 0.55f - 10 * dpx * z - 9 * d else front + 10 * dpx * z
                sprite(c, YARN, bx, groundY - 9 * d - h, d, false)
                fill.color = 0xFFF8A4C0.toInt()
                for (i in 0 until 6) c.drawRect(bx - i * d * 1.2f, groundY - d * (1 + (i % 2)), bx - i * d * 1.2f + d, groundY - d * (i % 2), fill)
            }
            "bone" -> {
                // 뼈다귀가 날아와 입에 쏙 → 물고 흔들기
                val mouthX = cx + w * 0.30f
                val mouthY = groundY - icon * z * 0.38f
                val k = (t / 0.7f).coerceAtMost(1f)
                val bx = front + 260 * dpx * (1f - k) - 6 * d
                val by = mouthY - 260 * dpx * 4 * k * (1f - k) - (1f - k) * 160 * dpx
                val b = d * 0.6f                    // 뼈다귀는 입에 맞게 조금 작게
                if (k < 1f) {
                    c.save()
                    c.rotate(t * 720f, bx + 6 * b, by + 2 * b)
                    sprite(c, BONE, bx, by, b, false)
                    c.restore()
                } else {
                    c.save()
                    c.rotate(sin(t * 12.0).toFloat() * 12f, mouthX, mouthY)
                    sprite(c, BONE, mouthX - 6 * b, mouthY - 2 * b, b, false)
                    c.restore()
                }
            }
            "bbq" -> {
                // 바비큐 그릴 + 지글지글 연기
                val gx = front + 6 * dpx * z
                sprite(c, GRILL, gx, groundY - 10 * d, d, false)
                for (i in 0 until 3) {
                    val sp = ((t * 0.9f + i / 3f) % 1f)
                    sprite(c, CLOUD_GRAY, gx + (4 + i * 4) * d + sin((t + i) * 5.0).toFloat() * 6 * dpx, groundY - 10 * d - sp * 120 * dpx * z, d * 0.35f, false)
                }
            }
            "hay" -> {
                // 건초를 우물우물 + 지푸라기 날림
                val hx = front - 4 * d
                sprite(c, HAY, hx, groundY - 9 * d, d, false)
                fill.color = 0xFFF8B800.toInt()
                for (i in 0 until 5) {
                    val sp = ((t * 1.3f + i / 5f) % 1f)
                    val x = hx + (3 + i * 2) * d + sp * (if (i % 2 == 0) 40 else -30) * dpx
                    val y = groundY - 9 * d - sin(sp * Math.PI).toFloat() * 60 * dpx * z
                    c.drawRect(x, y, x + d * 1.5f, y + d * 0.5f, fill)
                }
            }
            "box" -> {
                val bx = partyX0 + BOX_DX * dpx
                drawProp(c, "box", 1, bx, boxBottom(pa, groundY), d * 1.5f)        // 앞판만 — 고양이가 안에서 빼꼼
                val tt = pa - 450L
                if (tt in 1300..1900) outlined(c, "쏙!", bx - 20 * dpx, groundY - icon * 1.3f, RED, 26f)
                if (tt > 2000) {
                    for (i in 0 until 3) {
                        val q = (t * 0.8f + i / 3f) % 1f
                        drawProp(c, "heart", 0, bx - 40 * dpx + i * 40 * dpx, groundY - icon * 1.1f - q * 120 * dpx, dot * 0.9f, alpha = (255 * (1 - q)).toInt())
                    }
                    outlined(c, "상자 최고!", bx - 70 * dpx, groundY - icon * 1.9f, INK, 24f)
                }
            }
            "podium" -> {
                val tt = pa - 450L
                if (tt > 700) {
                    val k = ((tt - 700) / 300f).coerceAtMost(1f)
                    val headTop = cy - icon * z * 0.5f + partyHop(pa)
                    drawProp(c, "trophy", ((pa / 260) % 2).toInt(), cx, headTop - 4 * dpx + sin(t * 6.0).toFloat() * 4 * dpx + (1 - k) * 40 * dpx, d * 0.8f)
                    outlined(c, "1등!", partyX0 + 90 * dpx, groundY - PODIUM_TOP * d - 20 * dpx, RED, 30f)
                }
                confetti(c, t, partyX0, groundY)
            }
            "frisbee" -> {
                val tt = pa - 450L
                val mouthX = cx + w * 0.38f
                val mouthY = cy - icon * z * 0.1f + partyHop(pa)
                val fp = d * 0.7f
                if (tt < 1050) {
                    val k = (tt / 1050f).coerceIn(0f, 1f)
                    val fx = mouthX + (1 - k) * 520 * dpx
                    val fy = mouthY - sin(k * Math.PI).toFloat() * 160 * dpx - (1 - k) * 40 * dpx
                    drawProp(c, "frisbee", ((pa / 90) % 2).toInt(), fx, fy + 12 * fp, fp)
                } else {
                    drawProp(c, "frisbee", 0, mouthX, mouthY + 12 * fp, fp, rot = sin(t * 12.0).toFloat() * 10f)
                    if (tt < 1900) outlined(c, "덥석!", mouthX - 20 * dpx, groundY - icon * 1.6f, RED, 26f)
                    else outlined(c, "나이스 캐치!", cx - 70 * dpx, groundY - icon * 1.7f, INK, 24f)
                }
            }
            "medal" -> {
                val k = (t / 0.9f).coerceAtMost(1f)
                val mp = d * 0.6f
                val nx = cx + w * 0.22f
                val ny = cy + partyHop(pa)
                val y = ny - (1 - k) * (1 - k) * 420 * dpx
                drawProp(c, "medal", 0, nx, y + 12 * mp, mp, rot = if (k >= 1f) sin(t * 5.0).toFloat() * 10f else 0f)
                if (k >= 1f) {
                    for (i in 0 until 3) {
                        val q = (t * 0.7f + i / 3f) % 1f
                        drawProp(c, "heart", 0, cx - 50 * dpx + i * 50 * dpx, cy - icon * z * 0.6f - q * 110 * dpx, dot * 0.8f, alpha = (255 * (1 - q)).toInt())
                    }
                    outlined(c, "착한 강아지 메달!", cx - 100 * dpx, groundY - icon * 1.8f, RED, 24f)
                }
            }
            "crown" -> {
                val k = (t / 0.9f).coerceAtMost(1f)
                val cp = d * 0.55f
                val hx = cx + w * 0.27f
                val crownBottom = cy - icon * z * 0.36f + partyHop(pa)
                drawProp(c, "crown", if (k >= 1f) ((pa / 240) % 2).toInt() else 0, hx, crownBottom - (1 - k) * (1 - k) * 380 * dpx, cp, rot = if (k >= 1f) -8f else 0f)
                if (k >= 1f) {
                    sparkle(c, hx - 34 * dpx, crownBottom - 40 * dpx, (4 + 10 * abs(sin(t * 5.0)).toFloat()) * dpx, GOLD)
                    sparkle(c, hx + 36 * dpx, crownBottom - 20 * dpx, (4 + 10 * abs(sin(t * 4.0 + 1)).toFloat()) * dpx, GOLD)
                    outlined(c, if (charName == "trex") "공룡의 왕!" else "왕의 귀환!", cx - 80 * dpx, groundY - icon * 1.9f, RED, 28f)
                }
                confetti(c, t, partyX0, groundY)
            }
            "carrot" -> {
                val cp = d * 0.6f
                val mx = cx + w * 0.42f
                val my = groundY - icon * z * 0.55f
                val k = (t / 0.8f).coerceAtMost(1f)
                if (k < 1f) {
                    drawProp(c, "carrot", 0, mx + (1 - k) * 380 * dpx, my - sin(k * Math.PI).toFloat() * 140 * dpx + 12 * cp, cp, rot = k * 540f)
                } else {
                    drawProp(c, "carrot", 0, mx + 8 * dpx, my + 12 * cp, cp, rot = -60f + sin(t * 10.0).toFloat() * 6f)
                    fill.color = 0xFFF57C00.toInt()
                    for (i in 0 until 4) {
                        val q = (t * 2f + i / 4f) % 1f
                        c.drawRect(mx + (i - 2) * 8 * dpx, my + q * 60 * dpx, mx + (i - 2) * 8 * dpx + d, my + q * 60 * dpx + d, fill)
                    }
                    outlined(c, "아삭아삭!", cx - 60 * dpx, groundY - icon * 1.7f, INK, 24f)
                }
            }
            "carwash" -> {
                if (t < 2.6f) {                                    // 물줄기 + 거품이 차를 덮는다
                    fill.color = 0xFF4FC3F7.toInt()
                    for (i in 0 until 10) {
                        val q = (t * 1.6f + i * 0.1f) % 1f
                        val x = cx - w * 0.6f + (i * 37 % 100) / 100f * w * 1.2f
                        val y = groundY - 300 * dpx + q * 280 * dpx
                        c.drawRect(x, y, x + d * 0.8f, y + d * 2f, fill)
                    }
                    for (i in 0 until 3) drawProp(c, "carwash", ((pa / 220) + i).toInt(), cx - w * 0.35f + i * w * 0.35f, groundY + 4 * dpx, d * 0.9f)
                    outlined(c, "보글보글 세차 중~", cx - 90 * dpx, groundY - icon * 1.7f, 0xFF1E88E5.toInt(), 24f)
                } else {
                    for (i in 0 until 4) sparkle(c, cx - w * 0.5f + i * w * 0.33f, cy - icon * z * (0.2f + (i % 2) * 0.3f), (6 + 8 * abs(sin(t * 6.0 + i)).toFloat()) * dpx, if (i % 2 == 0) GOLD else 0xFF4FC3F7.toInt())
                    outlined(c, "반짝반짝 세차 완료!", cx - 100 * dpx, groundY - icon * 1.7f, RED, 24f)
                }
            }
            "chest" -> if (t > 0.9f) {                             // 상자가 열리고 코인이 퐁퐁
                val chx = partyX0 + w * 0.15f
                for (i in 0 until 6) {
                    val q = (t - 0.9f) * 0.9f - i * 0.12f
                    if (q !in 0f..1f) continue
                    val x = chx + (i - 2.5f) * 50 * dpx * q
                    val y = groundY - 12 * d - 4 * q * (1 - q) * 220 * dpx
                    drawCoin(c, x, y, icon * 0.45f, SystemClock.uptimeMillis(), i)
                }
                outlined(c, "보물이다!", chx - 60 * dpx, groundY - icon * 2.0f, RED, 28f)
            }
            "cake" -> {
                val kx = front + 40 * dpx
                if (charName == "dragon" && t < 1.0f) {               // 작은 불꽃으로 촛불 붙이기
                    val sx = cx + w * 0.48f
                    val sy = cy - icon * z * 0.1f
                    for (i in 0 until 6) {
                        val q = (t * 3 + i / 6f) % 1f
                        fill.color = FLAME[i % FLAME.size]
                        val x = sx + (kx - sx) * q
                        val y = sy + (groundY - 22 * d - sy) * q
                        c.drawRect(x, y, x + d * 1.2f, y + d * 1.2f, fill)
                    }
                }
                drawProp(c, "cake", ((pa / 200) % 2).toInt(), kx, groundY, d)
                if (t > 1.0f) {
                    for (i in 0 until 2) {
                        val q = (t * 0.6f + i / 2f) % 1f
                        drawProp(c, "heart", 0, kx - 30 * dpx + i * 60 * dpx, groundY - 26 * d - q * 100 * dpx, dot * 0.8f, alpha = (255 * (1 - q)).toInt())
                    }
                    outlined(c, "생일 축하해~", kx - 70 * dpx, groundY - icon * 1.8f, RED, 24f)
                }
            }
            "candy" -> {
                val bx = front + 30 * dpx
                val bp = d * 0.9f
                drawProp(c, "candybag", 0, bx, groundY, bp)
                for (i in 0 until 8) {
                    val q = t * 0.8f - i * 0.18f
                    if (q !in 0f..1f) continue
                    val x = bx + ((i * 53) % 9 - 4) * 30 * dpx * q
                    val y = groundY - 22 * bp - 4 * q * (1 - q) * 200 * dpx + q * q * 60 * dpx
                    fill.color = CANDY[i % CANDY.size]
                    c.drawRect(x - d, y - d * 0.7f, x + d, y + d * 0.7f, fill)
                    fill.color = 0xFFFFE0B2.toInt()
                    c.drawRect(x - d * 1.8f, y - d * 0.4f, x - d, y + d * 0.4f, fill)
                    c.drawRect(x + d, y - d * 0.4f, x + d * 1.8f, y + d * 0.4f, fill)
                }
                outlined(c, "사탕 한가득!", cx - 70 * dpx, groundY - icon * 1.8f, 0xFFF57C00.toInt(), 26f)
            }
            "cauldron" -> {
                val kx = cx + w * 0.1f
                val kp = d * 1.1f
                drawProp(c, "cauldron", ((pa / 260) % 2).toInt(), kx, groundY, kp)
                for (i in 0 until 5) {
                    val q = (t * 0.7f + i / 5f) % 1f
                    sparkle(c, kx + sin((t * 2 + i).toDouble()).toFloat() * 30 * dpx, groundY - 24 * kp - q * 200 * dpx, (5 + 7 * (1 - q)) * dpx, if (i % 2 == 0) 0xFF7CFC6A.toInt() else 0xFFB388FF.toInt())
                }
                if (t > 1.2f) outlined(c, "수리수리 마수리!", cx - 90 * dpx, groundY - icon * 2.0f, 0xFF7B3FC4.toInt(), 26f)
            }
            "gift" -> {
                val heli = charName == "heli"
                val gx = if (heli) cx + w * 0.05f else front + 30 * dpx
                val gp = d * 0.9f
                val bottom = if (heli) {                               // 헬기는 밧줄로 내려 준다
                    val k = ((t - 0.3f) / 1.3f).coerceIn(0f, 1f)
                    val by = under + 24 * gp + (groundY - under - 24 * gp) * k
                    if (k < 1f) { fill.color = 0xFF7C4C1C.toInt(); c.drawRect(gx - 2 * dpx, under, gx + 2 * dpx, by - 20 * gp, fill) }
                    by
                } else groundY
                val open = t > 1.9f
                drawProp(c, "gift", if (open) 1 else 0, gx, bottom, gp)
                if (open) {
                    sparkle(c, gx - 30 * dpx, bottom - 26 * gp, (5 + 8 * abs(sin(t * 6.0)).toFloat()) * dpx, GOLD)
                    sparkle(c, gx + 30 * dpx, bottom - 22 * gp, (5 + 8 * abs(sin(t * 5.0 + 1)).toFloat()) * dpx, GOLD)
                    outlined(c, "선물 도착!", gx + 40 * dpx, groundY - icon * 0.9f, RED, 26f)
                    confetti(c, t, partyX0, groundY)
                }
            }
            "helipad" -> {                                            // 양쪽 조명이 착륙하는 헬기를 비춘다
                val x0 = partyX0
                for (sd in intArrayOf(-1, 1)) {
                    val lx = x0 + sd * 230 * dpx
                    val ly = groundY - 180 * dpx
                    val sweep = sin(t * 2.0 + sd).toFloat() * 30 * dpx
                    fill.color = 0x33FFF59D
                    val path = android.graphics.Path().apply {
                        moveTo(lx, ly); lineTo(x0 + sweep - 70 * dpx, groundY); lineTo(x0 + sweep + 70 * dpx, groundY); close()
                    }
                    c.drawPath(path, fill)
                    drawProp(c, "spotlight", 0, lx, ly + 8 * dot * 1.6f, dot * 1.6f, flip = sd > 0)
                }
                if (t > 1.6f) outlined(c, "착륙 성공!", x0 - 70 * dpx, groundY - icon * 1.9f, RED, 28f)
            }
            "cropcircle" -> {
                if (t < 2.5f) {                                       // 빔이 땅을 쓸며 무늬를 그린다
                    val sweep = sin(t * 3.0).toFloat() * 60 * dpx * z
                    fill.color = 0x7758D854
                    val path = android.graphics.Path().apply {
                        moveTo(cx - 14 * dpx * z, under - 4 * dpx); lineTo(cx + 14 * dpx * z, under - 4 * dpx)
                        lineTo(cx + sweep + 50 * dpx * z, groundY); lineTo(cx + sweep - 50 * dpx * z, groundY); close()
                    }
                    c.drawPath(path, fill)
                } else {
                    for (i in 0 until 3) sparkle(c, partyX0 - 80 * dpx + i * 80 * dpx, groundY - 30 * dpx - (i % 2) * 20 * dpx, (5 + 8 * abs(sin(t * 6.0 + i)).toFloat()) * dpx, GOLD)
                    outlined(c, "미스터리 서클 완성!", partyX0 - 110 * dpx, groundY - icon * 0.9f, 0xFF2E7D32.toInt(), 26f)
                }
            }
            "fossil" -> {
                val fx = front + 40 * dpx
                val k = ((t - 0.2f) / 1.0f).coerceIn(0f, 1f)
                val fh = 22 * d
                c.save()
                c.clipRect(fx - 70 * dpx, 0f, fx + 70 * dpx, groundY + 1)
                drawProp(c, "fossil", 0, fx, groundY + fh * (1 - k), d)
                c.restore()
                if (k < 1f) {
                    fill.color = 0x99A08060.toInt()
                    for (i in 0 until 8) {
                        val ph = (t * 3 + i * 0.13f) % 1f
                        val x = fx + ((i * 37) % 100 - 50) / 50f * 50 * dpx
                        val y = groundY - ph * 50 * dpx
                        val sz = 7 * dpx * (1 - ph)
                        c.drawRect(x, y, x + sz, y + sz, fill)
                    }
                } else {
                    sparkle(c, fx + 10 * dpx, groundY - fh - 8 * dpx, (6 + 8 * abs(sin(t * 6.0)).toFloat()) * dpx, GOLD)
                    outlined(c, "화석 발견!", cx - 60 * dpx, groundY - icon * 1.8f, RED, 28f)
                }
            }
            "pinata" -> {
                val tt = pa - 450L
                val ax = front + 50 * dpx
                val ay = groundY - icon * z * 1.75f
                val hit = tt >= 1300
                val swing = if (hit) sin((tt - 1300) / 90.0).toFloat() * 18f * ((2200 - tt) / 900f).coerceAtLeast(0f) else sin(t * 3.0).toFloat() * 10f
                fill.color = 0xFF8D6E63.toInt()
                c.drawRect(ax - 70 * dpx, ay - 96 * dpx, ax + 70 * dpx, ay - 88 * dpx, fill)     // 나뭇가지
                c.drawRect(ax - 1.5f * dpx, ay - 90 * dpx, ax + 1.5f * dpx, ay, fill)            // 끈
                val pp = d * 0.9f
                c.save()
                c.rotate(swing, ax, ay)
                drawProp(c, "pinata", if (hit) 1 else 0, ax, ay + 24 * pp, pp)
                c.restore()
                if (hit) {
                    if (tt < 1700) outlined(c, "와장창!", ax - 50 * dpx, ay - 10 * dpx, RED, 30f)
                    val fall = groundY - 4 * dpx - (ay + 16 * pp)
                    for (i in 0 until 10) {
                        val q = ((tt - 1300) / 900f - i * 0.05f).coerceIn(0f, 1f)
                        val x = ax + ((i * 41) % 9 - 4) * 16 * dpx
                        val y = ay + 16 * pp + fall * q * q
                        fill.color = CANDY[i % CANDY.size]
                        c.drawRect(x - d, y - d * 0.7f, x + d, y + d * 0.7f, fill)
                    }
                    if (tt > 2300) outlined(c, "사탕 비가 내려요!", cx - 90 * dpx, groundY - icon * 2.1f, 0xFFF57C00.toInt(), 24f)
                }
            }
            "fish" -> {
                val tt = pa - 450L
                val fp = d * 0.8f
                if (tt < 900) {
                    val hopF = abs(sin(tt / 140.0)).toFloat() * 14 * dpx
                    drawProp(c, "fish", ((tt / 140) % 2).toInt(), partyX0, groundY - hopF, fp)
                } else {
                    drawProp(c, "fish", ((pa / 160) % 2).toInt(), cx, cy + icon * z * 0.45f + 22 * fp, fp, rot = sin(t * 8.0).toFloat() * 12f)
                    if (tt < 1900) outlined(c, "낚아챘다!", cx - 60 * dpx, groundY - icon * 2.0f, RED, 26f)
                }
            }
            "balloons" -> {
                drawProp(c, "balloons", ((pa / 400) % 2).toInt(), cx - w * 0.05f, cy - icon * z * 0.3f, d * 1.1f)
                outlined(c, "둥실둥실~", cx + w * 0.5f, cy - icon * z * 0.2f, INK, 24f)
                confetti(c, t, partyX0, groundY)
            }
            "heart" -> {
                val u = (pa - 450f) / (PARTY_MS - 950f)
                if (u > 0.86f) {
                    val k = ((u - 0.86f) / 0.08f).coerceIn(0f, 1f)
                    val hp = dot * 2.6f * k
                    drawProp(c, "heart", ((pa / 200) % 2).toInt(), partyX0, partyY0 - (HEART_RISE - 5 * HEART_S) * dpx + 8 * hp, hp)
                    outlined(c, "사랑해요!", partyX0 - 70 * dpx, partyY0 - (HEART_RISE + 90) * dpx, 0xFFFF4F7A.toInt(), 30f)
                }
            }
        }
        if (partyCameo && charName == "dragon") babyDragon(c, t, partyX0 - bodyW() * z * 0.95f, groundY)
    }

    /** 이스터에그: 알이 톡톡 → 쩍 → 아기 용이 나와 콜록 불꽃 재채기 → 엄마 따라 퍼덕퍼덕 */
    private fun babyDragon(c: Canvas, t: Float, x: Float, groundY: Float) {
        val eggH = 30 * dpx
        val eggW = 24 * dpx
        val shell = 0xFFFFF3D6.toInt()
        if (t < 1.4f) {
            if (t < 0.25f) return
            val wob = if (t > 0.6f) sin(t * 30.0).toFloat() * 5f * ((t - 0.6f) / 0.8f) else 0f
            c.save()
            c.rotate(wob, x, groundY)
            fill.color = INK; c.drawOval(x - eggW / 2 - 2 * dpx, groundY - eggH - 2 * dpx, x + eggW / 2 + 2 * dpx, groundY + 1 * dpx, fill)
            fill.color = shell; c.drawOval(x - eggW / 2, groundY - eggH, x + eggW / 2, groundY, fill)
            fill.color = 0xFFF0A050.toInt()
            c.drawCircle(x - 5 * dpx, groundY - eggH * 0.62f, 3 * dpx, fill)
            c.drawCircle(x + 6 * dpx, groundY - eggH * 0.35f, 4 * dpx, fill)
            if (t > 1.0f) {                                          // 금이 쩍
                fill.color = INK
                for (k in 0 until 6) c.drawRect(x - eggW / 2 + k * 4 * dpx, groundY - eggH * 0.55f - (k % 2) * 4 * dpx, x - eggW / 2 + k * 4 * dpx + 4 * dpx, groundY - eggH * 0.55f - (k % 2) * 4 * dpx + 2 * dpx, fill)
            }
            c.restore()
            if (t > 0.6f) outlined(c, if (t > 1.0f) "쩌억!" else "톡… 톡…", x - 30 * dpx, groundY - eggH - 16 * dpx, INK, 18f)
            return
        }
        val k = ((t - 1.4f) / 0.3f).coerceIn(0f, 1f)
        val hop = if (t > 2.6f) abs(sin(t * 8.0)).toFloat() * 10 * dpx else 0f
        val h = icon * 0.5f * (0.6f + 0.4f * k)
        mini(c, idleSheet ?: walkSheet, x, groundY - eggH * 0.25f - hop, h)
        fill.color = INK; c.drawArc(x - eggW / 2 - 2 * dpx, groundY - eggH * 0.6f - 2 * dpx, x + eggW / 2 + 2 * dpx, groundY + 1 * dpx, 0f, 180f, true, fill)
        fill.color = shell; c.drawArc(x - eggW / 2, groundY - eggH * 0.6f, x + eggW / 2, groundY, 0f, 180f, true, fill)
        if (t in 1.9f..2.4f) {                                       // 콜록! 작은 불꽃 재채기
            for (i in 0 until 5) {
                val q = ((t - 1.9f) / 0.5f + i * 0.08f).coerceAtMost(1f)
                fill.color = FLAME[i % FLAME.size]
                val fx = x + h * 0.45f + q * 50 * dpx
                c.drawRect(fx, groundY - h * 0.75f - i * 2 * dpx, fx + 5 * dpx, groundY - h * 0.75f - i * 2 * dpx + 5 * dpx, fill)
            }
            outlined(c, "콜록! 퐁", x - 20 * dpx, groundY - h - 24 * dpx, RED, 20f)
        } else if (t > 2.4f) outlined(c, "아기 용 깜짝 등장!", x - 70 * dpx, groundY - h - 24 * dpx, 0xFFE65100.toInt(), 20f)
    }

    /** 캐릭터 뒤에 깔리는 소품 (상자 뒤판 · 시상대 · 헬기장 · 미스터리 서클 · 보물상자) */
    private fun ceremonyBack(c: Canvas, pa: Long, groundY: Float, z: Float) {
        if (pa < 350 || pa > PARTY_MS - 350) return
        val t = (pa - 350) / 1000f
        val d = dot * z * 0.85f
        val x0 = partyX0
        when (partyKind) {
            "box" -> drawProp(c, "box", 0, x0 + BOX_DX * dpx, boxBottom(pa, groundY), d * 1.5f)
            "podium" -> drawProp(c, "podium", 0, x0, groundY, d)
            "helipad" -> drawProp(c, "helipad", 0, x0, groundY, d * 1.6f)
            "chest" -> drawProp(c, "chest", if (t > 0.9f) 1 else 0, x0 + bodyW() * z * 0.15f, groundY, d * 1.2f)
            "cropcircle" -> {
                val k = ((t - 0.4f) / 2.0f).coerceIn(0f, 1f)
                if (k > 0f) {
                    val hw = 24 * d * 1.6f
                    c.save()
                    c.clipRect(x0 - hw * k, groundY - 30 * d, x0 + hw * k, groundY + 10 * dpx)
                    drawProp(c, "cropcircle", 0, x0, groundY + 6 * dpx, d * 1.6f)
                    c.restore()
                }
            }
        }
    }

    /** 상자가 위에서 툭 떨어진다 */
    private fun boxBottom(pa: Long, groundY: Float): Float {
        val k = ((pa - 450) / 500f).coerceIn(0f, 1f)
        return groundY - (1 - k) * (1 - k) * 420 * dpx
    }

    /** 도착 세레모니: 깃발 위로 폭죽이 연달아 팡팡, 코인 비, 큰 글씨 */
    private fun fireworks(c: Canvas, now: Long, dt: Float, groundY: Float, flagX: Float) {
        if (burstsLeft > 0 && now >= nextBurstAt) {
            burstsLeft--
            nextBurstAt = now + 280 + Random.nextLong(220)
            val bx = (flagX - 520 * dpx + Random.nextFloat() * 620 * dpx).coerceIn(60 * dpx, width - 60 * dpx)
            val by = groundY - (300 + Random.nextFloat() * 260) * dpx
            val color = SPARK_COLORS[Random.nextInt(SPARK_COLORS.size)]
            val n = 26
            for (i in 0 until n) {
                val a = i * (Math.PI * 2 / n)
                val sp = (220 + Random.nextFloat() * 160) * dpx
                sparks += Spark(bx, by, (cos(a) * sp).toFloat(), (sin(a) * sp).toFloat(), if (i % 5 == 0) GOLD else color, 1f)
            }
        }
        val it = sparks.iterator()
        while (it.hasNext()) {
            val p = it.next()
            p.vy += 320 * dpx * dt
            p.vx *= (1f - 0.9f * dt)
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt / 1.2f
            if (p.life <= 0f) { it.remove(); continue }
            fill.color = p.color
            val sz = dot * 1.5f * (0.5f + p.life)
            c.drawRect(p.x, p.y, p.x + sz, p.y + sz, fill)
        }
        val age = now - partyAt
        if (age in 0..PARTY_MS) {
            // 코인 비
            for (i in 0 until 6) {
                val t = (age - i * 220) / 1400f
                if (t !in 0f..1f) continue
                val x = flagX - 420 * dpx + i * 90 * dpx
                drawCoin(c, x, groundY - 520 * dpx + t * 420 * dpx, icon * 0.8f, now, i)
            }
            // 큰 글씨 (톡 튀어나왔다가 자리 잡기)
            val pop = if (age < 300) age / 300f * 1.15f else if (age < 450) 1.15f - (age - 300) / 150f * 0.15f else 1f
            c.save()
            // 커진 캐릭터 머리 위 말풍선(정산)과 겹치지 않게 더 높이
            c.scale(pop, pop, flagX - 200 * dpx, groundY - 470 * dpx)
            outlined(c, "도착!  +${partyCoins}코인", flagX - 420 * dpx, groundY - 470 * dpx, RED, 44f)
            c.restore()
        }
    }

    private fun bodyW(): Float = walkSheet?.let { (it.width / 4) * (icon / it.height) } ?: icon

    /** Pleos 왼쪽 차량 판과 앱 영역의 경계 (2560 화면 기준). 화면이 좁으면 없음 */
    private fun divider(): Float = if (PetScale.isPleos && width > 1800 * dpx) PANEL_DP * dpx else -1f   // Pleos 화면에만 있는 왼쪽 차량 판

    /** 몸통 가운데 (그림을 돌릴 기준점) */
    private fun center(): Pair<Float, Float> = when {
        act == Act.FALL -> fallX to fallY
        surf == Surf.FLOOR -> px to py - icon / 2
        surf == Surf.LEFT -> px + icon / 2 to py
        surf == Surf.RIGHT -> px - icon / 2 to py
        else -> px to py + icon / 2
    }

    /** 달릴 때 고양이가 있어야 할 길 위 자리 (몸 가운데) */
    private var runTarget = 0f

    private fun move(now: Long, dt: Float, groundY: Float) {
        val half = bodyW() * sizeK / 2
        if (!placed) { placed = true; px = width * 0.25f; py = groundY; surf = Surf.FLOOR }
        if (act == Act.FALL) { fallStep(now, dt, groundY, half); return }
        if (driving || now < homeUntil) { runToGoal(dt, groundY); return }
        when (act) {
            Act.FALL, Act.ROAM -> Unit
            Act.HIDE -> {
                // 커튼 쪽으로 걸어 들어가 꼬리만 남기고 멈춘다
                val outside = if (curtainSide < 0) px + half - curtainX else curtainX - (px - half)
                if (outside > TAIL_DP * dpx) {
                    speed = 80 * dpx
                    px += dir * speed * dt
                } else {
                    speed = 0f
                    if (hideUntil == 0L) hideUntil = now + 2500 + Random.nextLong(3500)
                    if (now > hideUntil) comeOut()
                }
                return
            }
            Act.PEEK -> {
                speed = 70 * dpx
                px += dir * speed * dt
                val out = if (curtainSide < 0) px - half - curtainX else curtainX - (px + half)
                if (out > 30 * dpx) { act = Act.ROAM; nextDecision = now + 1200 }
                return
            }
        }
        if (now > nextDecision) decide(now)
        if (idleAct != null && idleAct != "pounce") speed = 0f
        val v = speed
        when (surf) {
            Surf.FLOOR -> {
                py = groundY
                val before = px
                px += dir * v * dt
                val div = divider()
                when {
                    dir < 0 && px - half <= 0f -> edge(0f, -1, false)
                    dir > 0 && px + half >= width -> edge(width.toFloat(), +1, false)
                    div > 0 && dir < 0 && before - half > div && px - half <= div -> edge(div, -1, true)
                    div > 0 && dir > 0 && before + half < div && px + half >= div -> edge(div, +1, true)
                }
            }
            Surf.LEFT, Surf.RIGHT -> {
                val down = if (surf == Surf.LEFT) dir else -dir   // +1 내려감, -1 올라감
                py += down * v * dt
                if (down < 0 && py - half <= 0f) {
                    if (Random.nextFloat() < 0.65f) toCeiling(half) else startFall()
                } else if (down > 0 && py + half >= groundY) {
                    val left = surf == Surf.LEFT
                    surf = Surf.FLOOR
                    py = groundY
                    px = if (left) wallX + half else wallX - half
                    dir = if (left) 1 else -1
                }
            }
            Surf.CEIL -> {
                py = 0f
                px -= dir * v * dt                                  // 거꾸로 붙어 있어서 앞이 반대
                if (dir > 0 && px - half <= 0f) {                   // 왼쪽 끝 → 왼쪽 벽 타고 내려가기
                    surf = Surf.LEFT; wallX = 0f; px = 0f; py = half; dir = 1
                } else if (dir < 0 && px + half >= width) {         // 오른쪽 끝 → 오른쪽 벽
                    surf = Surf.RIGHT; wallX = width.toFloat(); px = wallX; py = half; dir = -1
                }
            }
        }
    }

    private fun fallStep(now: Long, dt: Float, groundY: Float, half: Float) {
        fallVy += 2400 * dpx * dt
        fallY += fallVy * dt
        fallAngle *= (1f - min(1f, dt * 7f))          // 공중에서 몸을 돌려 발로 착지
        if (fallY + icon / 2 >= groundY) {
            surf = Surf.FLOOR
            act = Act.ROAM
            px = fallX.coerceIn(half, width - half)
            py = groundY
            speed = 0f
            nextDecision = now + 700
            landedAt = now                                // 착지: 웅크리고 먼지 탁
        }
    }

    /** 주행 중: 벽·천장·커튼에서 나와 바닥으로 → 길 위 자기 자리까지 뛰어가 깃발 쪽을 보고 달린다 */
    private fun runToGoal(dt: Float, groundY: Float) {
        if (act == Act.HIDE || act == Act.PEEK) act = Act.ROAM
        if (surf != Surf.FLOOR) { startFall(); return }
        py = groundY
        val dash = 420 * dpx
        val dx = runTarget - px
        if (abs(dx) > dash * dt) {
            dir = if (dx > 0) 1 else -1
            speed = dash
            px += dir * dash * dt
        } else {
            px = runTarget
            dir = 1
            speed = if (speedKmh > 1f) 160 * dpx else 0f   // 차가 서면(신호 대기) 그 자리에 앉아 기다린다
        }
    }

    /** 가만히 있을지, 방향을 바꿀지, 뛰어내릴지 — 몇 초마다 고양이 마음대로 */
    private fun decide(now: Long) {
        val r = Random.nextFloat()
        when (surf) {
            Surf.FLOOR -> {
                if (idleAct == "p_uturn") dir = -dir             // 공중 유턴이 끝나면 반대 방향으로
                idleAct = null                                   // 하던 동작은 여기서 끝
                when {
                    r < 0.5f -> { speed = 0f; startIdle(now) }
                    r < 0.65f -> {
                        speed = 80 * dpx
                        val nd = if (Random.nextBoolean()) 1 else -1
                        if (nd != dir && charName == "plane") { uturn(now); return } else dir = nd
                    }
                    else -> speed = 80 * dpx
                }
                // 동작(잠·밥·세수…)을 시작했으면 그 동작이 끝날 때까지 다음 고르기를 미룬다
                nextDecision = if (idleAct != null) idleUntil else now + 1600 + Random.nextLong(2400)
            }
            Surf.LEFT, Surf.RIGHT -> {
                when {
                    r < 0.2f -> speed = 0f
                    r < 0.35f -> startFall()
                    r < 0.5f -> { dir = -dir; speed = 60 * dpx }
                    else -> speed = 60 * dpx
                }
                nextDecision = now + 1200 + Random.nextLong(2000)
            }
            Surf.CEIL -> {
                when {
                    r < 0.35f -> startFall()
                    r < 0.5f -> speed = 0f
                    r < 0.65f -> { dir = -dir; speed = 55 * dpx }
                    else -> speed = 55 * dpx
                }
                nextDecision = now + 1500 + Random.nextLong(2500)
            }
        }
    }

    /** 바닥에서 벽(또는 판 경계)에 닿았을 때: 타고 오르기 · 커튼 뒤로 숨기 · 돌아서기(경계는 그냥 지나가기) */
    /** 비행기 방향 바꾸기 = 공중 유턴 (2초) */
    private fun uturn(now: Long) {
        speed = 0f
        idleAct = "p_uturn"; idleActAt = now; idleUntil = now + 2000
        nextDecision = idleUntil
    }

    private fun edge(x: Float, side: Int, isDivider: Boolean) {
        if (charName == "plane" && !isDivider) { if (idleAct != "p_uturn") uturn(SystemClock.uptimeMillis()); return }
        if (charName in NO_CLIMB) { dir = -dir; return }        // 무거운 공룡·개·말: 벽 앞에서 숨거나 오르지 않고 돌아선다
        val r = Random.nextFloat()
        val canHide = !isDivider || side < 0     // 왼쪽 판 뒤(오른쪽에서 들어갈 때)와 화면 양끝
        // 화면 끝 '커튼 뒤로 숨기'는 쓰지 않는다 (사라진 것처럼 보여서) — 벽을 타거나 돌아선다
        @Suppress("UNUSED_VARIABLE") val unused = canHide
        when {
            mobility == Mobility.WALKER && r < 0.35f && charName !in NO_CLIMB -> climb(x, side)
            isDivider -> Unit
            else -> dir = -dir
        }
    }

    private fun climb(x: Float, side: Int) {
        climbStartAt = SystemClock.uptimeMillis()
        wallX = x
        surf = if (side < 0) Surf.LEFT else Surf.RIGHT
        px = x
        py = height - 4f * dpx - PetScale.stageGroundLift - bodyW() / 2
        dir = if (surf == Surf.LEFT) -1 else 1    // 위쪽으로
        speed = 60 * dpx
    }

    private fun toCeiling(half: Float) {
        val fromLeft = surf == Surf.LEFT
        surf = Surf.CEIL
        py = 0f
        px = if (fromLeft) wallX + half else wallX - half
        dir = if (fromLeft) -1 else 1             // 벽에서 멀어지는 쪽으로
        speed = 55 * dpx
    }

    private fun startFall() {
        val (cx, cy) = center()
        fallX = cx
        fallY = cy
        fallVy = -140 * dpx                       // 살짝 폴짝
        fallAngle = if (surf == Surf.CEIL && Random.nextBoolean()) -180f else surf.angle
        act = Act.FALL
        speed = 0f
    }

    private fun comeOut() {
        act = Act.PEEK
        dir = -curtainSide
        hideUntil = 0L
    }

    private val srcRect = android.graphics.Rect()

    /** 캐릭터: 아이콘과 같은 높이(= 카메라 크기). 몸 가운데를 기준으로 붙은 면에 맞게 돌린다 */
    private fun drawCharacter(c: Canvas, cx: Float, cy: Float, angle: Float, flip: Boolean, walking: Boolean, now: Long, bump: Float, party: Boolean) {
        c.save()
        c.translate(cx, cy)
        c.rotate(angle)
        if (flip) c.scale(-1f, 1f)
        val walk = walkSheet
        if (walk == null) {
            sprite(c, Icons.CAR, -icon / 2, -icon / 2 + bump, dot, false)
            c.restore()
            return
        }
        val face = faceSheet
        val run = runSheet
        val pch = punchSheet
        val pe = now - punchAt
        val procFrame: Triple<Bitmap, Int, Int>? = run {
            val k = idleAct?.takeIf { it.startsWith("p_") && !driving && !party }?.removePrefix("p_") ?: return@run null
            val sh = procSheets[k] ?: return@run null
            val pr = ((now - idleActAt).toFloat() / (idleUntil - idleActAt).coerceAtLeast(1)).coerceIn(0f, 1f)
            if ((k == "meat" && pr < 0.18f) || (k == "fisheat" && pr < 0.25f)) return@run null   // 고기·물고기가 날아오는 동안은 평소 모습
            val n = frameCount(sh)
            if (k == "meat" && n < 4) return@run null                     // 고기가 그려진 옛 그림(3칸)은 안 쓴다 — 고기는 앱이 한 입씩 그린다
            val idx = when (k) {
                "headbutt" -> when { pr < 0.35f -> 0; pr < 0.5f -> 1; pr < 0.75f -> 2; else -> 0 }
                "meat" -> when { pr < 0.7f -> ((now / 160) % 2).toInt(); pr < 0.82f -> 2; else -> 3 }   // 덥석·우물우물 → 꿀꺽 → 꺼억
                "fisheat" -> when { pr < 0.45f -> 0; pr < 0.7f -> 1; else -> 2 }
                "tailswing" -> ((pr * 2f) % 1f).let { ph -> when { ph < 0.35f -> 0; ph < 0.6f -> 1; ph < 0.85f -> 2; else -> 0 } }
                "nap", "doze", "hoard" -> if (n < 3 || pr < 0.12f || pr > 0.92f) 0 else 1 + ((now / 650) % 2).toInt()   // 눕기 → 새근새근 → 일어나기
                in ONCE_ACTS -> (pr * n * 1.25f).toInt()
                else -> ((now / 200) % n).toInt()
            }.coerceIn(0, n - 1)
            Triple(sh, n, idx)
        }
        val (bmp, frames, idx) = when {
            pe in 0..420 && pch != null -> Triple(pch, 2, if (pe < 110) 0 else 1)       // 냥냥 펀치 (준비 → 퍽)
            procFrame != null -> procFrame                                                // 공룡 습성 동작 그림
            now - landedAt < 320 && actSheets["pounce"] != null -> Triple(actSheets["pounce"]!!, 2, 0)   // 착지: 웅크림
            party && partyAct != null && partyAct != "chase" && actSheets[partyAct] != null -> {
                val tt = now - partyAt - 450L
                Triple(actSheets[partyAct]!!, 2, when (partyAct) {
                    "wave" -> ((now / 250) % 2).toInt()
                    "pounce" -> if ((tt - 2500) / 800f < 0.45f) 0 else 1
                    else -> ((now / 350) % 2).toInt()
                })
            }
            idleAct != null && actSheets[idleAct] != null -> {
                val ta = now - idleActAt
                Triple(actSheets[idleAct]!!, 2, when (idleAct) {
                    "groom" -> ((now / 280) % 2).toInt()
                    "stretch" -> if (ta < 1300) 0 else 1
                    "sleep" -> ((now / 900) % 2).toInt()
                    "wave" -> ((now / 250) % 2).toInt()
                    "pounce" -> if (ta < 600 || ta > 1150) 0 else 1
                    else -> ((now / 350) % 2).toInt()
                })
            }
            party && face != null -> Triple(face, 3, 2)                                  // 도착! 웃는 얼굴
            alert && face != null -> Triple(face, 3, 1)                                  // 놀란 얼굴
            act == Act.FALL -> Triple(walk, frameCount(walk), 1)
            // 주행 중엔 전력질주 — 차가 빠를수록 다리도 빨리
            sneaking && walking && sneakSheet != null && !chasing -> {
                val sn = sneakSheet!!
                val n = frameCount(sn)
                Triple(sn, n, ((now / 240) % n).toInt())
            }
            walking && (driving || chasing) && run != null -> {
                val n = frameCount(run)
                // 차가 빠를수록 다리도 빨리, 동물마다 박자는 다르게 (8장짜리 갤럽은 한 장을 조금 짧게)
                val ms = ((if (chasing) 80f else (110 - speedKmh).coerceIn(60f, 110f)) * runBeat() * (if (n > 4) 4f / n * 1.4f else 1f)).toLong().coerceAtLeast(30)
                Triple(run, n, ((now / ms) % n).toInt())
            }
            walking -> { val n = frameCount(walk); Triple(walk, n, ((now / (140 * runBeat() * (if (n > 4) 4f / n * 1.3f else 1f)).toLong().coerceAtLeast(40)) % n).toInt()) }
            talking && face != null -> if ((now / 160) % 2 == 0L) Triple(face, 3, 0) else Triple(idleSheet ?: walk, if (idleSheet != null) 2 else frameCount(walk), 0)
            else -> Triple(idleSheet ?: walk, if (idleSheet != null) 2 else frameCount(walk), if ((now / 100) % 34 == 0L && idleSheet != null) 1 else 0)
        }
        val fw = bmp.width / frames
        val scale = icon / bmp.height
        srcRect.set(idx * fw, 0, idx * fw + fw, bmp.height)
        val w = fw * scale
        if (scared) { bmpPaint.colorFilter = paleFilter; c.translate(((now / 40) % 3 - 1) * 2.5f * dpx, 0f) }
        dst.set(-w / 2, -icon / 2 + bump, w / 2, icon / 2 + bump)
        c.drawBitmap(bmp, srcRect, dst, bmpPaint)
        bmpPaint.colorFilter = null
        c.restore()
    }

    private fun pictogram(t: HazardType): List<String> = when (t) {
        HazardType.CAMERA -> Icons.CAMERA
        HazardType.RAIN -> Icons.CLOUD
        HazardType.ACCIDENT -> if ((SystemClock.uptimeMillis() / 300) % 2 == 0L) BEACON_RED else BEACON_BLUE   // 경광등 번쩍번쩍
        HazardType.POTHOLE -> POTHOLE_PIC                                                                         // 패인 구멍 + 금
        HazardType.HARD_BRAKE -> Icons.WARNING_DIAMOND
        HazardType.POTHOLE, HazardType.DEBRIS, HazardType.CONSTRUCTION, HazardType.ICE, HazardType.BUMP, HazardType.SCHOOL -> Sprites.pictogram(t)
        else -> Icons.WARNING_DIAMOND              // 방지턱·포트홀·낙하물·보호구역·결빙 = 삼각 표지, 공사 = 고깔
    }

    /** 말풍선: 캐릭터 위에, 위가 모자라면(천장) 아래에 */
    private fun bubble(c: Canvas, now: Long, cx: Float, top: Float, bottom: Float) {
        val msg = bubbleText ?: return
        if (now > bubbleUntil + 200) return
        val age = now - bubbleAt
        val scale = when {
            age < 200 -> (age / 200f) * 1.06f
            age < 300 -> 1.06f - (age - 200) / 100f * 0.06f
            now > bubbleUntil -> (1f - (now - bubbleUntil) / 200f).coerceAtLeast(0f)
            else -> 1f
        }
        if (scale <= 0.01f) return
        val maxW = (width * 0.36f).toInt().coerceAtLeast((340 * dpx).toInt())
        bodyText.color = INK
        val lay = layoutCache ?: StaticLayout.Builder.obtain(msg, 0, msg.length, bodyText, maxW)
            .setAlignment(Layout.Alignment.ALIGN_NORMAL).setLineSpacing(6 * dpx, 1f).build().also { layoutCache = it }
        val pad = 20 * dpx
        val tagH = 30 * dpx
        val textW = (0 until lay.lineCount).maxOf { lay.getLineWidth(it) }
        val bw = min(maxW.toFloat(), textW).coerceAtLeast(150 * dpx) + pad * 2
        val bh = lay.height + tagH + pad * 2
        var bx = cx - icon * 0.3f
        if (bx + bw > width - rightReserved - 10 * dpx) bx = width - rightReserved - 10 * dpx - bw
        if (bx < 8 * dpx) bx = 8 * dpx
        val below = top - bh - 26 * dpx < 8 * dpx
        val by = if (below) bottom + 26 * dpx else top - bh - 26 * dpx
        val pivotY = if (below) bottom else top
        val tailX = cx.coerceIn(bx + 20 * dpx, bx + bw - 40 * dpx)
        c.save()
        c.scale(scale, scale, tailX, pivotY)
        val d = 4 * dpx
        val edge = if (bubbleDanger) RED else INK
        stepped(c, bx + d, by + d, bw, bh, d, INK, INK)
        stepped(c, bx, by, bw, bh, d, PAPER, edge)
        // 꼬리 (계단) — 캐릭터 쪽으로
        for (i in 0 until 4) {
            val ty = if (below) by - i * d else by + bh - d + i * d
            fill.color = edge
            c.drawRect(tailX - (4 - i) * d * 0.5f, ty, tailX + (4 - i) * d, ty + d, fill)
            fill.color = PAPER
            if (i < 3) c.drawRect(tailX - (3 - i) * d * 0.5f + d * 0.5f, ty, tailX + (3 - i) * d, ty + d - 0.1f, fill)
        }
        // 태그
        fill.color = edge
        label.color = PAPER
        label.style = Paint.Style.FILL
        val tagW = label.measureText(bubbleTag) + 20 * dpx
        c.drawRect(bx + pad, by + pad - 4 * dpx, bx + pad + tagW, by + pad + tagH - 10 * dpx, fill)
        c.drawText(bubbleTag, bx + pad + 10 * dpx, by + pad + tagH - 17 * dpx, label)
        c.translate(bx + pad, by + pad + tagH)
        lay.draw(c)
        c.restore()
    }

    // ── 배경: 도트 크기(1칸 = 4dp)의 작은 그림으로 한 번 만들어 두고 확대해서 옅게 그린다 ──
    /** 비가 오나 (와이퍼가 켜지면) — 겨울이면 눈 */
    var raining = false
    /** 기상청 예보: 비 · 눈 · 안개 */
    var weatherRain = false
    /** 내가(또는 근처 차가) 제보한 비·눈 */
    var reportRain = false
    var reportSnow = false
    /** 뒤에서 다가오는 긴급차량 */
    var chaser: Hazard? = null
    /** 지금 제한속도 (어린이보호구역 근처 30, 아니면 60) */
    var speedLimit = 60
    private var overSince = 0L
    /** 과속이 2.5초 넘게 이어지는 중 → 사색 */
    private var scared = false
    private val paleFilter = android.graphics.LightingColorFilter(0xB8C8E8, 0x303848)
    // 들은 말 (마이크 버튼 위에 3초)
    private var heardText = ""
    private var heardAt = 0L
    fun showHeard(t: String) { heardText = t; heardAt = SystemClock.uptimeMillis(); invalidate() }
    // 내 제보 소식 말풍선: 제보한 자리 위에 오래 (15초), 350m 넘게 멀어지면 사라짐
    private var reportText = ""
    private var reportAnchor = 0.0
    private var reportUntil = 0L
    fun reportSay(t: String, atM: Double) { reportText = t; reportAnchor = atM; reportUntil = SystemClock.uptimeMillis() + 15_000; invalidate() }
    var snowing = false
    var foggy = false
    /** 상점 배경 테마 ("auto" = 사계절 자동) */
    var theme: String = "auto"
    private val themeBmps = HashMap<String, Bitmap?>()
    private var backBmp: Bitmap? = null
    private var backKey = ""
    private val backPaint = Paint().apply { isFilterBitmap = false; isAntiAlias = false; alpha = BACK_ALPHA }
    private val weatherPaint = Paint().apply { isAntiAlias = false }
    private class Drop(var x: Float, var y: Float, val v: Float)
    private val drops = ArrayList<Drop>()

    /** 0 봄 · 1 여름 · 2 가을 · 3 겨울 (오늘 날짜로) */
    private fun season(): Int = when (java.util.Calendar.getInstance().get(java.util.Calendar.MONTH) + 1) {
        3, 4, 5 -> 0
        6, 7, 8 -> 1
        9, 10, 11 -> 2
        else -> 3
    }

    private fun backdrop(c: Canvas, groundY: Float, dt: Float) {
        val se = season()
        val cols = (width / dot).toInt() + 1
        val rows = BACK_ROWS
        val night = isNight()
        // 탭 Pleos 화면은 그림 위라 더 옅게, 지도 앱 위(탭 '지도' 모드)는 지도를 가리지 않게 배경을 생략
        val mapMode = !PetScale.isPleos && !kr.incar.base.car.CarSpeedSource.available
        backPaint.alpha = if (PetScale.stage) 70 else BACK_ALPHA
        val tb = if (theme != "auto") themeBmps.getOrPut(theme) { load("bg/$theme.png") } else null
        if (mapMode) {
            // 배경 없음
        } else if (tb != null) {
            // 상점 배경: 640x130 도트 그림을 가로로 이어 붙인다 (Pleos 화면 시연에선 왼쪽 차량 판은 비운다)
            val tw = tb.width * dot
            val th = tb.height * dot
            c.save()
            if (PetScale.stage) c.clipRect(width * 852f / 2560f, 0f, width.toFloat(), height.toFloat())
            var x = 0f
            while (x < width) {
                dst.set(x, groundY - th, x + tw, groundY)
                c.drawBitmap(tb, null, dst, backPaint)
                x += tw
            }
            c.restore()
        } else {
            val key = "$cols:$se:$raining:$night"
            if (backKey != key || backBmp == null) {
                backBmp = buildBackdrop(cols, rows, se, raining, night)
                backKey = key
            }
            dst.set(0f, groundY - rows * dot, cols * dot, groundY)
            c.drawBitmap(backBmp!!, null, dst, backPaint)
        }
        // 기상청 안개: 길 위를 옅게 덮는다
        if (foggy) {
            fill.color = 0x40E8ECF2
            c.drawRect(0f, groundY - 320 * dpx, width.toFloat(), groundY, fill)
        }

        // 날씨: 비(파란 빗줄기) · 눈(하얀 송이) — 배경과 같이 옅게
        if (raining || snowing || reportSnow) {
            val snow = se == 3 || snowing || reportSnow
            val top = groundY - 520 * dpx
            while (drops.size < (if (snow) 70 else 110)) {
                drops += Drop(Random.nextFloat() * width, top + Random.nextFloat() * (groundY - top),
                    (if (snow) 60 + Random.nextFloat() * 50 else 520 + Random.nextFloat() * 200) * dpx)
            }
            weatherPaint.color = if (snow) PAPER else 0xFF5A9CE6.toInt()
            weatherPaint.alpha = if (snow) 220 else 150
            for (d in drops) {
                d.y += d.v * dt
                if (snow) d.x += sin((d.y + d.v) / (30 * dpx).toDouble()).toFloat() * 20 * dpx * dt
                if (d.y > groundY) { d.y = top; d.x = Random.nextFloat() * width }
                if (snow) c.drawRect(d.x, d.y, d.x + dot, d.y + dot, weatherPaint)
                else c.drawRect(d.x, d.y, d.x + dot * 0.5f, d.y + dot * 3, weatherPaint)
            }
        } else drops.clear()
    }

    /** 밤인가: 저녁 7시~새벽 6시, 또는 기기 다크 모드 (감응형) */
    private fun isNight(): Boolean {
        val h = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
        val dark = (resources.configuration.uiMode and android.content.res.Configuration.UI_MODE_NIGHT_MASK) == android.content.res.Configuration.UI_MODE_NIGHT_YES
        return h >= 19 || h < 6 || dark
    }

    /** 밤 색으로 어둡게 (푸르스름하게) */
    private fun dusk(c: Int): Int {
        val r = (android.graphics.Color.red(c) * 0.35f + 18).toInt().coerceIn(0, 255)
        val g = (android.graphics.Color.green(c) * 0.38f + 22).toInt().coerceIn(0, 255)
        val b = (android.graphics.Color.blue(c) * 0.5f + 48).toInt().coerceIn(0, 255)
        return android.graphics.Color.rgb(r, g, b)
    }

    /** 산 두 겹 + 나무 줄 + (맑으면) 해·구름, (비 오면) 먹구름, (밤) 달·별. 1픽셀 = 1도트 */
    private fun buildBackdrop(cols: Int, rows: Int, se: Int, rain: Boolean, night: Boolean = false): Bitmap {
        val b = Bitmap.createBitmap(cols, rows, Bitmap.Config.ARGB_8888)
        val cv = Canvas(b)
        val pt = Paint().apply { isAntiAlias = false }
        fun px(x: Int, y: Int, color: Int) { if (x in 0 until cols && y in 0 until rows) b.setPixel(x, y, color) }
        val rnd = Random(7)
        val far0 = intArrayOf(0xFFA8D8A0.toInt(), 0xFF7CC48A.toInt(), 0xFFE8A878.toInt(), 0xFFD8E0EC.toInt())[se]
        val near0 = intArrayOf(0xFF78C070.toInt(), 0xFF4C9C58.toInt(), 0xFFD07840.toInt(), 0xFFB8C4D4.toInt())[se]
        val far = if (night) dusk(far0) else far0
        val near = if (night) dusk(near0) else near0
        val edge = 0xFF5C6470.toInt()
        val cap = PAPER
        // 산: 계단식 삼각형 (먼 산은 크고 옅게, 가까운 산은 작고 진하게)
        fun mountain(cx: Int, h: Int, fillC: Int, snowRows: Int) {
            for (dy in 0..h) {
                val y = rows - 1 - h + dy
                val half = (dy * 1.5f).toInt()
                pt.color = if (dy < snowRows) cap else fillC
                cv.drawRect((cx - half).toFloat(), y.toFloat(), (cx + half + 1).toFloat(), (y + 1).toFloat(), pt)
                px(cx - half, y, edge); px(cx + half, y, edge)
            }
        }
        val farPeaks = listOf(0.12f to 46, 0.34f to 58, 0.58f to 50, 0.80f to 62)
        for ((fx, h) in farPeaks) mountain((cols * fx).toInt(), h, far, if (se == 3 || se == 0) 6 else 0)
        val nearPeaks = listOf(0.24f to 30, 0.47f to 36, 0.69f to 28, 0.92f to 34)
        for ((fx, h) in nearPeaks) mountain((cols * fx).toInt(), h, near, if (se == 3) 5 else 0)
        // 봄 꽃점 · 가을 단풍 얼룩
        if (se == 0 || se == 2) repeat(cols / 3) {
            val x = rnd.nextInt(cols); val y = rows - 1 - rnd.nextInt(30)
            if (b.getPixel(x, y) == near || b.getPixel(x, y) == far) px(x, y, if (se == 0) 0xFFF8A4C0.toInt() else 0xFFF0C040.toInt())
        }
        // 나무: 둥근 나무 · 소나무를 땅을 따라
        val canopy = intArrayOf(0xFFF8B8C8.toInt(), 0xFF3C8C48.toInt(), 0xFFE07830.toInt(), 0)[se].let { if (night && it != 0) dusk(it) else it }
        val canopy2 = intArrayOf(0xFF8CCB7C.toInt(), 0xFF2E7038.toInt(), 0xFFF0B840.toInt(), 0)[se].let { if (night && it != 0) dusk(it) else it }
        val pine = if (night) dusk(0xFF2E6A44.toInt()) else 0xFF2E6A44.toInt()
        val trunk = 0xFF7C5434.toInt()
        var x = 6
        while (x < cols - 6) {
            val gy = rows - 1
            val kind = rnd.nextInt(3)
            if (kind == 0 || se == 3 && kind == 1) {
                // 소나무 (겨울엔 눈 얹음)
                val h = 9 + rnd.nextInt(4)
                for (i in 0 until h - 2) {
                    val w = (i / 2) % 3 + i / 4
                    for (dx in -w..w) px(x + dx, gy - h + i, if (se == 3 && i % 3 == 0) cap else pine)
                }
                px(x, gy - 1, trunk); px(x, gy, trunk)
            } else {
                // 둥근 나무 (겨울엔 앙상한 가지)
                for (i in 0..3) px(x, gy - i, trunk)
                if (se == 3) {
                    px(x - 1, gy - 4, trunk); px(x + 1, gy - 5, trunk); px(x - 2, gy - 5, trunk); px(x + 2, gy - 6, trunk); px(x, gy - 6, trunk)
                } else {
                    for (dy in -3..3) for (dx in -3..3) {
                        if (dx * dx + dy * dy <= 10) px(x + dx, gy - 7 + dy, if ((dx + dy + x) % 3 == 0) canopy2 else canopy)
                    }
                }
            }
            x += 22 + rnd.nextInt(30)
        }
        // 땅 위 풀선 (계절색)
        pt.color = near
        cv.drawRect(0f, (rows - 1).toFloat(), cols.toFloat(), rows.toFloat(), pt)
        // 하늘: 맑으면 해 + 흰 구름, 비면 먹구름 여러 개
        fun cloud(cx: Int, cy: Int, color: Int) {
            for (dy in -3..3) for (dx in -9..9) {
                val r = (dx * dx) / 81f + (dy * dy) / 9f
                if (r <= 1f || (dx in -4..2 && dy in -5..-1 && (dx + 1) * (dx + 1) / 16f + (dy + 2) * (dy + 2) / 9f <= 1f)) px(cx + dx, cy + dy, color)
            }
        }
        if (night) {
            // 별: 하늘 곳곳 작은 점 (몇 개는 십자 반짝)
            repeat(cols / 6) {
                val x = rnd.nextInt(cols); val y = rnd.nextInt(44)
                if (b.getPixel(x, y) == 0) {
                    val star = if (rnd.nextInt(4) == 0) 0xFFF8E8A0.toInt() else 0xFFE8ECF8.toInt()
                    px(x, y, star)
                    if (rnd.nextInt(6) == 0) { px(x - 1, y, star); px(x + 1, y, star); px(x, y - 1, star); px(x, y + 1, star) }
                }
            }
            // 초승달 (큰 원에서 오른쪽 위 원을 빼기)
            val mx = (cols * 0.72f).toInt(); val my = 14
            for (dy in -6..6) for (dx in -6..6) {
                val inMoon = dx * dx + dy * dy <= 36
                val cut = (dx - 3) * (dx - 3) + (dy + 2) * (dy + 2) <= 30
                if (inMoon && !cut) px(mx + dx, my + dy, 0xFFF8E8A0.toInt())
            }
            if (rain) listOf(0.25f, 0.55f, 0.82f).forEachIndexed { i, fx -> cloud((cols * fx).toInt(), 16 + (i % 2) * 6, 0xFF4A5068.toInt()) }
        } else if (rain) {
            listOf(0.18f, 0.40f, 0.63f, 0.85f).forEachIndexed { i, fx -> cloud((cols * fx).toInt(), 12 + (i % 2) * 6, 0xFF8C94A0.toInt()) }
        } else {
            val sx = (cols * 0.72f).toInt(); val sy = 14
            for (dy in -4..4) for (dx in -4..4) if (dx * dx + dy * dy <= 16) px(sx + dx, sy + dy, 0xFFF8C838.toInt())
            for (k in 0 until 8) {
                val a = k * Math.PI / 4
                for (r in 6..7) px(sx + (kotlin.math.cos(a) * r).toInt(), sy + (sin(a) * r).toInt(), 0xFFF8C838.toInt())
            }
            cloud((cols * 0.30f).toInt(), 18, 0xFFF4F6F8.toInt())
            cloud((cols * 0.52f).toInt(), 10, 0xFFF4F6F8.toInt())
        }
        return b
    }

    private fun mountains(c: Canvas, groundY: Float, endX: Float) {
        // 낮은 산 두 봉우리 (회색 선, 고정)
        fill.color = HILL
        val p = dot
        fun peak(cx: Float, h: Int) {
            for (i in 0..h) {
                val y = groundY - (h - i) * p
                c.drawRect(cx - i * p, y, cx - i * p + p, y + p, fill)
                c.drawRect(cx + i * p, y, cx + i * p + p, y + p, fill)
            }
        }
        peak(width * 0.42f, 22)
        peak(width * 0.55f, 15)
        peak(endX - 40 * dpx, 18)
    }

    private fun speedLines(c: Canvas, p: Float, groundY: Float) {
        val a = when { p < 0.1f -> p / 0.1f; p > 0.85f -> (1 - p) / 0.15f; else -> 1f }.coerceIn(0f, 1f)
        fill.color = INK
        fill.alpha = (a * 255).toInt()
        val top = groundY - 300 * dpx
        for (i in 0 until 24) {
            val seed = (i * 73 % 97) / 97f
            val y = top + seed * 290 * dpx
            val len = width * (0.10f + 0.22f * ((i * 31 % 17) / 17f))
            val xx = ((seed * 1.7f + p * 3.2f) % 1.4f - 0.2f) * width
            val th = if (i % 3 == 0) 5 * dpx else 2 * dpx
            c.save()
            c.rotate(-10f, xx, y)
            c.drawRect(xx, y, xx + len, y + th, fill)
            c.restore()
        }
        fill.alpha = 255
    }

    private val bandPath = android.graphics.Path()

    private fun faceCutIn(c: Canvas, cut: Long, groundY: Float) {
        val t = cutInType ?: return
        // 띠: 오른쪽에서 쓱 → 머물고 → 왼쪽으로 쓱
        val slide = when {
            cut < 140 -> 1f - cut / 140f
            cut > 800 -> -(cut - 800) / 150f
            else -> 0f
        }
        val h = 210 * dpx
        val y0 = groundY - 520 * dpx
        val off = slide * width
        val skew = 60 * dpx
        bandPath.reset()
        bandPath.moveTo(off + skew, y0); bandPath.lineTo(off + width.toFloat(), y0)
        bandPath.lineTo(off + width - skew, y0 + h); bandPath.lineTo(off, y0 + h); bandPath.close()
        val tone = CHAR_TONES[charName] ?: CHAR_TONES.getValue("cat")
        fill.color = (tone[0] and 0xFFFFFF) or (0xE6 shl 24)          // 캐릭터 색의 가장 어두운 톤
        c.drawPath(bandPath, fill)
        fill.color = tone[1]                                          // 테두리 = 캐릭터 본색
        c.drawRect(off, y0 - 6 * dpx, off + width, y0, fill)
        c.drawRect(off, y0 + h, off + width, y0 + h + 6 * dpx, fill)
        fill.color = tone[3]                                          // 포인트 색 가는 줄
        c.drawRect(off, y0 - 10 * dpx, off + width, y0 - 7 * dpx, fill)
        c.drawRect(off, y0 + h + 7 * dpx, off + width, y0 + h + 10 * dpx, fill)
        // 띠 안 집중선 (밝은 톤)
        fill.color = (tone[2] and 0xFFFFFF) or (0x55 shl 24)
        for (i in 0 until 10) {
            val ly = y0 + (i * 37 % 200) * dpx
            val lx = off + ((i * 173 + cut * 3) % width.toLong()).toFloat()
            c.drawRect(lx, ly, lx + 160 * dpx, ly + 3 * dpx, fill)
        }
        // 기계: 조종사가 튀어나와 고글(바이저) 위로 빛이 쓱
        val pilot = pilotSheet
        if (pilot != null) {
            val fw = pilot.width / 2
            val sc = (h - 16 * dpx) / pilot.height
            val fx = off + width * 0.14f
            val fy = y0 + 8 * dpx
            val pop = if (cut < 220) 0.7f + 0.3f * (cut / 220f) else 1f
            c.save(); c.scale(pop, pop, fx + fw * sc / 2, fy + pilot.height * sc / 2)
            srcRect.set(fw, 0, fw * 2, pilot.height)
            dst.set(fx, fy, fx + fw * sc, fy + pilot.height * sc)
            c.drawBitmap(pilot, srcRect, dst, bmpPaint)
            pilotGoggle?.let { g ->
                if (cut in 160..560) {
                    val k = (cut - 160) / 400f
                    val gl = fx + g.left * sc; val gt = fy + g.top * sc; val gr = fx + g.right * sc; val gb = fy + g.bottom * sc
                    c.save(); c.clipRect(gl, gt, gr, gb)
                    val sx = gl - (gb - gt) + (gr - gl + (gb - gt) * 2) * k
                    fill.color = 0xE6FFFFFF.toInt()
                    bandPath.reset()
                    bandPath.moveTo(sx, gb); bandPath.lineTo(sx + 3 * sc, gb); bandPath.lineTo(sx + 3 * sc + (gb - gt), gt); bandPath.lineTo(sx + (gb - gt), gt); bandPath.close()
                    c.drawPath(bandPath, fill)
                    fill.color = 0x99FFFFFF.toInt()
                    c.drawRect(sx + 5 * sc, gt, sx + 6 * sc, gb, fill)
                    c.restore()
                }
            }
            c.restore()
        }
        // 동물: 얼굴 클로즈업 (놀란 얼굴, 머리만 크게) + 얼굴 옆에 반짝 ✦
        val face = if (pilot != null) null else faceSheet ?: idleSheet ?: walkSheet
        if (face != null) {
            val frames = if (face == faceSheet) 3 else if (face == idleSheet) 2 else 4
            val fw = face.width / frames
            val col = if (face == faceSheet) 1 else 0
            val head = if (face == faceSheet) android.graphics.Rect(col * fw + 13, 0, col * fw + 33, 16) else android.graphics.Rect(0, 0, fw, face.height)
            val sc = (h - 16 * dpx) / head.height()
            val fx = off + width * 0.16f
            dst.set(fx, y0 + 8 * dpx, fx + head.width() * sc, y0 + 8 * dpx + head.height() * sc)
            c.drawBitmap(face, head, dst, bmpPaint)
            // 번뜩! — 눈 위가 아니라 얼굴 옆에 반짝이 하나가 톡 (만화식)
            if (cut in 160..620) {
                val k = ((cut - 160) / 460f)
                val pop = if (k < 0.3f) k / 0.3f * 1.3f else 1.3f - (k - 0.3f) * 0.5f
                val sx = dst.right + 10 * dpx
                val sy = dst.top + 14 * dpx
                sparkle(c, sx, sy, 22 * dpx * pop, tone[2])
                sparkle(c, sx + 26 * dpx, sy + 36 * dpx, 11 * dpx * pop, PAPER)
            }
        }
        // 위험 그림 + 글자 (컬러 도트 그림, 글자는 캐릭터의 밝은 톤)
        val ph = h * 0.66f
        val hb = hazBitmap(t)
        if (hb != null) frame(c, hb, ((cut / 200) % 2).toInt(), off + width * 0.42f, y0 + h * 0.17f, ph)
        else { val pic = pictogram(t); sprite(c, pic, off + width * 0.42f, y0 + h * 0.19f, (h * 0.62f) / pic.size, false) }
        outlined(c, "위험!", off + width * 0.56f, y0 + h * 0.45f, tone[2], 54f)
        outlined(c, "500m 앞 ${t.label}", off + width * 0.56f, y0 + h * 0.82f, PAPER, 34f)
    }

    /** 스포츠카 도착 세레모니: 철컥철컥 로봇으로 변신 → 근육 자랑 (키 약 2배) */
    private fun drawRobot(c: Canvas, t: Long, cx: Float, groundY: Float, now: Long) {
        val tr = robotTransform ?: return
        val fl = robotFlex ?: return
        // 변신하며 서서히 커진다 (처음엔 달리던 차 크기)
        val h = icon * (1.15f + 0.95f * (t / 700f).coerceIn(0f, 1f))
        val (b, n, i) = if (t < 1400) Triple(tr, 8, (t / 175).toInt().coerceAtMost(7)) else Triple(fl, 4, (((t - 1400) / 260) % 4).toInt())
        val fw = b.width / n
        srcRect.set(i * fw, 0, i * fw + fw, b.height)
        val w = h * fw / b.height
        val bounce = if (t >= 1400) -abs(sin((t - 1400) / 260.0 * Math.PI)).toFloat() * 6 * dpx else 0f
        dst.set(cx - w / 2, groundY - h + bounce, cx + w / 2, groundY + bounce)
        c.drawBitmap(b, srcRect, dst, bmpPaint)
        if (t < 1400) {
            if ((t / 120) % 2 == 0L) outlined(c, "철컥!", cx + w * 0.3f, groundY - h * 0.7f, 0xFF90A4AE.toInt(), 22f)
            if (t > 900) outlined(c, "변신!", cx - 40 * dpx, groundY - h - 16 * dpx, RED, 36f)
        } else {
            outlined(c, "근육 자랑!", cx - 70 * dpx, groundY - h - 16 * dpx, RED, 34f)
            sparkle(c, cx + w * 0.55f, groundY - h * 0.75f, (10 + 6 * abs(sin(now / 150.0)).toFloat()) * dpx, 0xFFFFD23F.toInt())
            sparkle(c, cx - w * 0.55f, groundY - h * 0.55f, (8 + 5 * abs(cos(now / 170.0)).toFloat()) * dpx, PAPER)
        }
    }

    /** 만화식 반짝이 ✦ (네 갈래 별) */
    private fun sparkle(c: Canvas, x: Float, y: Float, r: Float, color: Int) {
        val path = android.graphics.Path().apply {
            moveTo(x, y - r); lineTo(x + r * 0.22f, y - r * 0.22f); lineTo(x + r, y); lineTo(x + r * 0.22f, y + r * 0.22f)
            lineTo(x, y + r); lineTo(x - r * 0.22f, y + r * 0.22f); lineTo(x - r, y); lineTo(x - r * 0.22f, y - r * 0.22f); close()
        }
        val st = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = 3 * dpx; this.color = INK }
        fill.color = color
        c.drawPath(path, fill)
        c.drawPath(path, st)
    }

    private fun cutInSign(c: Canvas, p: Float, groundY: Float, fromX: Float) {
        val t = cutInType ?: return
        val pic = pictogram(t)
        val grow = when { p < 0.15f -> p / 0.15f; p > 0.85f -> (1 - p) / 0.15f; else -> 1f }.coerceIn(0f, 1f)
        val size = icon * (1.2f + 1.3f * grow)
        val px = size / pic.size
        val cx = fromX + icon + 60 * dpx
        sprite(c, pic, cx, groundY - size, px, false)
        if (p in 0.25f..0.9f) {
            label.textSize = 34f * dpx
            outlined(c, "위험! ${t.label}", cx + size + 16 * dpx, groundY - size * 0.55f, RED)
            label.textSize = 18f * dpx
        }
    }

    private fun outlined(c: Canvas, s: String, x: Float, y: Float, color: Int, sizeSp: Float = 0f) {
        val keep = label.textSize
        if (sizeSp > 0f) label.textSize = sizeSp * dpx
        label.style = Paint.Style.STROKE
        label.strokeWidth = (label.textSize * 0.16f).coerceIn(2 * dpx, 5 * dpx)
        label.strokeJoin = Paint.Join.ROUND
        label.color = PAPER
        c.drawText(s, x, y, label)
        label.style = Paint.Style.FILL
        label.color = color
        c.drawText(s, x, y, label)
        label.textSize = keep
    }

    private fun stepped(c: Canvas, x: Float, y: Float, w: Float, h: Float, d: Float, body: Int, line: Int) {
        fill.color = body
        c.drawRect(x + d, y + d, x + w - d, y + h - d, fill)
        fill.color = line
        c.drawRect(x + 2 * d, y, x + w - 2 * d, y + d, fill)
        c.drawRect(x + 2 * d, y + h - d, x + w - 2 * d, y + h, fill)
        c.drawRect(x, y + 2 * d, x + d, y + h - 2 * d, fill)
        c.drawRect(x + w - d, y + 2 * d, x + w, y + h - 2 * d, fill)
        c.drawRect(x + d, y + d, x + 2 * d, y + 2 * d, fill)
        c.drawRect(x + w - 2 * d, y + d, x + w - d, y + 2 * d, fill)
        c.drawRect(x + d, y + h - 2 * d, x + 2 * d, y + h - d, fill)
        c.drawRect(x + w - 2 * d, y + h - 2 * d, x + w - d, y + h - d, fill)
    }

    private val baked = HashMap<Pair<List<String>, Boolean>, Bitmap>()
    private val bmpPaint = Paint().apply { isFilterBitmap = false; isAntiAlias = false }
    private val dst = RectF()

    /** 도트 그림을 1도트=1픽셀 비트맵으로 한 번 구워 두고 확대해서 그린다 */
    private fun sprite(c: Canvas, rows: List<String>, x: Float, y: Float, px: Float, flip: Boolean) {
        val bmp = baked.getOrPut(rows to flip) {
            val w = rows.maxOf { it.length }
            Bitmap.createBitmap(w, rows.size, Bitmap.Config.ARGB_8888).also { b ->
                rows.forEachIndexed { r, line ->
                    line.forEachIndexed { col, ch ->
                        val color = COLORS[ch] ?: return@forEachIndexed
                        b.setPixel(if (flip) w - 1 - col else col, r, color)
                    }
                }
            }
        }
        dst.set(x, y, x + bmp.width * px, y + bmp.height * px)
        c.drawBitmap(bmp, null, dst, bmpPaint)
    }

    companion object {
        const val INK = 0xFF1E1E1E.toInt()
        const val PAPER = 0xFFFFFFFF.toInt()
        const val RED = 0xFFF83800.toInt()
        const val HILL = 0xFFB8B8B8.toInt()
        /** Pleos 왼쪽 차량 판 폭 (2560x1440 화면 기준) */
        const val PANEL_DP = 853
        /** 커튼 뒤로 숨을 때 밖에 남겨 두는 꼬리 길이 */
        const val TAIL_DP = 18
        /** 도착 세레모니 길이 · 클로즈업 배율 */
        const val PARTY_MS = 4800L
        const val ZOOM = 1f
        /** 세레모니 때 폴짝 뛰는 캐릭터 (말·기계·나는 것은 제자리) */
        private val HOPPERS = setOf("dog", "lion", "pumpkin")
        /** 공룡 간판 동작 (고를 때 거의 늘 이걸 선보인다) */
        private val SIGNATURE = mapOf("trex" to "meat", "trike" to "headbutt", "stego" to "tailswing", "ptero" to "fisheat", "brachio" to "reach",
            "ghost" to "swarm", "ufo" to "alien", "heli" to "bucket", "dragon" to "pearl", "witch" to "potion")
        /** 그림을 처음부터 끝까지 한 번 차례로 (마지막 칸에서 멈춤) */
        private val ONCE_ACTS = setOf("roar", "reach", "bellow", "yawn", "rear", "howl", "boo", "hattip", "lights", "peekaboo", "fire")
        /** 몸 기울이기·늘이기로 '자세'를 흉내 내던 동작 — 그림이 생기면 기울이기를 빼고 그림만 (위치 이동은 그대로) */
        private val POSTURE_ACTS = setOf(
            "graze", "drink", "nap", "doze", "hoard", "bow", "howl", "yawn", "claws", "rear", "sniff", "dig", "scratch",
            "sunbask", "wallow", "reach", "bellow", "meat", "shortarms", "hattip", "tailswing", "chomp", "headshake", "roar",
            "mane", "stomp", "snort", "fire", "wag", "seeds", "grin", "glow", "boo", "chill", "sweep", "potion", "pearl",
            "stalk", "bounce", "flash", "honk", "nitro", "wisp", "sparkle", "rollover", "dustroll", "lights", "beam", "search",
        )
        /** 그림 없이는 어색한 자세 (공룡) — 그림이 생기면 그때부터 나온다 */
        private val NEEDS_SHEET = setOf("graze", "drink", "nap", "sunbask", "wallow", "perch", "shortarms")
        private val DINOS = setOf("trex", "trike", "stego", "brachio", "ptero")

        /** 동작별 고증 한 줄 ("기본 이름:동작") — 사실만, 추정은 '~대요·추정돼요' */
        private val ACT_FACTS = mapOf(
            "cat:groom" to "고양이는 깨어 있는 시간의 30~50%를 털 고르기에 써요.",
            "cat:sleep" to "고양이는 하루에 12~16시간 정도 자요.",
            "cat:pounce" to "고양이는 자기 키의 약 5배 높이까지 뛰어오를 수 있어요.",
            "cat:stretch" to "고양이 수염은 몸이 지나갈 수 있는 틈을 재는 자 역할을 해요.",
            "dog:sniff" to "강아지 후각은 사람보다 수만 배 이상 예민해요.",
            "dog:wag" to "강아지가 꼬리를 오른쪽으로 더 흔들면 기분이 좋은 거래요.",
            "dog:howl" to "강아지의 하울링은 늑대 조상에게서 물려받은 버릇이에요.",
            "dog:dig" to "강아지 코 주름은 사람 지문처럼 모두 달라요.",
            "lion:roar" to "사자 울음소리는 8km 밖에서도 들려요.",
            "lion:nap" to "사자는 하루 16~20시간을 쉬거나 자요.",
            "lion:stalk" to "사냥은 주로 암사자들이 힘을 합쳐서 해요.",
            "horse:doze" to "말은 다리를 고정해서 서서도 잘 수 있어요.",
            "horse:dustroll" to "말이 흙에 뒹구는 건 벌레를 쫓고 털을 고르는 거예요.",
            "horse:graze" to "말은 하루 15시간 넘게 풀을 뜯기도 해요.",
            "horse:rear" to "말의 눈은 머리 옆에 있어서 거의 한 바퀴를 다 볼 수 있어요.",
            "car:drift" to "드리프트는 뒷바퀴를 일부러 미끄러뜨려 코너를 도는 기술이에요.",
            "car:flash" to "상향등을 짧게 깜빡이는 '패싱'은 양보나 고마움의 신호로도 써요.",
            "car:honk" to "경적은 위험할 때만 짧게! 그게 운전 매너예요.",
            "plane:rock" to "조종사는 날개를 좌우로 흔들어 인사나 '알겠다'는 신호를 보내요.",
            "plane:touchgo" to "'터치 앤 고'는 바퀴만 닿았다가 바로 다시 뜨는 착륙 연습이에요.",
            "plane:smoke" to "에어쇼의 색 연기는 연기용 기름을 뜨거운 배기에 뿌려 만들어요.",
            "heli:tilt" to "헬기는 앞으로 가려면 몸을 앞으로 기울여야 해요.",
            "heli:bucket" to "산불 헬기는 큰 물주머니로 물을 퍼 날라 불을 꺼요.",
            "heli:hoist" to "구조 헬기는 줄을 감는 '호이스트'로 사람을 끌어 올려요.",
            "heli:search" to "밤 구조 때는 강한 탐조등으로 땅을 비춰요.",
            "ufo:lights" to "영화 '미지와의 조우'에선 외계인과 '레 미 도 도 솔' 다섯 음으로 인사해요.",
            "ufo:beam" to "UFO는 '미확인 비행 물체'의 줄임말이에요.",
            "ufo:alien" to "외계인을 진짜로 만난 사람은 아직 없어요. 그래서 상상하는 재미가 있죠!",
            "dragon:pearl" to "동양의 용은 여의주로 구름과 비를 부른다고 전해져요.",
            "dragon:hoard" to "서양 전설 속 용은 동굴에서 보물을 지킨대요.",
            "dragon:fire" to "용은 12띠 동물 중 유일한 상상의 동물이에요.",
            "ghost:swarm" to "영화 '고스트버스터즈'는 1984년에 나왔어요.",
            "ghost:wisp" to "도깨비불은 밤에 무덤가나 늪에서 보인다는 옛이야기 속 푸른 불이에요.",
            "ghost:boo" to "할로윈은 옛 켈트족의 '삼하인' 축제에서 시작됐어요.",
            "pumpkin:grin" to "잭오랜턴은 원래 호박이 아니라 순무로 만들었어요.",
            "pumpkin:seeds" to "호박씨는 볶으면 고소한 간식이 돼요.",
            "pumpkin:bounce" to "세계에서 가장 무거운 호박은 1톤이 넘어요.",
            "witch:sweep" to "빗자루 탄 마녀 그림은 1451년에 나온 책에 처음 그려졌어요.",
            "witch:hattip" to "검은 고양이는 영국과 일본에선 행운의 상징이기도 해요.",
            "witch:moon" to "보름달은 약 29.5일마다 한 번씩 떠요.",
            "trex:meat" to "티라노는 한 입에 고기 약 230kg을 삼킬 수 있었다고 추정돼요.",
            "trex:shortarms" to "티라노 팔은 약 1m로 짧지만 근육은 아주 튼튼했어요.",
            "trex:roar" to "티라노의 진짜 울음소리는 아무도 몰라요. 영화 소리는 여러 동물 소리를 섞은 거예요.",
            "trex:chomp" to "티라노 이빨은 뿌리까지 약 30cm, 바나나만 했어요.",
            "trex:stomp" to "티라노는 약 6800만~6600만 년 전, 백악기 말에 살았어요.",
            "trike:headbutt" to "트리케라톱스 뼈에서 뿔에 찔린 상처가 발견돼, 서로 뿔싸움을 했던 걸로 보여요.",
            "trike:charge" to "트리케라톱스는 '세 뿔 얼굴'이라는 뜻이에요.",
            "trike:graze" to "앵무새처럼 생긴 부리로 질긴 식물을 끊어 먹었어요.",
            "trike:headshake" to "트리케라톱스는 티라노와 같은 시대, 같은 곳에 살았어요.",
            "trike:wallow" to "머리뼈만 2m가 넘는, 아주 큰 머리를 가졌어요.",
            "stego:tailswing" to "꼬리 끝 가시 4개를 '타고마이저'라고 불러요. 만화에서 나온 이름이에요.",
            "stego:sunbask" to "등판은 체온을 조절하거나 멋을 부리는 데 썼다는 설이 있어요.",
            "stego:graze" to "스테고사우루스는 몸집에 비해 뇌가 아주 작았어요.",
            "stego:nap" to "스테고와 티라노 사이보다, 티라노와 우리 사이가 더 가까워요!",
            "brachio:reach" to "브라키오사우루스가 고개를 들면 약 12m, 아파트 4층 높이예요.",
            "brachio:drink" to "앞다리가 뒷다리보다 길어서 '팔 도마뱀'이라는 이름이 붙었어요.",
            "brachio:stomp" to "몸무게는 약 30~50톤, 코끼리 여러 마리 무게예요.",
            "brachio:bellow" to "약 1억 5천만 년 전, 쥐라기 후기에 살았어요.",
            "ptero:fisheat" to "프테라노돈은 '이빨 없는 날개'라는 뜻이에요. 부리로 물고기를 잡았어요.",
            "ptero:perch" to "익룡은 땅에서 날개를 앞발처럼 짚고 네 발로 걸었어요.",
            "ptero:glide" to "프테라노돈은 날개를 펴면 최대 약 7m나 됐어요.",
            "ptero:dive" to "익룡은 공룡이 아니에요! 공룡의 친척인 날아다니는 파충류예요.",
        )
        /** 차에 탄 아이들을 위한 안전 한 줄 */
        private val SAFETY = listOf(
            "차에서 내릴 땐 찻길 말고 인도 쪽 문으로 내려요.",
            "안전벨트는 어깨와 골반에 딱 맞게 매요.",
            "창문 밖으로 손이나 머리를 내밀면 위험해요.",
            "주차장에선 어른 손을 꼭 잡고 걸어요.",
            "카시트는 내 몸집에 맞는 걸로 꼭 앉아요.",
        )
        /** 몸집 배율 (발밑 기준으로 키운다) — 브라키오사우루스는 고증대로 다른 공룡의 2배 */
        private val SIZE_K = mapOf("brachio" to 2f)
        /** 벽을 못 타는 캐릭터 (너무 무거워서) */
        private val NO_CLIMB = setOf("brachio", "stego", "trike", "dog", "horse")
        /** 동작을 시작할 때 내는 울음 (기분) — 6초에 한 번까지 */
        private val ACT_SOUND = mapOf(
            "roar" to "alert", "bellow" to "alert", "howl" to "alert", "headbutt" to "alert", "swarm" to "alert", "boo" to "alert",
            "rear" to "alert", "tailswing" to "alert", "fire" to "alert", "honk" to "talk", "chomp" to "talk", "reach" to "talk",
            "beam" to "talk", "hover" to "talk", "hattip" to "talk", "meat" to "happy", "fisheat" to "happy", "alien" to "happy",
            "bounce" to "happy", "loop" to "happy", "wag" to "happy", "wave" to "happy",
        )

        /** 도착 세레모니 종류 (기본 이름 → 2~3가지 중 무작위) */
        private val PARTY_KINDS: Map<String, List<String>> = mapOf(
            "cat" to listOf("yarn", "box", "podium"),
            "dog" to listOf("bone", "frisbee", "medal"),
            "lion" to listOf("bbq", "crown", "podium"),
            "horse" to listOf("hay", "carrot", "podium"),
            "car" to listOf("robot", "carwash", "drift"),
            "dragon" to listOf("fire", "chest", "cake"),
            "plane" to listOf("airshow", "heart"),
            "heli" to listOf("dogdrop", "helipad", "gift"),
            "ufo" to listOf("abduct", "cropcircle"),
            "ghost" to listOf("candy", "gift"),
            "pumpkin" to listOf("candy", "cake"),
            "witch" to listOf("cauldron", "candy"),
            "trex" to listOf("fossil", "pinata", "crown"),
            "trike" to listOf("fossil", "pinata"),
            "stego" to listOf("fossil", "pinata"),
            "brachio" to listOf("fossil", "pinata"),
            "ptero" to listOf("fish", "balloons"),
        )
        /** 소품 시트 칸 수 (없으면 1칸) */
        private val PROP_FRAMES = mapOf(
            "trophy" to 2, "crown" to 2, "cake" to 2, "balloons" to 2, "frisbee" to 2, "box" to 2, "chest" to 2,
            "cauldron" to 2, "fish" to 2, "gift" to 2, "confetti" to 4, "heart" to 2, "pinata" to 2, "carwash" to 2,
        )
        private val CANDY = intArrayOf(0xFFE53935.toInt(), 0xFF43A047.toInt(), 0xFF1E88E5.toInt(), 0xFFFFC107.toInt(), 0xFFAB47BC.toInt())
        /** 상자까지 거리(dp) · 시상대 1등 칸 높이(도트) · 하트 크기·높이(dp) */
        private const val BOX_DX = 110f
        private const val PODIUM_TOP = 21f
        private const val HEART_S = 7f
        private const val HEART_RISE = 170f
        /** 주차 중 동작: 이름 → (뽑힐 가중치, 하는 시간 ms) */
        /** 카메라·방지턱 필살기: 시작 거리(m, 카메라 - 나) · 맞는 순간(ms) · 맞을 때 글자 */
        private class Attack(val kind: String, val window: ClosedFloatingPointRange<Double>, val impact: Long, val word: String)
        private val ATTACKS: Map<String, Attack> = mapOf(
            "cat" to Attack("punch", -10.0..18.0, 110, "퍽!"),
            "dog" to Attack("lick", 0.0..30.0, 320, "할짝!"),
            "horse" to Attack("kick", -28.0..-6.0, 160, "뻥!"),
            "lion" to Attack("roar", 10.0..60.0, 360, "어흥!"),
            "ufo" to Attack("meteor", 40.0..130.0, 560, "쾅!"),
            "heli" to Attack("ladder", 10.0..60.0, 380, "철썩!"),
            "plane" to Attack("missile", 40.0..130.0, 480, "펑!"),
            "car" to Attack("ram", -6.0..14.0, 120, "쿵!"),
            "dragon" to Attack("fire", 20.0..80.0, 380, "화르륵!"),
            "ghost" to Attack("possess", 10.0..50.0, 520, "스르륵~"),
            "pumpkin" to Attack("headbutt", -6.0..14.0, 140, "통!"),
            "witch" to Attack("spell", 30.0..110.0, 480, "펑!"),
            "trex" to Attack("bite", -6.0..16.0, 160, "와작!"),
            "trike" to Attack("ram", -6.0..16.0, 130, "쾅!"),
            "stego" to Attack("kick", -28.0..-6.0, 170, "철썩!"),
            "brachio" to Attack("stomp", -4.0..20.0, 260, "쿵!"),
            "ptero" to Attack("possess", 20.0..70.0, 420, "휙!"),
        )

        /** 위험 컷인 톤온톤 배색: [어두운, 본색, 밝은, 포인트] */
        private val CHAR_TONES: Map<String, IntArray> = mapOf(
            "cat" to intArrayOf(0xFF2E3238.toInt(), 0xFF6E747C.toInt(), 0xFFC8CED6.toInt(), 0xFFD62828.toInt()),
            "dog" to intArrayOf(0xFF4A2A0C.toInt(), 0xFFC8843C.toInt(), 0xFFF4D7A8.toInt(), 0xFF2F6FD8.toInt()),
            "lion" to intArrayOf(0xFF5A3406.toInt(), 0xFFE0A030.toInt(), 0xFFFFE08A.toInt(), 0xFFB8561A.toInt()),
            "horse" to intArrayOf(0xFF3A1C0E.toInt(), 0xFFA0522D.toInt(), 0xFFE8B890.toInt(), 0xFFFFFFFF.toInt()),
            "car" to intArrayOf(0xFF4A0808.toInt(), 0xFFD62828.toInt(), 0xFFFFA89A.toInt(), 0xFFFFD23F.toInt()),
            "plane" to intArrayOf(0xFF0D2A5C.toInt(), 0xFF2F80ED.toInt(), 0xFFDDEBFF.toInt(), 0xFFFFD23F.toInt()),
            "heli" to intArrayOf(0xFF4C3800.toInt(), 0xFFF2B600.toInt(), 0xFFFFF0A8.toInt(), 0xFFE53935.toInt()),
            "ufo" to intArrayOf(0xFF1A2622.toInt(), 0xFF5FBF7A.toInt(), 0xFFD2F5DC.toInt(), 0xFFB388FF.toInt()),
            "dragon" to intArrayOf(0xFF4A1E06.toInt(), 0xFFF0883A.toInt(), 0xFFFFDDB8.toInt(), 0xFFE53935.toInt()),
            "ghost" to intArrayOf(0xFF241E38.toInt(), 0xFF9E8CE0.toInt(), 0xFFF2EEFF.toInt(), 0xFF4FC3F7.toInt()),
            "pumpkin" to intArrayOf(0xFF3E1C00.toInt(), 0xFFF57C00.toInt(), 0xFFFFCC80.toInt(), 0xFF43A047.toInt()),
            "witch" to intArrayOf(0xFF1A0D2E.toInt(), 0xFF7B3FC4.toInt(), 0xFFD9C2FF.toInt(), 0xFFFFD23F.toInt()),
            "trex" to intArrayOf(0xFF1B4D2E.toInt(), 0xFF4CAF50.toInt(), 0xFFC8F2C0.toInt(), 0xFFFF7043.toInt()),
            "trike" to intArrayOf(0xFF0D3B44.toInt(), 0xFF26A69A.toInt(), 0xFFB2DFDB.toInt(), 0xFFFFCA28.toInt()),
            "stego" to intArrayOf(0xFF33461A.toInt(), 0xFF9CCC65.toInt(), 0xFFE6F5C8.toInt(), 0xFFFF8F00.toInt()),
            "brachio" to intArrayOf(0xFF2E2350.toInt(), 0xFF8E7CC3.toInt(), 0xFFE4DCFF.toInt(), 0xFF8BC34A.toInt()),
            "ptero" to intArrayOf(0xFF5A1438.toInt(), 0xFFF06292.toInt(), 0xFFFFD6E6.toInt(), 0xFF26C6DA.toInt()),
        )

        /** 그림 시트가 없는 캐릭터의 대기 동작 — 동물은 실제 습성대로, 기계는 특기대로 (이름 to 길이 ms) */
        private val PROC_ACTS: Map<String, List<Pair<String, Long>>> = mapOf(
            "dog" to listOf("chase" to 1800L, "wag" to 1800L, "dig" to 2200L, "sniff" to 2000L, "scratch" to 1500L, "bow" to 1400L, "howl" to 2000L, "rollover" to 2200L),
            "lion" to listOf("roar" to 1800L, "yawn" to 2000L, "nap" to 6000L, "stalk" to 2600L, "mane" to 1200L, "claws" to 1800L),
            "horse" to listOf("rear" to 1800L, "graze" to 3600L, "swish" to 2400L, "dustroll" to 2400L, "stomp" to 1400L, "doze" to 4500L),
            "car" to listOf("drift" to 1800L, "honk" to 1200L, "flash" to 1500L, "hop" to 1100L, "nitro" to 1600L, "wheelie" to 1500L),
            "plane" to listOf("loop" to 2400L, "eight" to 3200L, "roll" to 1700L, "smoke" to 2400L, "rock" to 1800L, "touchgo" to 2800L),
            "heli" to listOf("spin" to 1800L, "search" to 2800L, "hover" to 2200L, "tilt" to 2000L, "hoist" to 3400L, "bucket" to 3600L),
            "ufo" to listOf("beam" to 2600L, "zigzag" to 1700L, "wobble" to 1600L, "alien" to 4600L, "lights" to 2600L, "teleport" to 2200L),
            "dragon" to listOf("fire" to 1700L, "roar" to 1500L, "flap" to 1500L, "snort" to 1600L, "pearl" to 2800L, "hoard" to 4200L),
            "ghost" to listOf("swarm" to 5200L, "boo" to 1600L, "spin" to 1600L, "fade" to 2200L, "wisp" to 2800L, "peekaboo" to 2400L, "chill" to 2200L),
            "pumpkin" to listOf("bounce" to 1500L, "glow" to 2000L, "spin" to 1400L, "tumble" to 1800L, "seeds" to 2000L, "grin" to 2200L),
            "witch" to listOf("loop" to 2400L, "sparkle" to 2200L, "spin" to 1600L, "sweep" to 2800L, "potion" to 2800L, "moon" to 3000L, "hattip" to 1600L),
            "trex" to listOf("meat" to 4600L, "roar" to 1800L, "stomp" to 1500L, "chomp" to 1400L, "shortarms" to 2200L, "swish" to 2000L, "nap" to 5000L),
            "trike" to listOf("headbutt" to 1900L, "charge" to 1600L, "headshake" to 1400L, "graze" to 3200L, "wallow" to 3200L, "stomp" to 1400L, "nap" to 5000L),
            "stego" to listOf("tailswing" to 2200L, "sunbask" to 3600L, "graze" to 3400L, "nap" to 5500L, "swish" to 2000L),
            "brachio" to listOf("reach" to 2800L, "bellow" to 1900L, "drink" to 3000L, "stomp" to 1500L, "graze" to 3400L, "swish" to 2000L, "nap" to 5500L),
            "ptero" to listOf("fisheat" to 2600L, "dive" to 2000L, "glide" to 2600L, "perch" to 3200L, "flap" to 1500L),
        )
        private val IDLE_ACTS = linkedMapOf(
            "groom" to (0.22f to 3600L),
            "stretch" to (0.16f to 2600L),
            "eat" to (0.16f to 4200L),
            "sleep" to (0.12f to 9000L),
            "wave" to (0.12f to 2200L),
            "pounce" to (0.22f to 1500L),
        )
        /** 밥그릇 + 생선 (k 외곽선 · r 빨간 그릇 · m 회색 생선 · w 눈) */
        private val FISH_BOWL = listOf(
            "...mmmmm.m..",
            "..mwmmmmmm..",
            "kkkkkkkkkkkk",
            "krrrrrrrrrrk",
            ".krrrrrrrrk.",
            "..kkkkkkkk..",
        )
        /** 지나칠 때 냥냥 펀치로 날려 버리는 것 (늘 있는 내비 정보) */
        private val PUNCHABLE = setOf(HazardType.CAMERA, HazardType.BUMP)
        /** 주행 중 다가올 때만 보이는 것 */
        private val DRIVING_ONLY = setOf(HazardType.CAMERA, HazardType.SCHOOL)

        /** 24×24 도트 그림 만들기 도우미 */
        private fun grid(draw: ((Int, Int, Char) -> Unit) -> Unit): List<String> {
            val g = Array(24) { CharArray(24) { '.' } }
            draw { x, y, ch -> if (x in 0..23 && y in 0..23) g[y][x] = ch }
            return g.map { String(it) }
        }

        /** 경광등: 받침 + 둥근 등 + 빛줄기 (빨강·파랑 번갈아) */
        private fun beacon(dome: Char) = grid { p ->
            for (x in 4..19) { p(x, 19, 'k'); p(x, 22, 'k') }
            for (y in 19..22) { p(4, y, 'k'); p(19, y, 'k') }
            for (x in 5..18) for (y in 20..21) p(x, y, 'm')
            for (y in 10..18) {
                val half = when (y) { 10 -> 3; 11 -> 4; else -> 5 }
                for (x in 12 - half..11 + half) p(x, y, dome)
                p(11 - half, y, 'k'); p(12 + half, y, 'k')
            }
            for (x in 9..14) p(x, 9, 'k')
            p(9, 12, 'w'); p(9, 13, 'w'); p(10, 11, 'w')
            listOf(3 to 6, 4 to 7, 20 to 6, 19 to 7, 12 to 4, 12 to 5, 1 to 14, 2 to 14, 21 to 14, 22 to 14).forEach { (x, y) -> p(x, y, 'y') }
        }
        val BEACON_RED = beacon('r')
        val BEACON_BLUE = beacon('b')

        /** 포트홀: 회색 아스팔트에 검게 패인 구멍 + 금 + 튄 조각 */
        val POTHOLE_PIC = grid { p ->
            for (y in 15..23) for (x in 0..23) {
                val dx = (x - 11.5) / 11.5; val dy = (y - 19.5) / 4.4
                if (dx * dx + dy * dy <= 1.0) p(x, y, 'm')
            }
            for (y in 17..22) for (x in 5..18) {
                val dx = (x - 11.5) / 6.6; val dy = (y - 19.6) / 2.7
                if (dx * dx + dy * dy <= 1.0) p(x, y, 'k')
            }
            p(9, 19, 'b'); p(10, 19, 'b'); p(14, 20, 'b')
            listOf(1 to 18, 2 to 17, 3 to 17, 20 to 21, 21 to 22, 22 to 22, 4 to 23, 19 to 17, 20 to 16).forEach { (x, y) -> p(x, y, 'k') }
            p(3, 13, 'm'); p(20, 12, 'm'); p(21, 12, 'm')
        }
        /** 배경 높이(도트 수) · 옅기(0~255) */
        const val BACK_ROWS = 130
        const val BACK_ALPHA = 105
        /** 목적지가 없을 때 한 구간 = 앞길 2km */
        const val AHEAD_M = 2000.0
        private val FLAME = intArrayOf(0xFFF83800.toInt(), 0xFFF87858.toInt(), 0xFFF8B800.toInt(), 0xFFF8D878.toInt())

        // 세레모니 소품 (k 외곽선 · w 흰색 · p 분홍 · r 빨강 · y 노랑 · n 갈색 · m 회색 · o 주황)
        private val YARN = listOf(
            "..kkkkk..",
            ".kppprpk.",
            "kpprpppkk",
            "kprppprpk",
            "kppprpppk",
            "kprpppprk",
            "kpprppppk",
            ".kpprppk.",
            "..kkkkk..",
        )
        private val BONE = listOf(
            ".kk.......kk.",
            "kwwkkkkkkkwwk",
            ".kwwwwwwwwwk.",
            "kwwkkkkkkkwwk",
            ".kk.......kk.",
        )
        private val GRILL = listOf(
            "...knnkknnk.....",
            "..knoonnoonk....",
            "kkkkkkkkkkkkkkkk",
            "kmkmkmkmkmkmkmkk",
            "kkkkkkkkkkkkkkkk",
            ".kroorroorroork.",
            ".kkkkkkkkkkkkkk.",
            "..k..........k..",
            "..k..........k..",
            ".kkk........kkk.",
        )
        private val HAY = listOf(
            ".kkkkkkkkkkkk.",
            "kyyynyyyynyyyk",
            "kyyyyyyyyyyyyk",
            "knyyyyynyyyynk",
            "knnnnnnnnnnnnk",
            "kyyynyyyyynyyk",
            "kyyyyyyyyyyyyk",
            "kynyyyynyyyyyk",
            ".kkkkkkkkkkkk.",
        )
        /** 내 제보 글씨 (진한 초록) */
        const val MINE = 0xFF1E8C5A.toInt()
        const val GOLD = 0xFFF8D030.toInt()
        private val SPARK_COLORS = intArrayOf(0xFFF83800.toInt(), 0xFF3CBCFC.toInt(), 0xFFF8A4C0.toInt(), 0xFF58D854.toInt(), 0xFFF8B800.toInt(), 0xFFB878F8.toInt())
        private val COLORS = mapOf(
            'k' to INK, 'w' to PAPER, 'g' to 0xFFB8B8B8.toInt(), 'm' to 0xFF7C7C7C.toInt(), 'r' to RED,
            'y' to 0xFFF8B800.toInt(), 'p' to 0xFFF8A4C0.toInt(), 'b' to 0xFF3CBCFC.toInt(), 'n' to 0xFFAC7C00.toInt(),
            'o' to 0xFFF87858.toInt(), 'G' to 0xFF66D96A.toInt(),
        )
        /** 비행접시에서 내려오는 꼬마 외계인 (팔 벌림 / 만세) */
        private val ALIEN_A = listOf(
            "...k.k...",
            "...k.k...",
            "..kGGGk..",
            ".kGGGGGk.",
            "kGkkGkkGk",
            "kGkwGkwGk",
            ".kGGGGGk.",
            "..kkGkk..",
            "GkGGGGGkG",
            "..kGGGk..",
            "..kG.Gk..",
            ".kk...kk.",
        )
        private val ALIEN_B = listOf(
            "...k.k...",
            "...k.k...",
            "G.kGGGk.G",
            "GkGGGGGkG",
            "kGkkGkkGk",
            "kGkwGkwGk",
            ".kGGGGGk.",
            "..kkGkk..",
            "..kGGGk..",
            "..kGGGk..",
            ".kG...Gk.",
            "kk.....kk",
        )
        val CLOUD_GRAY = Icons.CLOUD.map { it.replace('k', 'g') }
    }
}
