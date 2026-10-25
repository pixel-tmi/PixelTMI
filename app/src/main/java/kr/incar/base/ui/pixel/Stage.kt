package kr.incar.base.ui.pixel

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.sp
import kr.incar.base.tmi.Hazard
import kotlin.math.pow

enum class Mood { NORMAL, ALERT, HAPPY, TALK }

/**
 * 도로 무대 — 크롬 공룡 게임처럼 옆으로 흐르는 길.
 * 티미는 왼쪽에 서 있고, 앞(오른쪽)의 위험이 거리만큼 떨어진 곳에서 다가온다.
 * 땅·구름은 차가 움직일 때만(내 위치 posM 만큼) 흘러간다.
 */
@Composable
fun Stage(
    posM: Double,
    speedKmh: Float,
    hazards: List<Hazard>,
    focusId: String?,
    level: Int,
    mood: Mood,
    font: FontFamily,
    modifier: Modifier = Modifier,
) {
    val tm = rememberTextMeasurer()
    val loop = rememberInfiniteTransition(label = "stage")
    val tick by loop.animateFloat(0f, 1f, infiniteRepeatable(tween(320, easing = LinearEasing), RepeatMode.Restart), label = "tick")
    val moving = speedKmh > 1f

    Canvas(modifier) {
        val px = size.width / DOTS_W
        val groundY = size.height * 0.80f

        // 먼 언덕 (회색 계단선)
        hills(px, groundY, posM)

        // 구름 (차가 움직일 때만 천천히)
        listOf(0.18f to 0.16f, 0.58f to 0.10f, 0.86f to 0.22f).forEachIndexed { i, (fx, fy) ->
            val drift = ((posM * 0.03 * (i + 1)) % (size.width / px + 40)).toFloat()
            var x = (fx * size.width / px - drift)
            if (x < -26) x += size.width / px + 40
            sprite(Sprites.CLOUD, x * px, fy * size.height, px, tint = P.gray)
        }

        // 땅선 + 흘러가는 자갈
        drawRect(P.ink, Offset(0f, groundY), Size(size.width, px))
        val cols = (size.width / px).toInt()
        for (i in 0 until 26) {
            val base = (i * 37 + (i * i) % 11) % (cols + 20)
            val x = ((base - posM * 0.6) % (cols + 20) + (cols + 20)) % (cols + 20)
            val y = groundY + px * (3 + (i * 7) % 9)
            drawRect(P.mid, Offset(x.toFloat() * px, y), Size(px * (1 + i % 3), px))
        }

        // 길 위의 것들
        val timiX = 10f
        val farX = DOTS_W - 22f
        hazards.filter { it.atM - posM in 0.0..RANGE_M }.sortedByDescending { it.atM }.forEach { h ->
            val d = h.atM - posM
            val t = (d / RANGE_M).pow(0.7).toFloat()
            val x = timiX + 40f + (farX - timiX - 40f) * t  // 티미 몸(약 38도트) 앞부터
            val sp = Sprites.of(h.type)
            val hpx = px * if (h.id == focusId) 1.25f else 1f
            val y = if (Sprites.floats(h.type)) groundY - 46 * px else groundY - sp.size * hpx + px * if (h.type == kr.incar.base.tmi.HazardType.POTHOLE) 3 else 0
            sprite(sp, x * px, y, hpx)
            val label = if (d >= 1000) "%.1fkm".format(d / 1000) else "${d.toInt()}m"
            text(tm, label, Offset(x * px, y - 9 * px), font, if (h.id == focusId) 30 else 22, if (h.id == focusId) P.red else P.ink)
        }

        // 티미 (움직이면 바퀴가 구르고 살짝 통통)
        val frameB = moving && tick > 0.5f
        val bob = if (moving && tick in 0.25f..0.75f) -px else 0f
        val tPx = px * 1.6f
        drawTimi(level, mood, timiX * px, groundY - 18 * tPx + bob, tPx, frameB, blink = tick < 0.06f, talkOpen = tick > 0.5f)

        // 속도
        text(tm, "${speedKmh.toInt()} km/h", Offset(px * 3, groundY + px * 8), font, 26, P.ink)
    }
}

/** 티미 그리기 — 레벨이 오르면 안테나 → 레이더 → 스카프 → 왕관 (다마고치처럼 자란다) */
fun DrawScope.drawTimi(level: Int, mood: Mood, tx: Float, ty: Float, tPx: Float, frameB: Boolean = false, blink: Boolean = false, talkOpen: Boolean = false) {
    val body = if (frameB) Sprites.TIMI_B else Sprites.TIMI_A
    when {
        level >= 5 -> sprite(Sprites.CROWN, tx + 10 * tPx, ty - 4 * tPx, tPx)
        level >= 3 -> sprite(Sprites.RADAR, tx + 9 * tPx, ty - 5 * tPx, tPx)
        level >= 2 -> sprite(Sprites.ANTENNA, tx + 10 * tPx, ty - 5 * tPx, tPx)
    }
    sprite(body, tx, ty, tPx)
    if (level >= 4) sprite(Sprites.SCARF, tx - 2 * tPx, ty + 10 * tPx, tPx)
    val eyes = when (mood) {
        Mood.ALERT -> Sprites.EYES_ALERT
        Mood.HAPPY -> Sprites.EYES_HAPPY
        else -> if (blink) Sprites.EYES_BLINK else Sprites.EYES_NORMAL
    }
    sprite(eyes, tx + 13 * tPx, ty + 6 * tPx, tPx)
    val mouth = when {
        mood == Mood.ALERT -> Sprites.MOUTH_O
        mood == Mood.TALK && talkOpen -> Sprites.MOUTH_TALK
        else -> Sprites.MOUTH_SMILE
    }
    sprite(mouth, tx + 9 * tPx, ty + 9 * tPx, tPx)
}

private fun DrawScope.hills(px: Float, groundY: Float, posM: Double) {
    val cols = (size.width / px).toInt()
    val shift = (posM * 0.08).toInt()
    var prevH = -1
    for (c in 0..cols) {
        val xx = c + shift
        val h = (6 + 5 * kotlin.math.sin(xx / 13.0) + 3 * kotlin.math.sin(xx / 5.3)).toInt().coerceAtLeast(1)
        val y = groundY - h * px
        drawRect(P.gray, Offset(c * px, y), Size(px, px))
        if (prevH >= 0 && prevH != h) {
            val top = minOf(prevH, h)
            val bot = maxOf(prevH, h)
            for (k in top until bot) drawRect(P.gray, Offset(c * px, groundY - k * px), Size(px, px))
        }
        prevH = h
    }
}

private fun DrawScope.text(tm: TextMeasurer, s: String, at: Offset, font: FontFamily, sizeSp: Int, color: androidx.compose.ui.graphics.Color) {
    drawText(tm, s, at, style = TextStyle(color = color, fontSize = sizeSp.sp, fontFamily = font))
}

const val DOTS_W = 160f
private const val RANGE_M = 2000.0
