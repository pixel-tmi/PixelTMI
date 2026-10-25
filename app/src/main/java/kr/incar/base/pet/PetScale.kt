package kr.incar.base.pet

import android.content.Context
import kr.incar.base.car.CarSpeedSource

/**
 * 펫 크기 기준. Pleos 화면(가로 2560dp)에 맞춰 그렸으니,
 * 갤럭시 탭처럼 가로 dp가 작은 화면에선 그만큼 줄여서(최소 0.6배) 고양이·버튼·말풍선이 너무 커 보이지 않게 한다.
 * 탭의 'Pleos 전용 앱'(stage)에선 Pleos 화면 그림(2560x1440)을 깐 배율과 1:1로 맞춘다.
 */
object PetScale {
    /** 탭 'Pleos 전용 앱' 화면 중인가 */
    @Volatile var stage = false
    /** stage일 때 Pleos 그림을 깐 배율 (그림 1px → 화면 px) */
    @Volatile var stageScale = 1f
    /** stage일 때 땅을 올릴 높이(px) = 그림 속 Pleos 아래 바 높이 */
    @Volatile var stageGroundLift = 0f

    /** 차량(Pleos·안드로이드 오토모티브)이거나 Pleos 전용 앱 — 왼쪽 차량 판 경계 같은 Pleos 배치를 쓸지 */
    val isPleos: Boolean get() = CarSpeedSource.available || stage

    fun dp(context: Context): Float {
        if (stage) return stageScale
        val dm = context.resources.displayMetrics
        val widePx = maxOf(dm.widthPixels, dm.heightPixels)
        val wideDp = widePx / dm.density
        return dm.density * (wideDp / 2560f).coerceIn(0.6f, 1f)
    }
}
