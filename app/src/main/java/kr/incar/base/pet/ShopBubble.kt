package kr.incar.base.pet

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Typeface
import android.os.SystemClock
import android.view.MotionEvent
import android.view.View
import kr.incar.base.tmi.ReportRecord
import kr.incar.base.tmi.ReportStage
import kr.incar.base.tmi.laneText
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 캐릭터·배경 고르기 말풍선 — 화면을 바꾸지 않고 톱니 위 말풍선 안에서 고른다.
 * 칸을 누르면 화면 속 펫이 그 자리에서 바로 그 캐릭터로 바뀌어 장기를 선보인다.
 * 세 번째 탭 '내 기록' = 내가 한 제보가 접수 → 공유 → 확인 → 해결까지 어디쯤 왔는지.
 */
@SuppressLint("ViewConstructor")
class ShopBubble(
    context: Context,
    private val current: () -> String,
    private val currentTheme: () -> String,
    private val owns: (PetChar) -> Boolean,
    private val ownsTheme: (Theme) -> Boolean,
    private val coins: () -> Int,
    private val pick: (PetChar) -> String,
    private val pickTheme: (Theme) -> String,
    private val onClose: () -> Unit,
    private val history: () -> List<ReportRecord> = { emptyList() },
    startTab: Int = 0,
) : View(context) {

    private val dp = PetScale.dp(context)
    private val font = Typeface.createFromAsset(context.assets, "fonts/galmuri11_bold.ttf")
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = font }
    private val fill = Paint()
    private val pix = Paint().apply { isFilterBitmap = false }
    private val src = Rect()
    private val dst = RectF()
    private val cache = HashMap<String, Bitmap?>()
    private fun bmp(p: String) = cache.getOrPut(p) { runCatching { context.assets.open(p).use { BitmapFactory.decodeStream(it) } }.getOrNull() }

    private var tab = startTab
    private var page = 0
    /** 사기 전 확인: 처음 누른 칸 id · 그때 시각 (3초 안에 한 번 더 누르면 산다) */
    private var armed: String? = null
    private var armedAt = 0L
    private fun confirmBuy(id: String, price: Int): Boolean {
        val now = SystemClock.uptimeMillis()
        if (armed == id && now - armedAt in 500..3000) { armed = null; return true }
        if (armed == id && now - armedAt < 500) return false              // 너무 빠른 연타는 무시
        armed = id; armedAt = now
        flash = "한 번 더 누르면 %,d코인에 사요".format(price); flashAt = now
        invalidate()
        return false
    }
    private fun isArmed(id: String) = armed == id && SystemClock.uptimeMillis() - armedAt < 3000
    private var flash = ""
    private var flashAt = 0L
    private val hits = ArrayList<Pair<RectF, () -> Unit>>()

    private val pad = 18f * dp
    private val cols = 5
    private val cell = 128f * dp
    private val gap = 10f * dp
    private val top = 78f * dp
    private val tail = 22f * dp

    fun wantedWidth(): Int = (pad * 2 + cols * cell + (cols - 1) * gap).toInt()
    fun wantedHeight(): Int {
        val rows = (maxOf(Catalog.all.size, Themes.all.size) + cols - 1) / cols
        return (top + rows * (cell + 30f * dp + gap) + pad + 46f * dp + tail).toInt()
    }

    override fun onDraw(c: Canvas) {
        val now = SystemClock.uptimeMillis()
        val w = width.toFloat()
        val h = height - tail
        hits.clear()
        // 말풍선 몸 (도트 테두리 + 아래 꼬리)
        val d = 4 * dp
        fill.color = PetView.INK
        c.drawRect(0f, 0f, w, h, fill)
        fill.color = PetView.PAPER
        c.drawRect(d, d, w - d, h - d, fill)
        for (i in 0..4) {
            fill.color = PetView.INK
            c.drawRect(w - 70 * dp + i * d, h - d + i * d, w - 40 * dp, h + i * d, fill)
            if (i < 4) { fill.color = PetView.PAPER; c.drawRect(w - 70 * dp + i * d + d, h - d + i * d, w - 40 * dp - d, h + i * d - 0.1f, fill) }
        }
        // 탭 + 코인
        tabChip(c, "캐릭터", pad, pad, tab == 0) { tab = 0; invalidate() }
        tabChip(c, "배경", pad + 150 * dp, pad, tab == 1) { tab = 1; invalidate() }
        tabChip(c, "내 기록", pad + 300 * dp, pad, tab == 2) { tab = 2; page = 0; invalidate() }
        label(c, "코인 %,d".format(coins()), w - pad - 150 * dp, pad + 34 * dp, 24f, PetView.INK)
        when (tab) { 0 -> chars(c, now); 1 -> themes(c, now); else -> records(c, w, h) }
        // 닫기
        val cr = RectF(w - pad - 120 * dp, h - pad - 44 * dp, w - pad, h - pad)
        fill.color = 0xFFEDEDED.toInt(); c.drawRect(cr, fill)
        label(c, "닫기", cr.centerX(), cr.centerY() + 9 * dp, 24f, PetView.INK, Paint.Align.CENTER)
        hits += cr to onClose
        if (tab != 2) label(c, "누르면 바로 바뀌어요 · 사는 건 두 번 눌러요 · 정차 중에만", pad, h - pad - 14 * dp, 22f, PetView.INK, Paint.Align.LEFT, w - pad * 2 - 140 * dp)
        // 큰 알림 글자
        if (flash.isNotEmpty() && now - flashAt < 1200) {
            label(c, flash, w / 2, top + 30 * dp, 40f, PetView.RED, Paint.Align.CENTER)
            postInvalidateOnAnimation()
        }
        postInvalidateDelayed(120)
    }

    private fun tile(i: Int): RectF {
        val x = pad + (i % cols) * (cell + gap)
        val y = top + (i / cols) * (cell + 30f * dp + gap)
        return RectF(x, y, x + cell, y + cell + 30f * dp)
    }

    private fun chars(c: Canvas, now: Long) {
        Catalog.all.forEachIndexed { i, ch ->
            val r = tile(i)
            val mine = owns(ch)
            val using = ch.id == current()
            fill.color = when { using -> 0xFFE3F6E8.toInt(); mine -> 0xFFF4F6FA.toInt(); else -> 0xFFE6E6E6.toInt() }
            c.drawRect(r, fill)
            // 쓰는 중이면 걷는 모습, 아니면 앉은 모습
            val sheet = if (using) bmp("pet/${ch.id}_walk.png") else bmp("pet/${ch.id}_idle.png") ?: bmp("pet/${ch.base}_idle.png")
            sheet?.let { b ->
                val n = Math.round(b.width / (b.height * 34f / 24f)).coerceAtLeast(1)
                val idx = if (using) ((now / 140) % n).toInt() else 0
                val fw = b.width / n
                src.set(idx * fw, 0, idx * fw + fw, b.height)
                val ih = cell * 0.66f
                val iw = ih * fw / b.height
                dst.set(r.centerX() - iw / 2, r.top + 6 * dp, r.centerX() + iw / 2, r.top + 6 * dp + ih)
                pix.alpha = if (mine) 255 else 120
                c.drawBitmap(b, src, dst, pix)
            }
            label(c, ch.name, r.centerX(), r.top + cell * 0.66f + 34 * dp, 23f, PetView.INK, Paint.Align.CENTER, cell - 8 * dp)
            val tag = when {
                using -> "함께"
                mine -> "보유"
                ch.collab -> "잠김"
                isArmed(ch.id) -> "한 번 더!"
                else -> "%,d".format(ch.coins)
            }
            label(c, tag, r.centerX(), r.bottom - 6 * dp, 21f, if (mine) 0xFF1E7A4F.toInt() else 0xFF8A5A00.toInt(), Paint.Align.CENTER)
            if (ch.event) label(c, "🎃", r.right - 16 * dp, r.top + 24 * dp, 18f, 0xFFFF9800.toInt(), Paint.Align.CENTER)
            if (using || isArmed(ch.id)) border(c, r, now)
            hits += r to {
                if (mine || ch.collab || confirmBuy(ch.id, ch.coins)) { flash = pick(ch); flashAt = SystemClock.uptimeMillis(); invalidate() }
            }
        }
    }

    private fun themes(c: Canvas, now: Long) {
        Themes.all.forEachIndexed { i, t ->
            val r = tile(i)
            val mine = ownsTheme(t)
            val using = t.id == currentTheme()
            fill.color = if (using) 0xFFE3F6E8.toInt() else 0xFFF4F6FA.toInt()
            c.drawRect(r, fill)
            val ic = bmp("bg/${t.id}_icon.png")
            val ir = RectF(r.left + 14 * dp, r.top + 8 * dp, r.right - 14 * dp, r.top + cell * 0.7f)
            if (ic != null) { pix.alpha = if (mine) 255 else 140; c.drawBitmap(ic, null, ir, pix) } else {
                val cs = intArrayOf(0xFFF8B8C8.toInt(), 0xFF7CC48A.toInt(), 0xFFE8A878.toInt(), 0xFFD8E0EC.toInt())
                for (k in 0 until 4) { fill.color = cs[k]; c.drawRect(ir.left + ir.width() / 4 * k, ir.top, ir.left + ir.width() / 4 * (k + 1), ir.bottom, fill) }
            }
            label(c, t.name, r.centerX(), r.top + cell * 0.7f + 30 * dp, 18f, PetView.INK, Paint.Align.CENTER, cell - 8 * dp)
            val tag = when { using -> "쓰는 중"; mine -> "보유"; isArmed("bg_" + t.id) -> "한 번 더!"; else -> "%,d".format(t.coins) }
            label(c, tag, r.centerX(), r.bottom - 6 * dp, 18f, if (mine) 0xFF1E8C5A.toInt() else 0xFFB8860B.toInt(), Paint.Align.CENTER)
            if (using || isArmed("bg_" + t.id)) border(c, r, now)
            hits += r to {
                if (mine || confirmBuy("bg_" + t.id, t.coins)) { flash = pickTheme(t); flashAt = SystemClock.uptimeMillis(); invalidate() }
            }
        }
    }

    /** 내 제보 기록: 한 줄에 한 건 (그림 · 무엇 · 언제 · 단계 · 공유/확인/코인) */
    private fun records(c: Canvas, w: Float, h: Float) {
        val list = history()
        val rowH = 74f * dp
        val listTop = top + 44f * dp
        val per = ((h - pad - 60f * dp - listTop) / rowH).toInt().coerceAtLeast(1)
        val pages = ((list.size + per - 1) / per).coerceAtLeast(1)
        page = page.coerceIn(0, pages - 1)
        val ok = list.count { it.stage == ReportStage.CONFIRMED || it.stage == ReportStage.RESOLVED }
        label(c, "내 제보 ${list.size}건 · 확인 ${ok}건 · 받은 코인 %,d".format(list.sumOf { it.coins }), pad, top + 20 * dp, 24f, PetView.INK)
        if (list.isEmpty()) {
            label(c, "아직 제보가 없어요", w / 2, listTop + 120 * dp, 30f, PetView.INK, Paint.Align.CENTER)
            label(c, "운전 중에 \"포트홀!\" \"사고 났어\"처럼 말해 보세요", w / 2, listTop + 170 * dp, 22f, 0xFF555555.toInt(), Paint.Align.CENTER)
            return
        }
        val fmt = SimpleDateFormat("M/d HH:mm", Locale.KOREA)
        list.drop(page * per).take(per).forEachIndexed { i, r ->
            val y = listTop + i * rowH
            fill.color = if (i % 2 == 0) 0xFFF4F6FA.toInt() else 0xFFFFFFFF.toInt()
            c.drawRect(pad, y, w - pad, y + rowH - 6 * dp, fill)
            bmp("pet/haz_${r.type.name.lowercase()}.png")?.let { b ->
                dst.set(pad + 8 * dp, y + 8 * dp, pad + 60 * dp, y + 60 * dp)
                pix.alpha = 255
                c.drawBitmap(b, null, dst, pix)
            }
            val tx = pad + 74 * dp
            label(c, "${laneText(r.lane)}${r.type.label}", tx, y + 30 * dp, 24f, PetView.INK)
            label(c, fmt.format(Date(r.at)), w - pad - 10 * dp, y + 30 * dp, 20f, 0xFF555555.toInt(), Paint.Align.RIGHT)
            // 단계 칩: 지난 단계는 진하게, 지금 단계는 빨강
            var cx = tx
            ReportStage.values().forEach { st ->
                val on = st.ordinal <= r.stage.ordinal
                val chipW = 64f * dp
                fill.color = when { st == r.stage -> PetView.RED; on -> PetView.INK; else -> 0xFFE0E0E0.toInt() }
                c.drawRect(cx, y + 40 * dp, cx + chipW, y + 62 * dp, fill)
                label(c, st.label, cx + chipW / 2, y + 57 * dp, 17f, if (on) PetView.PAPER else 0xFF777777.toInt(), Paint.Align.CENTER)
                cx += chipW + 6 * dp
            }
            val extra = buildList {
                if (r.sharedTo > 0) add("공유 ${r.sharedTo}대")
                if (r.confirms > 0) add("확인 ${r.confirms}명")
                if (r.coins > 0) add("+${r.coins}코인")
            }.joinToString(" · ").ifEmpty { "다른 차의 확인을 기다리는 중" }
            label(c, extra, cx + 10 * dp, y + 58 * dp, 18f, if (r.coins > 0) 0xFF1E8C5A.toInt() else 0xFF555555.toInt())
        }
        if (pages > 1) {
            val by = h - pad - 44 * dp
            val prev = RectF(pad, by, pad + 90 * dp, by + 44 * dp)
            val next = RectF(pad + 200 * dp, by, pad + 290 * dp, by + 44 * dp)
            fill.color = 0xFFEDEDED.toInt(); c.drawRect(prev, fill); c.drawRect(next, fill)
            label(c, "◀ 앞", prev.centerX(), prev.centerY() + 8 * dp, 22f, PetView.INK, Paint.Align.CENTER)
            label(c, "뒤 ▶", next.centerX(), next.centerY() + 8 * dp, 22f, PetView.INK, Paint.Align.CENTER)
            label(c, "${page + 1} / $pages", pad + 145 * dp, by + 30 * dp, 22f, PetView.INK, Paint.Align.CENTER)
            hits += prev to { page = (page - 1).coerceAtLeast(0); invalidate() }
            hits += next to { page = (page + 1).coerceAtMost(pages - 1); invalidate() }
        }
    }

    /** 고른 칸: 노랑↔빨강 번쩍이는 테두리 */
    private fun border(c: Canvas, r: RectF, now: Long) {
        fill.color = if ((now / 180) % 2 == 0L) 0xFFFFD23F.toInt() else PetView.RED
        val b = 4 * dp
        c.drawRect(r.left, r.top, r.right, r.top + b, fill)
        c.drawRect(r.left, r.bottom - b, r.right, r.bottom, fill)
        c.drawRect(r.left, r.top, r.left + b, r.bottom, fill)
        c.drawRect(r.right - b, r.top, r.right, r.bottom, fill)
    }

    private fun tabChip(c: Canvas, s: String, x: Float, y: Float, on: Boolean, act: () -> Unit) {
        val r = RectF(x, y, x + 140 * dp, y + 46 * dp)
        fill.color = if (on) PetView.INK else 0xFFEDEDED.toInt()
        c.drawRect(r, fill)
        label(c, s, r.centerX(), r.centerY() + 9 * dp, 24f, if (on) PetView.PAPER else PetView.INK, Paint.Align.CENTER)
        hits += r to act
    }

    private fun label(c: Canvas, s: String, x: Float, y: Float, size: Float, color: Int, align: Paint.Align = Paint.Align.LEFT, maxW: Float = 0f) {
        text.textSize = size * dp; text.color = color; text.textAlign = align
        if (maxW > 0f) { val m = text.measureText(s); if (m > maxW) text.textSize = text.textSize * maxW / m }   // 긴 이름은 칸에 맞게 줄인다
        c.drawText(s, x, y, text)
    }

    private var downX = -1f
    private var downY = -1f

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(e: MotionEvent): Boolean {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> { downX = e.x; downY = e.y }
            MotionEvent.ACTION_UP -> {
                val h = hits.firstOrNull { it.first.contains(e.x, e.y) && it.first.contains(downX, downY) }?.second
                if (h != null) { performClick(); h() }
                downX = -1f
            }
        }
        return true
    }

    override fun performClick(): Boolean { super.performClick(); return true }
}
