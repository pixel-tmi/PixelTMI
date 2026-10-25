package kr.incar.base.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

object C {
    val bg = Color(0xFF0E1116)
    val panel = Color(0xFF171B22)
    val panelHi = Color(0xFF1F2530)
    val line = Color(0xFF2A313D)
    val text = Color(0xFFF4F6F8)
    val textSub = Color(0xFFC9D1DB) // 연한 회색 대신 충분히 밝은 보조색
    val accent = Color(0xFF00AAD2)
    val ok = Color(0xFF3DDC97)
    val warn = Color(0xFFFFB020)
    val bad = Color(0xFFFF5A5F)
}

@Composable
fun InCarTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            background = C.bg,
            surface = C.panel,
            primary = C.accent,
            onPrimary = Color.White,
            onBackground = C.text,
            onSurface = C.text,
        ),
        content = content,
    )
}
