package kr.incar.base.ui.pixel

import kr.incar.base.tmi.HazardType

/**
 * 도트 그림 모음. 한 글자 = 한 도트.
 * k=검정 w=흰색 g=회색 m=진회색 r=빨강 y=노랑 p=분홍 b=파랑 n=갈색 .=투명
 * 미리보기: 베이스앱\도구\도트_미리보기.py
 */
object Sprites {

    // ── 티미 (다마고치 같은 꼬마 자동차, 오른쪽을 본다) ── 24 x 18
    private val timiTop = listOf(
        "..........kkkk..........",
        ".......kkkwwwwkkk.......",
        ".....kkwwwwwwwwwwkk.....",
        "....kwwwwwwwwwwwwwwk....",
        "...kwwwwwwwwwwwwwwwwk...",
        "..kwwwwwwwwwwwwwwwwwwk..",
        "..kwwwwwwwwwwwwwwwwwwk..",
        ".kwwwwwwwwwwwwwwwwwwwwk.",
        ".kwwwwwwwwwwwwwwwwwwwwk.",
        ".kwwwwwwwwwwwwwwwwwwwyk.",
        ".kwwwwwwwwwwwwwwwwwwwyk.",
        ".kwwwwwwwwwwwwwwwwwwwwk.",
        "..kggggggggggggggggggk..",
        "...kkkkkkkkkkkkkkkkkk...",
        "....kkk..........kkk....",
        "...kwwwk........kwwwk...",
    )
    val TIMI_A = timiTop + listOf(
        "...kwkwk........kwkwk...",
        "....kkk..........kkk....",
    )
    val TIMI_B = timiTop + listOf(
        "...kkwkk........kkwkk...",
        "....kkk..........kkk....",
    )

    /** 얼굴 (몸 위에 겹쳐 그림). 위치: col 12, row 6 */
    val EYES_NORMAL = listOf(
        "wk...wk",
        "kk...kk",
        "kk...kk",
    )
    val EYES_ALERT = listOf(
        "kkk.kkk",
        "kwk.kwk",
        "kkk.kkk",
    )
    val EYES_HAPPY = listOf(
        ".k...k.",
        "k.k.k.k",
        ".......",
    )
    val EYES_BLINK = listOf(
        ".......",
        "kk...kk",
        ".......",
    )
    /** 볼·입. 위치: col 10, row 10 */
    val MOUTH_SMILE = listOf(
        "pp..k..k..pp",
        ".....kk.....",
    )
    val MOUTH_TALK = listOf(
        "pp..kkkk..pp",
        "....kwwk....",
        ".....kk.....",
    )
    val MOUTH_O = listOf(
        "pp...kk...pp",
        "....kwwk....",
        ".....kk.....",
    )

    // ── 레벨이 오르면 자라는 장식 (몸 기준 위치는 Stage에서) ──
    val ANTENNA = listOf(
        ".kk.",
        "kyyk",
        ".kk.",
        "..k.",
        "..k.",
    )
    val RADAR = listOf(
        "k.....k",
        ".k...k.",
        "..kkk..",
        "...k...",
        "...k...",
    )
    val SCARF = listOf(
        "rr....",
        "rrrr..",
        ".rrrr.",
    )
    val CROWN = listOf(
        "k.k.k",
        "kykyk",
        "kyyyk",
        "kkkkk",
    )

