package kr.incar.base.ui.pixel

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kr.incar.base.tmi.Hazard
import kotlin.math.min

/**
 * 도트 테두리: 모서리를 한 칸씩 깎은 계단 모양 + 오른쪽 아래 검정 그림자(레트로 버튼 느낌).
 */
fun Modifier.pixelBox(fill: Color = P.paper, line: Color = P.ink, dot: Dp = 4.dp, shadow: Boolean = true): Modifier = drawBehind {
    val d = dot.toPx()
    val sh = if (shadow) d else 0f
    val w = size.width - sh
    val h = size.height - sh
    if (shadow) steppedRect(Offset(sh, sh), w, h, d, P.ink, P.ink)
    steppedRect(Offset.Zero, w, h, d, fill, line)
}

private fun DrawScope.steppedRect(o: Offset, w: Float, h: Float, d: Float, fill: Color, line: Color) {
    // 채움
    drawRect(fill, o + Offset(d, d), Size(w - 2 * d, h - 2 * d))
    // 테두리 (모서리는 비움)
    drawRect(line, o + Offset(2 * d, 0f), Size(w - 4 * d, d))
    drawRect(line, o + Offset(2 * d, h - d), Size(w - 4 * d, d))
    drawRect(line, o + Offset(0f, 2 * d), Size(d, h - 4 * d))
    drawRect(line, o + Offset(w - d, 2 * d), Size(d, h - 4 * d))
    // 모서리 계단
    drawRect(line, o + Offset(d, d), Size(d, d))
    drawRect(line, o + Offset(w - 2 * d, d), Size(d, d))
    drawRect(line, o + Offset(d, h - 2 * d), Size(d, d))
    drawRect(line, o + Offset(w - 2 * d, h - 2 * d), Size(d, d))
}

/**
 * 말풍선 — 티미가 말할 때 쏙 나왔다가 다 말하면 쏙 들어간다.
 * danger면 검정 바탕 흰 글씨로 뒤집어서 긴장감.
 */
@Composable
fun SpeechBubble(
    visible: Boolean,
    tag: String,
    text: String,
    danger: Boolean,
    font: FontFamily,
    modifier: Modifier = Modifier,
) {
    AnimatedVisibility(
        visible = visible,
        modifier = modifier,
        enter = scaleIn(spring(dampingRatio = 0.55f, stiffness = Spring.StiffnessMediumLow), initialScale = 0.3f, transformOrigin = TransformOrigin(0.12f, 1f)) + fadeIn(),
        exit = scaleOut(tween(160), targetScale = 0.4f, transformOrigin = TransformOrigin(0.12f, 1f)) + fadeOut(tween(160)),
    ) {
        val fill = if (danger) P.ink else P.paper
        val ink = if (danger) P.paper else P.ink
        Column {
            Box(Modifier.pixelBox(fill = fill, line = P.ink, dot = 5.dp).padding(start = 28.dp, end = 34.dp, top = 20.dp, bottom = 26.dp)) {
                Column {
                    Box(Modifier.pixelBox(fill = if (danger) P.red else P.ink, line = if (danger) P.paper else P.ink, dot = 3.dp, shadow = false).padding(horizontal = 14.dp, vertical = 6.dp)) {
                        Text(tag, color = P.paper, fontSize = 18.sp, fontFamily = font)
                    }
                    Spacer(Modifier.size(10.dp))
                    Text(text, color = ink, fontSize = 30.sp, lineHeight = 40.sp, fontFamily = font)
                }
            }
            // 꼬리 (티미 머리 쪽, 계단 모양)
            Canvas(Modifier.padding(start = 60.dp).size(40.dp, 30.dp)) {
                val d = 5.dp.toPx()
                for (i in 0 until 5) {
                    val w = (5 - i) * d
                    drawRect(P.ink, Offset(i * d * 0.6f, i * d), Size(w + d, d))
                    if (w > d) drawRect(fill, Offset(i * d * 0.6f + d, i * d - if (i == 0) d else 0f), Size(w - d, if (i == 0) 2 * d else d))
                }
            }
        }
    }
}

/**
 * 위험 컷인 (약 1초) — 사선 집중선 + 티미 클로즈업 + 눈 번뜩.
 * 주행 중 주의분산을 줄이려고 한 번만, 짧게.
 */
