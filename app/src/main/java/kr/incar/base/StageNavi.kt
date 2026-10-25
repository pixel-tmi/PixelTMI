package kr.incar.base

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Typeface
import kr.incar.base.tmi.HazardType
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.min
import kotlin.math.sin
import kotlin.random.Random

/**
 * Pleos 화면 가운데 내비 칸 — 시연용으로 직접 그린 내비.
 * 지도(블록·골목·큰길·강·공원) 위에 파란 경로, 진행 방향이 위로 오는 내 차 화살표, 다음 회전 안내, 길 위 위험 표시, 결승 깃발.
 * 모의 주행 · 출근길 시연 · 실제 길안내(지도 앱) 모두 이 화면으로 보여 준다.
 * 좌표는 미터(m), 화면 y는 아래가 +.
 */
class StageNavi(private val load: (String) -> Bitmap?) {

    private class Seg(val x0: Float, val y0: Float, val dx: Float, val dy: Float, val len: Float, val start: Float, val road: String) {
        val x1 get() = x0 + dx * len
        val y1 get() = y0 + dy * len
    }

    private var routeKey: String? = null
    private var segs: List<Seg> = emptyList()
    /** 경로 전체 길이(m) */
    var total = 0f
        private set
    /** 화면에 보이는 '간 거리' (부드럽게 따라감) */
    private var shown = 0f
    private var heading = 0f
    private val icons = HashMap<String, Bitmap?>()
    private fun icon(name: String) = icons.getOrPut(name) { load(name) }