    // ── 위험 컷인용 클로즈업 얼굴 (정면, 눈썹 찡그림) ── 32 x 16
    val FACE = listOf(
        "........kkkkkkkkkkkkkkkk........",
        ".....kkkwwwwwwwwwwwwwwwwkkk.....",
        "...kkwwwwwwwwwwwwwwwwwwwwwwkk...",
        "..kwwkkkkwwwwwwwwwwwwwwkkkkwwk..",
        ".kwwwwwkkkkwwwwwwwwwwkkkkwwwwwk.",
        ".kwwwwkkkkkkwwwwwwwwkkkkkkwwwwk.",
        "kwwwwkkwwkkkwwwwwwwwkkkwwkkwwwwk",
        "kwwwwkkwwkkkwwwwwwwwkkkwwkkwwwwk",
        "kwwwwkkkkkkkwwwwwwwwkkkkkkkwwwwk",
        "kwwwwwkkkkkwwwwwwwwwwkkkkkwwwwwk",
        "kwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwk",
        "kwwppwwwwwwwwkkkkkkwwwwwwwppwwwk",
        ".kwwwwwwwwwwwkwkwkwkwwwwwwwwwwk.",
        "..kwwwwwwwwwwwkkkkkkwwwwwwwwwk..",
        "...kkwwwwwwwwwwwwwwwwwwwwwwkk...",
        ".....kkkkkkkkkkkkkkkkkkkkkk.....",
    )
    /** 눈 반짝임 위치 (FACE 기준 도트 좌표) */
    val FACE_GLINTS = listOf(7.5f to 6.5f, 23.5f to 6.5f)

    // ── 길 위의 것들 (바닥에 붙여 그림) ── 폭 16
    val POTHOLE = listOf(
        "..kk........kk..",
        ".kmmkkkkkkkkmmk.",
        "kmmmmmmmmmmmmmmk",
        ".kkmmmmmmmmmmkk.",
        "...kkkkkkkkkk...",
    )
    val DEBRIS = listOf(
        "...kkkkkkkkk....",
        "..knnnnyynnnk...",
        "..knnnnyynnnk...",
        "..kkkkkkkkkkk...",
        "..knnnnyynnnk...",
        "..knnnnyynnnk...",
        "..kkkkkkkkkkk...",
        "k.k..........k.k",
    )
    val ACCIDENT = listOf(
        ".......kk.......",
        "......kwwk......",
        "......kwwk......",
        ".....kwrrwk.....",
        ".....kwrrwk.....",
        "....kwwrrwwk....",
        "....kwwrrwwk....",
        "...kwwwwwwwwk...",
        "...kwwwrrwwwk...",
        "..kwwwwrrwwwwk..",
        "..kwwwwwwwwwwk..",
        ".kkkkkkkkkkkkkk.",
    )
    val CONE = listOf(
        ".......kk.......",
        "......krrk......",
        "......kwwk......",
        ".....krrrrk.....",
        ".....kwwwwk.....",
        "....krrrrrrk....",
        "....kwwwwwwk....",
        "...krrrrrrrrk...",
        "...kwwwwwwwwk...",
        "..kkkkkkkkkkkk..",
        ".kmmmmmmmmmmmmk.",
        ".kkkkkkkkkkkkkk.",
    )
    val CAMERA = listOf(
        "..kkkkkkkkkk....",
        ".kwwwwwwwwwwk...",
        ".kwwkkkkwwwwkkk.",
        ".kwkwwwwkwwwkwk.",
        ".kwkwkkwkwrwkwk.",
        ".kwkwwwwkwwwkkk.",
        ".kwwkkkkwwwwk...",
        "..kkkkkkkkkk....",
        "......kk........",
        "......kk........",
        "......kk........",
        "......kk........",
        "....kkkkkk......",
    )
    val BUMP = listOf(
        ".....kkkkkk.....",
        "...kkykykykkk...",
        "..kykykykykykk..",
        ".kkkkkkkkkkkkkk.",
    )
    val SCHOOL = listOf(
        "....kkkkkkkk....",
        "...kyyyyyyyyk...",
        "..kyyyykkyyyyk..",
        "..kyyyykkyyyyk..",
        "..kyyykkkkyyyk..",
        "..kyyyykkyyyyk..",
        "..kyyykyykyyyk..",
        "...kyyyyyyyyk...",
        "....kkkkkkkk....",
        ".......kk.......",
        ".......kk.......",
        ".......kk.......",
        ".....kkkkkk.....",
    )
    val SKID = listOf(
        "kkkkkkk..kkkkkk.",
        "................",
        ".kkkkk....kkkkkk",
    )
    val RAIN = listOf(
        ".....kkkkk......",
        "...kkmmmmmkk....",
        ".kkmmmmmmmmmkk..",
        "kmmmmmmmmmmmmmk.",
        "kkkkkkkkkkkkkkk.",
        "................",
        "..b...b...b.....",
        ".b...b...b......",
        "................",
        "...b...b...b....",
    )
    val ICE = listOf(
        ".......b........",
        "...b...b...b....",
        "....b..b..b.....",
        ".....b.b.b......",
        "..bbbbbbbbbbbbb.",
        ".....b.b.b......",
        "....b..b..b.....",
        "...b...b...b....",
        ".......b........",
    )

