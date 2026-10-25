package kr.incar.base.pet

import java.util.Calendar

/** 움직이는 방식: 걷는 동물(벽·천장까지) · 바퀴(바닥만) · 나는 것(땅 위로 살짝 떠서) */
enum class Mobility { WALKER, DRIVER, FLYER }

/**
 * 상점 캐릭터 하나.
 * - 기본 4종은 무료. 외관(스킨)은 코인으로, 특별 캐릭터는 코인 또는 유료(₩, 앱 마켓 출시 때 결제 연결).
 * - collab = 콜라보 자리 (캐릭터 에디션처럼). 계약 뒤에 공개 — 지금은 잠금만.
 * - base = 울음소리·세레모니를 고르는 기본 동물/기계 이름 (흰 고양이도 고양이처럼 운다)
 * - event = 할로윈처럼 기간 한정 (그 기간엔 무료)
 */
data class PetChar(
    val id: String,
    val name: String,
    val mobility: Mobility,
    val coins: Int = 0,
    val won: Int? = null,
    val collab: Boolean = false,
    val base: String = id,
    /** 선택 화면 한 줄 소개 (특기) */
    val desc: String = "",
    val event: Boolean = false,
) {
    val free: Boolean get() = (coins == 0 && won == null && !collab) || (event && Catalog.halloween())
}

object Catalog {
    val all = listOf(
        PetChar("cat", "고양이", Mobility.WALKER, desc = "벽 타기 · 냥냥 펀치 · 털실 세레모니"),
        PetChar("dog", "강아지", Mobility.WALKER, desc = "귀 펄럭 질주 · 뼈다귀 세레모니"),
        PetChar("lion", "사자", Mobility.WALKER, desc = "성큼성큼 도약 · 바비큐 세레모니"),
        PetChar("horse", "말", Mobility.WALKER, desc = "택시 미터기 갤럽 · 건초 세레모니"),
        PetChar("cat_white", "흰 고양이", Mobility.WALKER, coins = 300, base = "cat", desc = "눈처럼 하얀 고양이"),
        PetChar("cat_black", "검은 고양이", Mobility.WALKER, coins = 300, base = "cat", desc = "밤길에 강한 검은 고양이"),
        PetChar("ghost", "유령", Mobility.FLYER, coins = 800, base = "ghost", desc = "할로윈 한정 · 둥실둥실 떠다녀요", event = true),
        PetChar("pumpkin", "호박 잭", Mobility.WALKER, coins = 800, base = "pumpkin", desc = "할로윈 한정 · 통통 튀는 호박", event = true),
        PetChar("witch", "마녀 고양이", Mobility.FLYER, coins = 1000, base = "witch", desc = "할로윈 한정 · 빗자루 비행", event = true),
        PetChar("trex", "티라노", Mobility.WALKER, coins = 2500, desc = "와작 물기 · 쿵쿵 포효 · 벽 타기"),
        PetChar("trike", "트리케라톱스", Mobility.WALKER, coins = 2500, desc = "뿔 돌진 · 머리 흔들기 · 풀 뜯기"),
        PetChar("stego", "스테고사우루스", Mobility.WALKER, coins = 2500, desc = "꼬리 가시 휘두르기 · 낮잠"),
        PetChar("brachio", "브라키오사우루스", Mobility.WALKER, coins = 2800, desc = "몸집 2배 · 긴 목 쭉 · 높은 잎 냠냠 · 쿵쿵 밟기"),
        PetChar("ptero", "익룡", Mobility.FLYER, coins = 3000, desc = "급강하 · 바람 타기 · 낚아채기"),
        PetChar("car", "스포츠카", Mobility.DRIVER, coins = 3000, won = 1900, desc = "드리프트 · 니트로 · 상향등 번쩍"),
        PetChar("dragon", "용", Mobility.FLYER, coins = 5000, won = 2900, desc = "불꽃 브레스 · 날갯짓"),
        PetChar("plane", "비행기", Mobility.FLYER, coins = 4000, won = 2500, desc = "공중제비 · 배럴 롤 · 연기 꼬리"),
        PetChar("heli", "헬기", Mobility.FLYER, coins = 4000, won = 2500, desc = "탐조등 · 제자리 회전 · 강아지 하차"),
        PetChar("ufo", "비행접시", Mobility.FLYER, coins = 6000, won = 3300, desc = "광선 · 지그재그 · 고양이 납치"),
        PetChar("collab", "콜라보 에디션", Mobility.WALKER, collab = true, base = "cat", desc = "곧 공개돼요"),
    )

    fun get(id: String): PetChar = all.firstOrNull { it.id == id } ?: all.first()

    /** 할로윈 주간 (10/25 ~ 11/1) — 할로윈 캐릭터·배경 무료 */
    fun halloween(): Boolean {
        val c = Calendar.getInstance()
        val m = c.get(Calendar.MONTH) + 1
        val d = c.get(Calendar.DAY_OF_MONTH)
        return (m == 10 && d >= 25) || (m == 11 && d <= 1)
    }
}

/** 상점 배경 (길 뒤에 옅게 깔리는 그림) — assets/bg/<id>.png (640×130 도트, 가로로 이어 붙임) */
data class Theme(val id: String, val name: String, val coins: Int, val desc: String, val event: Boolean = false) {
    val free: Boolean get() = coins == 0 || (event && Catalog.halloween())
}

object Themes {
    val all = listOf(
        Theme("auto", "사계절 (자동)", 0, "오늘 날짜에 맞춰 봄·여름·가을·겨울로 바뀌어요"),
        Theme("cherry", "벚꽃길", 500, "꽃잎 날리는 강가 벚꽃길"),
        Theme("beach", "여름 바다", 500, "등대 · 돛단배 · 야자수"),
        Theme("joseon", "조선시대", 1200, "한옥 기와 · 궁궐 문 · 소나무"),
        Theme("dino", "공룡시대", 1500, "화산 · 목 긴 공룡 · 익룡"),
        Theme("space", "우주", 2000, "고리 행성 · 로켓 · 우주인"),
        Theme("halloween", "할로윈", 800, "할로윈 한정 · 보름달 · 박쥐 · 유령의 집", event = true),
    )

    fun get(id: String): Theme = all.firstOrNull { it.id == id } ?: all.first()
}
