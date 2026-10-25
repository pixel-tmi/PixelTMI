package kr.incar.base.pet

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Typeface
import android.view.MotionEvent
import android.view.View

/**
 * 톱니바퀴를 누르면 올라오는 말풍선 설정 — 한 줄 누르면 바로 바뀐다.
 * rows() 는 매번 새로 불러서 "켜짐/꺼짐" 같은 현재 상태를 보여 준다.
 */
@SuppressLint("ViewConstructor")
class SettingsBubble(
    context: Context,
    private val rows: () -> List<Pair<String, () -> Unit>>,
    private val onClose: () -> Unit,
) : View(context) {

    private val dp = PetScale.dp(context)
    private val font = Typeface.createFromAsset(context.assets, "fonts/galmuri11_bold.ttf")
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = font; textSize = 32f * dp; color = PetView.INK }
    private val fill = Paint()
    private val rowH = 92f * dp
    private val pad = 18f * dp
    private val tail = 22f * dp

    fun wantedHeight(): Int = (rows().size * rowH + pad * 2 + tail).toInt()

    private var pressed = -1

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(e: MotionEvent): Boolean {
        val i = ((e.y - pad) / rowH).toInt().let { if (e.y < pad) -1 else it }
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> { pressed = i; invalidate() }
            MotionEvent.ACTION_MOVE -> if (i != pressed && pressed >= 0) { pressed = -2; invalidate() }   // 미끄러지면 취소
            MotionEvent.ACTION_UP -> {
                val list = rows()
                val hit = pressed
                pressed = -1
                if (hit >= 0 && hit == i && i in list.indices) list[i].second()
                else if (hit == -1 && i !in list.indices) onClose()
                invalidate()
            }
            MotionEvent.ACTION_CANCEL -> { pressed = -1; invalidate() }
        }
        return true
    }

    override fun onDraw(c: Canvas) {
        val d = 4 * dp
        val w = width - d
        val h = height - tail - d
        // 그림자 + 몸통 (계단 모서리)
        box(c, d, d, w, h, d, PetView.INK, PetView.INK)
        box(c, 0f, 0f, w, h, d, PetView.PAPER, PetView.INK)
        // 꼬리 (오른쪽 아래, 톱니 쪽)
        for (i in 0 until 5) {
            fill.color = PetView.INK
            c.drawRect(w - 70 * dp + i * d, h - d + i * d, w - 40 * dp, h + i * d, fill)
            if (i < 4) { fill.color = PetView.PAPER; c.drawRect(w - 70 * dp + i * d + d, h - d + i * d, w - 40 * dp - d, h + i * d - 0.1f, fill) }
        }
        rows().forEachIndexed { i, (label, _) ->
            val y = pad + i * rowH
            if (i == pressed) { fill.color = 0xFFE3EEFF.toInt(); c.drawRect(pad, y + 2 * dp, w - pad, y + rowH, fill) }
            if (i > 0) { fill.color = 0xFFE0E0E0.toInt(); c.drawRect(pad, y, w - pad, y + 2 * dp, fill) }
            val maxW = w - pad * 2 - 16 * dp
            text.textSize = 32f * dp
            val m = text.measureText(label)
            if (m > maxW) text.textSize = (32f * dp * maxW / m).coerceAtLeast(20f * dp)   // 긴 이름은 잘리지 않게 줄인다
            c.drawText(label, pad + 8 * dp, y + rowH * 0.64f, text)
        }
    }

    private fun box(c: Canvas, x: Float, y: Float, w: Float, h: Float, d: Float, body: Int, line: Int) {
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
}
