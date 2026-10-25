package kr.incar.base.ui.pixel

import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import android.content.res.AssetManager

/**
 * 도트 팔레트 — 크롬 공룡 게임처럼 흰 바탕 + 검정 도트 선.
 * 강조색은 8비트 게임기 64색 팔레트에서 몇 개만 골라 아껴 쓴다.
 */
object P {
    val paper = Color(0xFFF8F8F8)   // 바탕 흰색
    val ink = Color(0xFF1E1E1E)     // 도트 선
    val gray = Color(0xFFBCBCBC)    // 구름·땅 점
    val mid = Color(0xFF7C7C7C)
    val red = Color(0xFFF83800)     // 위험
    val yellow = Color(0xFFF8B800)  // 코인
    val green = Color(0xFF00B800)   // 확인
    val pink = Color(0xFFF8A4C0)    // 볼터치
    val blue = Color(0xFF3CBCFC)    // 비
    val brown = Color(0xFFAC7C00)   // 상자
}

/** 갈무리 픽셀 글꼴 (SIL OFL 1.1, assets/licenses/Galmuri_OFL.txt) */
fun galmuri(assets: AssetManager): FontFamily = FontFamily(Font("fonts/galmuri11_bold.ttf", assets, FontWeight.Normal), Font("fonts/galmuri11_bold.ttf", assets, FontWeight.Bold))

/**
 * 글자 그림(스프라이트)을 도트로 그린다.
 * k=검정 w=흰색 g=회색 m=진회색 r=빨강 y=노랑 p=분홍 b=파랑 n=갈색 .=투명
 */
fun DrawScope.sprite(rows: List<String>, x: Float, y: Float, px: Float, flipX: Boolean = false, tint: Color? = null) {
    val w = rows.maxOf { it.length }
    rows.forEachIndexed { r, line ->
        line.forEachIndexed { c, ch ->
            val color = when (ch) {
                'k' -> P.ink
                'w' -> P.paper
                'g' -> P.gray
                'm' -> P.mid
                'r' -> P.red
                'y' -> P.yellow
                'p' -> P.pink
                'b' -> P.blue
                'n' -> P.brown
                else -> null
            } ?: return@forEachIndexed
            val cx = if (flipX) w - 1 - c else c
            drawRect(tint?.takeIf { ch == 'k' } ?: color, Offset(x + cx * px, y + r * px), Size(px + 0.5f, px + 0.5f))
        }
    }
}

fun spriteWidth(rows: List<String>) = rows.maxOf { it.length }