    // ── 배경 ──
    val CLOUD = listOf(
        "..........kkkkk.........",
        "........kkwwwwwkk.......",
        "...kkkkkwwwwwwwwwk......",
        "..kwwwwwwwwwwwwwwwkkk...",
        ".kwwwwwwwwwwwwwwwwwwwk..",
        "kkkkkkkkkkkkkkkkkkkkkkk.",
    )
    val COIN = listOf(
        "..kkkk..",
        ".kyyyyk.",
        "kyykyyyk",
        "kyykyyyk",
        "kyykyyyk",
        "kyykyyyk",
        ".kyyyyk.",
        "..kkkk..",
    )
    val MIC = listOf(
        "....kkkk....",
        "...kwwwwk...",
        "...kwwwwk...",
        "...kwwwwk...",
        "...kwwwwk...",
        ".k.kwwwwk.k.",
        ".k.kwwwwk.k.",
        ".k..kkkk..k.",
        "..k......k..",
        "...kkkkkk...",
        ".....kk.....",
        ".....kk.....",
        "...kkkkkk...",
    )


    // ══════════ 픽토그램 세트 ══════════

    /** 자동차 옆모습 실루엣 (오른쪽을 본다): 검정 차체 · 흰 창문 · 노란 전조등 · 빨간 미등 · 문 틈 */ // 30 x 10
    val CAR_BODY = listOf(
        "..........kkkkkkkkkk..........",
        ".........kwwwwwkwwwwwk........",
        "........kwwwwwwkwwwwwwk.......",
        ".......kwwwwwwwkwwwwwwwk......",
        "...kkkkkkkkkkkkkkkkkkkkkkkk...",
        ".kkkkkkkkkkkkkwkkkkkkkkkkkkkk.",
        "kkkkkkkkkkkkkkwkkkkkkkkkkkkyyk",
        "rkkkkkkkkkkkkkwkkkkkkkkkkkkkkk",
        "kkkk......kkkkkkkkkk......kkkk",
        ".kkk......kkkkkkkkkk......kkk.",
    )
    /** 바퀴 (두 장을 번갈아 그려 굴러가게) */ // 6 x 6
    val WHEEL_A = listOf(
        ".kkkk.",
        "kkkkkk",
        "kkwwkk",
        "kkwwkk",
        "kkkkkk",
        ".kkkk.",
    )
    val WHEEL_B = listOf(
        ".kkkk.",
        "kwkkwk",
        "kkkkkk",
        "kkkkkk",
        "kwkkwk",
        ".kkkk.",
    )

    /** 삼각 경고표지 + 기둥 (빨간 테두리, 흰 바탕). symbol = (열, 행) 검정 도트 */ // 16 x 17
    private val TRIANGLE = listOf(
        ".......rr.......",
        "......rwwr......",
        "......rwwr......",
        ".....rwwwwr.....",
        ".....rwwwwr.....",
        "....rwwwwwwr....",
        "....rwwwwwwr....",
        "...rwwwwwwwwr...",
        "...rwwwwwwwwr...",
        "..rwwwwwwwwwwr..",
        "..rwwwwwwwwwwr..",
        ".rwwwwwwwwwwwwr.",
        ".rrrrrrrrrrrrrr.",
        ".......kk.......",
        ".......kk.......",
        ".......kk.......",
        "......kkkk......",
    )

    private fun sign(vararg marks: Pair<Int, Int>): List<String> {
        val g = TRIANGLE.map { it.toCharArray() }
        marks.forEach { (c, r) -> g[r][c] = 'k' }
        return g.map { String(it) }
    }