@Composable
fun DangerCutIn(hazard: Hazard?, font: FontFamily, onDone: () -> Unit) {
    if (hazard == null) return
    val t = remember(hazard.id) { Animatable(0f) }
    LaunchedEffect(hazard.id) {
        t.snapTo(0f)
        t.animateTo(1f, tween(1100, easing = LinearEasing))
        onDone()
    }
    val p = t.value
    Box(Modifier.fillMaxSize()) {
        Canvas(Modifier.fillMaxSize()) {
            val alpha = when {
                p < 0.08f -> p / 0.08f
                p > 0.85f -> (1f - p) / 0.15f
                else -> 1f
            }.coerceIn(0f, 1f)
            // 번쩍 (시작 순간 흰 화면)
            if (p < 0.1f) drawRect(P.paper.copy(alpha = alpha), size = size)
            // 사선 띠
            val bandH = size.height * 0.62f
            val cy = size.height * 0.45f
            drawRect(P.paper.copy(alpha = 0.92f * alpha), Offset(0f, cy - bandH / 2), Size(size.width, bandH))
            // 집중선 (사선, 빠르게 흐름)
            val n = 34
            for (i in 0 until n) {
                val seed = (i * 73 % 97) / 97f
                val y = cy - bandH / 2 + seed * bandH
                val len = size.width * (0.18f + 0.3f * ((i * 31 % 17) / 17f))
                val x = ((seed * 1.7f + p * 3.2f) % 1.4f - 0.2f) * size.width
                val slant = len * 0.22f
                drawLine(P.ink.copy(alpha = alpha), Offset(x, y + slant), Offset(x + len, y - slant), strokeWidth = if (i % 3 == 0) 7f else 3f)
            }
            // 띠 위아래 굵은 선
            drawRect(P.ink.copy(alpha = alpha), Offset(0f, cy - bandH / 2), Size(size.width, 10f))
            drawRect(P.ink.copy(alpha = alpha), Offset(0f, cy + bandH / 2 - 10f), Size(size.width, 10f))

            // 티미 클로즈업 — 왼쪽에서 확 들어와 멈춘다
            val fpx = min(size.width / 52f, bandH / 22f)
            val faceW = 32 * fpx
            val slide = (p / 0.18f).coerceIn(0f, 1f)
            val ease = 1f - (1f - slide) * (1f - slide)
            val fx = -faceW + (size.width * 0.08f + faceW) * ease
            val fy = cy - 8 * fpx
            if (alpha > 0.05f) sprite(Sprites.FACE, fx, fy, fpx)
            // 눈 번뜩 (찌릭)
            if (p in 0.32f..0.62f) {
                val g = 1f - kotlin.math.abs((p - 0.47f) / 0.15f)
                Sprites.FACE_GLINTS.forEach { (gx, gy) ->
                    glint(Offset(fx + gx * fpx, fy + gy * fpx), fpx * 5f * g)
                }
            }
        }
        // 오른쪽 경고 글자
        if (p > 0.22f && p < 0.9f) {
            Box(Modifier.align(Alignment.CenterEnd).padding(end = 28.dp)) {
                Box(Modifier.pixelBox(fill = P.red, line = P.ink, dot = 6.dp).padding(horizontal = 26.dp, vertical = 16.dp)) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("위험!!", color = P.paper, fontSize = 40.sp, fontFamily = font)
                        Text(hazard.type.label, color = P.paper, fontSize = 30.sp, fontFamily = font)
                    }
                }
            }
        }
    }
}

private fun DrawScope.glint(c: Offset, r: Float) {
    if (r <= 0f) return
    val t = r / 5f
    drawRect(P.paper, Offset(c.x - t, c.y - r), Size(2 * t, 2 * r))
    drawRect(P.paper, Offset(c.x - r, c.y - t), Size(2 * r, 2 * t))
    drawRect(P.yellow, Offset(c.x - t, c.y - t), Size(2 * t, 2 * t))
}

/** 큰 도트 버튼 */
@Composable
fun PixelButton(
    label: String,
    font: FontFamily,
    modifier: Modifier = Modifier,
    icon: List<String>? = null,
    fill: Color = P.paper,
    textColor: Color = P.ink,
    sizeSp: Int = 34,
    onClick: () -> Unit,
) {
    Box(modifier.pixelBox(fill = fill, dot = 5.dp).clickable(onClick = onClick), contentAlignment = Alignment.Center) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(end = 5.dp, bottom = 5.dp)) {
            if (icon != null) {
                Canvas(Modifier.size(52.dp)) {
                    val w = spriteWidth(icon)
                    val dotPx = size.width / maxOf(w, icon.size)
                    sprite(icon, (size.width - w * dotPx) / 2, (size.height - icon.size * dotPx) / 2, dotPx)
                }
                Spacer(Modifier.width(12.dp))
            }
            Text(label, color = textColor, fontSize = sizeSp.sp, fontFamily = font)
        }
    }
}

/** 코인 아이콘 */
@Composable
fun CoinIcon(sizeDp: Dp = 30.dp) {
    Canvas(Modifier.size(sizeDp)) { sprite(Sprites.COIN, 0f, 0f, size.width / 8f) }
}
