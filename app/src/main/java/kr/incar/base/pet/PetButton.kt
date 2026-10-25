package kr.incar.base.pet

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.View
import kotlin.math.hypot

/**
 * 화면 오른쪽 끝 작은 도트 버튼 (톱니 = 설정 말풍선, 마이크 = 말하기 …).
 * 버튼 4개는 한 묶음 — 꾹 누르고 있다가(홀드 0.45초, 드르륵) 끌면 묶음째 옮겨진다.
 * 그냥 스치거나 살짝 밀린 건 무시해서 쉽게 흔들리지 않는다. 설정에서 '버튼 위치 고정'이면 아예 안 움직인다.
 */
@SuppressLint("ViewConstructor")
class PetButton(
    context: Context,
    glyph: List<String>,
    private val onTap: () -> Unit,
    /** 옮길 수 있나 (위치 고정이면 false) */
    private val movable: () -> Boolean = { false },
    /** 홀드로 옮기기 시작 / 끄는 중(누른 자리에서 움직인 px) / 끝 */
    private val onMoveStart: (() -> Unit)? = null,
    private val onDrag: ((Float, Float) -> Unit)? = null,
    private val onDragEnd: (() -> Unit)? = null,
    /** 버튼 아래 작은 이름 (소리 · 브리핑 · 말하기 · 설정) */
    private val caption: String = "",
) : View(context) {
    private val capPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        typeface = android.graphics.Typeface.createFromAsset(context.assets, "fonts/galmuri11_bold.ttf")
        textAlign = Paint.Align.CENTER
    }
    /** 그림 — 볼륨 버튼처럼 눌릴 때마다 바뀔 수 있다 */
    var glyph: List<String> = glyph
        set(v) { field = v; invalidate() }
    var listening = false
    /** 옮기는 중 (묶음 전체가 살짝 들려 보인다) */
    var lifted = false
        set(v) { field = v; invalidate() }
    private val dp = PetScale.dp(context)
    private val paint = Paint()

    private var downX = 0f
    private var downY = 0f
    private var moving = false
    private var slipped = false
    private val slop = 24 * dp      // 손가락이 조금 미끄러져도 누르기로 친다
    private val hold = Runnable {
        if (slipped || !movable()) return@Runnable
        moving = true
        isPressed = false
        performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
        onMoveStart?.invoke()
    }

    init {
        contentDescription = "Pixel TMI 버튼"
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(e: MotionEvent): Boolean {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                downX = e.rawX; downY = e.rawY
                moving = false; slipped = false
                isPressed = true
                postDelayed(hold, HOLD_MS)
            }
            MotionEvent.ACTION_MOVE -> {
                if (moving) {
                    onDrag?.invoke(e.rawX - downX, e.rawY - downY)
                } else if (!slipped && hypot(e.rawX - downX, e.rawY - downY) > slop) {
                    // 홀드 전에 밀리면 누르기 취소 (흔들림 방지)
                    slipped = true
                    isPressed = false
                    removeCallbacks(hold)
                }
            }
            MotionEvent.ACTION_UP -> {
                removeCallbacks(hold)
                isPressed = false
                when {
                    moving -> onDragEnd?.invoke()
                    !slipped -> { performClick(); onTap() }
                }
                moving = false
            }
            MotionEvent.ACTION_CANCEL -> {
                removeCallbacks(hold)
                isPressed = false
                if (moving) onDragEnd?.invoke()
                moving = false
            }
        }
        return true
    }

    override fun performClick(): Boolean {
        super.performClick()
        return true
    }

    override fun onDraw(c: Canvas) {
        val d = 5 * dp
        val lift = if (lifted) -d else 0f
        val w = width - d
        val h = height - d
        val inverted = isPressed                       // 듣는 중은 뒤집지 않고 초록 점으로 (늘 검게 보여 헷갈리지 않게)
        val body = if (inverted) PetView.INK else PetView.PAPER
        // 그림자 (옮기는 중엔 더 길게)
        paint.color = PetView.INK
        c.drawRect(2 * d + d, d + d, w - d + d, h + d - 0f, paint)
        c.save()
        c.translate(lift, lift)
        // 몸통 (계단 모서리)
        paint.color = if (lifted) 0xFFFFF4C2.toInt() else body
        c.drawRect(d, d, w - d, h - d, paint)
        paint.color = PetView.INK
        c.drawRect(2 * d, 0f, w - 2 * d, d, paint)
        c.drawRect(2 * d, h - d, w - 2 * d, h, paint)
        c.drawRect(0f, 2 * d, d, h - 2 * d, paint)
        c.drawRect(w - d, 2 * d, w, h - 2 * d, paint)
        c.drawRect(d, d, 2 * d, 2 * d, paint)
        c.drawRect(w - 2 * d, d, w - d, 2 * d, paint)
        c.drawRect(d, h - 2 * d, 2 * d, h - d, paint)
        c.drawRect(w - 2 * d, h - 2 * d, w - d, h - d, paint)
        // 아이콘 (Pixelarticons)
        val rows = glyph
        val px = (w * 0.62f) / rows.maxOf { it.length }
        val ox = (w - rows.maxOf { it.length } * px) / 2
        val oy = (h - rows.size * px) / 2 - (if (caption.isNotEmpty()) h * 0.1f else 0f)
        val inv = inverted && !lifted
        rows.forEachIndexed { r, line ->
            line.forEachIndexed { col, ch ->
                val color = when (ch) {
                    'k' -> if (inv) PetView.PAPER else PetView.INK
                    'w' -> if (inv) PetView.INK else PetView.PAPER
                    else -> return@forEachIndexed
                }
                paint.color = color
                c.drawRect(ox + col * px, oy + r * px, ox + (col + 1) * px, oy + (r + 1) * px, paint)
            }
        }
        if (caption.isNotEmpty()) {
            capPaint.textSize = h * 0.2f
            capPaint.color = if (inverted && !lifted) PetView.PAPER else PetView.INK
            c.drawText(caption, w / 2, h - d * 1.7f, capPaint)
        }
        if (listening) {
            paint.color = 0xFF2ECC71.toInt()
            c.drawRect(w - 4.2f * d, 2.4f * d, w - 2.4f * d, 4.2f * d, paint)
        }
        c.restore()
    }

    override fun setPressed(pressed: Boolean) {
        super.setPressed(pressed)
        invalidate()
    }

    companion object {
        /** 이만큼 꾹 누르고 있어야 옮기기 시작 */
        const val HOLD_MS = 450L
    }
}