    private fun span(r: Int, from: Int, to: Int) = (from..to).map { it to r }.toTypedArray()

    /** 사고·급정거: 느낌표 */
    val SIGN_ALERT = sign(*span(4, 7, 8), *span(5, 7, 8), *span(6, 7, 8), *span(7, 7, 8), *span(8, 7, 8), *span(10, 7, 8))
    /** 과속방지턱: 노면 위 둥근 턱 */
    val SIGN_BUMP = sign(*span(8, 6, 9), *span(9, 5, 10), *span(10, 4, 11), *span(11, 2, 13))
    /** 노면 파손(포트홀): 움푹 꺼진 길 + 금 */
    val SIGN_POTHOLE = sign(7 to 6, 8 to 7, 7 to 8, *span(10, 2, 5), *span(10, 10, 13), *span(11, 5, 10), 6 to 10, 9 to 10)
    /** 낙하물: 떨어진 상자 */
    val SIGN_DEBRIS = sign(*span(5, 6, 9), 6 to 6, 9 to 6, *span(7, 6, 9), *span(10, 4, 5), *span(10, 7, 8), *span(10, 10, 11), *span(11, 2, 13))
    /** 어린이 보호구역: 손잡은 두 아이 */
    val SIGN_SCHOOL = sign(6 to 5, 9 to 5, *span(6, 5, 7), *span(6, 8, 10), 6 to 7, 9 to 7, *span(8, 6, 9), 5 to 9, 7 to 9, 8 to 9, 10 to 9, 5 to 10, 7 to 10, 8 to 10, 10 to 10)
    /** 결빙: 눈송이 */
    val SIGN_ICE = sign(7 to 5, 8 to 5, 5 to 7, 10 to 7, *span(7, 7, 8), *span(8, 6, 9), *span(9, 4, 11), *span(10, 6, 9), 5 to 11, 10 to 11, 7 to 11, 8 to 11)

    /** 목적지: 체크무늬 깃발 */ // 10 x 17
    val FLAG_CHECK = listOf(
        "kkkkkkkkkk",
        "kwwkkwwkkk",
        "kwwkkwwkkk",
        "kkkwwkkwwk",
        "kkkwwkkwwk",
        "kwwkkwwkkk",
        "kkkkkkkkkk",
        "kk........",
        "kk........",
        "kk........",
        "kk........",
        "kk........",
        "kk........",
        "kk........",
        "kk........",
        "kk........",
        "kkkk......",
    )

    /** 픽토그램 고르기 */
    fun pictogram(t: HazardType): List<String> = when (t) {
        HazardType.POTHOLE -> SIGN_POTHOLE
        HazardType.DEBRIS -> SIGN_DEBRIS
        HazardType.ACCIDENT -> SIGN_ALERT
        HazardType.HARD_BRAKE -> SIGN_ALERT
        HazardType.CONSTRUCTION -> CONE
        HazardType.ICE -> SIGN_ICE
        HazardType.RAIN -> RAIN
        HazardType.CAMERA -> CAMERA
        HazardType.BUMP -> SIGN_BUMP
        HazardType.SCHOOL -> SIGN_SCHOOL
        else -> SIGN_ALERT
    }

    fun of(t: HazardType): List<String> = when (t) {
        HazardType.POTHOLE -> POTHOLE
        HazardType.DEBRIS -> DEBRIS
        HazardType.ACCIDENT -> ACCIDENT
        HazardType.CONSTRUCTION -> CONE
        HazardType.ICE -> ICE
        HazardType.HARD_BRAKE -> SKID
        HazardType.RAIN -> RAIN
        HazardType.CAMERA -> CAMERA
        HazardType.BUMP -> BUMP
        HazardType.SCHOOL -> SCHOOL
        else -> ACCIDENT
    }

    /** 하늘에 떠 있는 것(비구름) vs 땅에 붙는 것 */
    fun floats(t: HazardType) = t in HazardType.AREA || t == HazardType.ICE
}