    private val fill = Paint(Paint.ANTI_ALIAS_FLAG)
    private val line = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeCap = Paint.Cap.ROUND; strokeJoin = Paint.Join.ROUND }
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = Typeface.create("sans-serif", Typeface.BOLD) }
    private val bmp = Paint().apply { isFilterBitmap = false }
    private val src = Rect()
    private val dst = RectF()

    /** 목적지가 바뀌면 경로를 새로 만든다 (같은 목적지는 늘 같은 길) */
    fun setRoute(name: String, totalM: Float) {
        if (name == routeKey && abs(totalM - total) < 1f) return
        if (name != routeKey) {
            routeKey = name
            shown = 0f
            segs = build(name, totalM)
            heading = angleOf(segs.first())
        } else {
            segs = build(name, totalM)   // 길이만 바뀜 (GPS 거리 갱신)
        }
        total = totalM
    }

    fun clearRoute() { routeKey = null; segs = emptyList(); total = 0f; shown = 0f }

    /** 매 프레임: 실제 간 거리 쪽으로 부드럽게 + 속도만큼 미리 */
    fun update(traveledM: Float, kmh: Float, dt: Float) {
        shown += kmh / 3.6f * dt
        shown += (traveledM - shown) * min(1f, dt * 2.5f)
        shown = shown.coerceIn(0f, total)
        segAt(shown)?.let { s ->
            val target = angleOf(s)
            var d = target - heading
            while (d > 180) d -= 360
            while (d < -180) d += 360
            heading += d * min(1f, dt * 3f)
        }
    }

    private fun angleOf(s: Seg) = Math.toDegrees(atan2(s.dx.toDouble(), (-s.dy).toDouble())).toFloat()   // 북=0, 동=90

    private fun segAt(m: Float): Seg? = segs.lastOrNull { it.start <= m } ?: segs.firstOrNull()

    private fun pointAt(m: Float): Pair<Float, Float> {
        val s = segAt(m) ?: return 0f to 0f
        val k = (m - s.start).coerceIn(0f, s.len)
        return (s.x0 + s.dx * k) to (s.y0 + s.dy * k)
    }

    private fun build(name: String, totalM: Float): List<Seg> {
        val r = Random(name.hashCode())
        val roads = ROADS.shuffled(r)
        val out = ArrayList<Seg>()
        var x = 0f; var y = 0f; var acc = 0f
        var dir = 0                                  // 0 북 · 1 동 · 2 남 · 3 서
        var i = 0
        while (acc < totalM - 1f) {
            val want = 260f + r.nextFloat() * 700f
            val len = min(want, totalM - acc).let { if (totalM - acc - it < 120f) totalM - acc else it }
            val (dx, dy) = DIRS[dir]
            out += Seg(x, y, dx, dy, len, acc, roads[i % roads.size])
            x += dx * len; y += dy * len; acc += len; i++
            dir = when (dir) {                       // 대체로 북동쪽으로, 가끔 반대로 꺾는다
                0 -> if (r.nextFloat() < 0.72f) 1 else 3
                1 -> if (r.nextFloat() < 0.75f) 0 else 2
                2 -> 1
                else -> 0
            }
        }
        if (out.isEmpty()) out += Seg(0f, 0f, 0f, -1f, totalM.coerceAtLeast(1f), 0f, roads[0])
        return out
    }

    // ───────────────────────── 그리기 ─────────────────────────

    /**
     * area = 내비 칸(화면 px), s = 그림 배율. 길 위 위험은 (경로 위 거리 m, 종류).
     * 경로가 없으면 내 위치 주변 지도만 (가만히).
     */
    fun draw(c: Canvas, area: RectF, s: Float, hazards: List<Pair<Float, HazardType>>, now: Long) {
        val route = segs.isNotEmpty()
        val (cx, cy) = if (route) pointAt(shown) else 0f to 0f
        val ppm = 1.15f * s                          // 1m = 1.15 그림 px
        val carX = area.left + area.width() * 0.62f
        val carY = area.top + area.height() * 0.70f
        val rot = if (route) heading else 0f
        c.save()
        c.clipRect(area)
        fill.color = 0xFFEEF0F3.toInt()
        c.drawRect(area, fill)
        c.save()
        c.translate(carX, carY)
        c.rotate(-rot)
        c.scale(ppm, ppm)
        c.translate(-cx, -cy)
        val reach = hypot(area.width(), area.height()) / ppm
        drawWorld(c, cx, cy, reach)
        if (route) {
            // 지나온 길(회색) · 앞길(파랑)
            line.strokeWidth = 26f; line.color = 0xFFFFFFFF.toInt()
            drawPath(c, 0f, total)
            line.strokeWidth = 18f; line.color = 0xFFB4BCC8.toInt()
            drawPath(c, 0f, shown)
            line.strokeWidth = 18f; line.color = 0xFF2F80ED.toInt()
            drawPath(c, shown, total)
        }
        c.restore()
        // 위로 세워 그리는 것들: 위험 아이콘 · 깃발 · 내 차
        fun screen(wx: Float, wy: Float): Pair<Float, Float> {
            val dx = wx - cx; val dy = wy - cy
            val a = Math.toRadians(-rot.toDouble())
            val rx = (dx * cos(a) - dy * sin(a)).toFloat()
            val ry = (dx * sin(a) + dy * cos(a)).toFloat()
            return (carX + rx * ppm) to (carY + ry * ppm)
        }
        if (route) {
            hazards.filter { it.first > shown && it.first < total }.forEach { (m, t) ->
                val (hx, hy) = pointAt(m).let { screen(it.first, it.second) }
                if (!area.contains(hx, hy)) return@forEach
                val sz = 70f * s
                val b = icon("pet/haz_${t.name.lowercase()}.png")
                fill.color = 0xFFFFFFFF.toInt()
                c.drawCircle(hx, hy - sz * 0.55f, sz * 0.62f, fill)
                line.strokeWidth = 3f * s; line.color = 0xFFE5484D.toInt()
                c.drawCircle(hx, hy - sz * 0.55f, sz * 0.62f, line)
                if (b != null) frame(c, b, ((now / 400) % 2).toInt(), hx - sz / 2, hy - sz * 1.05f, sz)
                label(c, distText(m - shown), hx, hy + 30f * s, 22f * s, 0xFFE5484D.toInt(), Paint.Align.CENTER)
            }
            val (fx, fy) = segs.last().let { screen(it.x1, it.y1) }
            icon("pet/flag_race.png")?.let { f -> if (area.contains(fx, fy)) frame(c, f, ((now / 140) % 4).toInt(), fx - 10f * s, fy - 96f * s, 96f * s) }
        }
        // 내 차 화살표 (진행 방향이 늘 위)
        fill.color = 0x332F80ED
        c.drawCircle(carX, carY, 60f * s, fill)
        val p = Path().apply {
            moveTo(carX, carY - 38f * s); lineTo(carX + 26f * s, carY + 28f * s)
            lineTo(carX, carY + 14f * s); lineTo(carX - 26f * s, carY + 28f * s); close()
        }
        fill.color = 0xFF1E5BD6.toInt(); c.drawPath(p, fill)
        line.strokeWidth = 5f * s; line.color = 0xFFFFFFFF.toInt(); c.drawPath(p, line)
        c.restore()
    }

    private fun drawPath(c: Canvas, from: Float, to: Float) {
        if (to <= from) return
        val path = Path()
        val (sx, sy) = pointAt(from)
        path.moveTo(sx, sy)
        segs.filter { it.start + it.len > from && it.start < to }.forEach { sg ->
            val e = min(to, sg.start + sg.len)
            val k = e - sg.start
            path.lineTo(sg.x0 + sg.dx * k, sg.y0 + sg.dy * k)
        }
        c.drawPath(path, line)
    }

    /** 블록 · 건물 · 골목(200m) · 큰길(1km) · 강 · 공원 — 같은 자리는 늘 같은 모양 */
    private fun drawWorld(c: Canvas, cx: Float, cy: Float, reach: Float) {
        val g = 200f
        val x0 = floor((cx - reach) / g).toInt(); val x1 = floor((cx + reach) / g).toInt()
        val y0 = floor((cy - reach) / g).toInt(); val y1 = floor((cy + reach) / g).toInt()
        for (gx in x0..x1) for (gy in y0..y1) {
            val h = hash(gx, gy)
            val l = gx * g; val t = gy * g
            when {
                h % 11 == 0 -> { fill.color = 0xFFCDEBC5.toInt(); c.drawRect(l + 14, t + 14, l + g - 14, t + g - 14, fill) }   // 공원
                h % 3 != 0 -> {                                                                                                 // 건물 몇 채
                    fill.color = 0xFFE0E3E8.toInt()
                    val w = 60f + (h % 50); val hh = 50f + (h / 7 % 60)
                    c.drawRect(l + 30, t + 30, l + 30 + w, t + 30 + hh, fill)
                    c.drawRect(l + g - 30 - (h / 3 % 50 + 40), t + g - 30 - (h / 5 % 50 + 40), l + g - 30, t + g - 30, fill)
                }
            }
        }
        // 강 (동서로 굽이치는 띠)
        val river = Path()
        var first = true
        var x = cx - reach
        while (x <= cx + reach) {
            val yy = RIVER_Y + 260f * sin(x / 900f)
            if (first) { river.moveTo(x, yy); first = false } else river.lineTo(x, yy)
            x += 60f
        }
        line.color = 0xFFA9D3F5.toInt(); line.strokeWidth = 150f
        c.drawPath(river, line)
        // 골목
        line.color = 0xFFFFFFFF.toInt(); line.strokeWidth = 12f
        for (gx in x0..x1 + 1) c.drawLine(gx * g, (y0 - 1) * g, gx * g, (y1 + 2) * g, line)
        for (gy in y0..y1 + 1) c.drawLine((x0 - 1) * g, gy * g, (x1 + 2) * g, gy * g, line)
        // 큰길 (1km마다, 연노랑)
        line.color = 0xFFFFF3C4.toInt(); line.strokeWidth = 30f
        val big = 1000f
        for (bx in floor((cx - reach) / big).toInt()..floor((cx + reach) / big).toInt() + 1) c.drawLine(bx * big, cy - reach, bx * big, cy + reach, line)
        for (by in floor((cy - reach) / big).toInt()..floor((cy + reach) / big).toInt() + 1) c.drawLine(cx - reach, by * big, cx + reach, by * big, line)
    }

    private fun hash(a: Int, b: Int): Int {
        var h = a * 73856093 xor b * 19349663
        h = h xor (h ushr 13)
        return abs(h * 1274126177)
    }

    // ───────────────────────── 안내 글자 ─────────────────────────

    /** 다음 회전 안내: (글자, 오른쪽이면 true, 마지막 구간이면 null) */
    fun nextTurn(): Triple<String, String, Boolean?> {
        val i = segs.indexOfLast { it.start <= shown }.coerceAtLeast(0)
        val sg = segs.getOrNull(i) ?: return Triple("", "", null)
        val d = sg.start + sg.len - shown
        val next = segs.getOrNull(i + 1) ?: return Triple("목적지까지 ${distText(d)}", "", null)
        val right = sg.dx * next.dy - sg.dy * next.dx > 0
        return Triple("${distText(d)} 앞 ${if (right) "우회전" else "좌회전"}", "${next.road} 방면", right)
    }

    val remaining: Float get() = (total - shown).coerceAtLeast(0f)
    val roadNow: String get() = segAt(shown)?.road ?: ""

    /** 회전 화살표 (TBT 박스 안) */
    fun drawTurnArrow(c: Canvas, x: Float, y: Float, size: Float, right: Boolean?) {
        line.color = 0xFFFFFFFF.toInt(); line.strokeWidth = size * 0.16f
        val p = Path()
        if (right == null) {                         // 직진(목적지)
            p.moveTo(x, y + size * 0.5f); p.lineTo(x, y - size * 0.35f)
            c.drawPath(p, line)
            arrowHead(c, x, y - size * 0.5f, 0f, size)
        } else {
            val sgn = if (right) 1f else -1f
            p.moveTo(x - sgn * size * 0.2f, y + size * 0.5f)
            p.lineTo(x - sgn * size * 0.2f, y - size * 0.1f)
            p.lineTo(x + sgn * size * 0.3f, y - size * 0.1f)
            c.drawPath(p, line)
            arrowHead(c, x + sgn * size * 0.45f, y - size * 0.1f, if (right) 90f else -90f, size)
        }
    }

    private fun arrowHead(c: Canvas, x: Float, y: Float, deg: Float, size: Float) {
        c.save(); c.translate(x, y); c.rotate(deg)
        val h = Path().apply { moveTo(0f, -size * 0.22f); lineTo(size * 0.22f, size * 0.12f); lineTo(-size * 0.22f, size * 0.12f); close() }
        fill.color = 0xFFFFFFFF.toInt(); c.drawPath(h, fill)
        c.restore()
    }

    private fun frame(c: Canvas, b: Bitmap, idx: Int, x: Float, y: Float, h: Float) {
        val n = (b.width / b.height).coerceAtLeast(1)
        val i = ((idx % n) + n) % n
        src.set(i * b.height, 0, (i + 1) * b.height, b.height)
        dst.set(x, y, x + h, y + h)
        c.drawBitmap(b, src, dst, bmp)
    }

    private fun label(c: Canvas, s: String, x: Float, y: Float, size: Float, color: Int, align: Paint.Align) {
        text.textSize = size; text.textAlign = align
        text.color = 0xFFFFFFFF.toInt(); text.style = Paint.Style.STROKE; text.strokeWidth = size * 0.22f
        c.drawText(s, x, y, text)
        text.color = color; text.style = Paint.Style.FILL
        c.drawText(s, x, y, text)
    }

    companion object {
        private val DIRS = listOf(0f to -1f, 1f to 0f, 0f to 1f, -1f to 0f)
        private val ROADS = listOf("올림픽로", "송파대로", "잠실로", "백제고분로", "강동대로", "천호대로", "양재대로", "테헤란로", "도산대로", "남부순환로", "위례성대로", "석촌호수로")
        private const val RIVER_Y = -1700f
        fun distText(m: Float): String = if (m >= 1000f) "%.1fkm".format(m / 1000f) else "${(m / 10).toInt() * 10}m"
    }
}
