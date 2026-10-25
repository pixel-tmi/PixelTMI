package kr.incar.base.tmi

import androidx.compose.ui.graphics.Color
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 위험 종류. clip = 옛 안내 음성 이름(지금은 쓰지 않음, 기록용).
 * fixed = 늘 그 자리에 있는 것(방지턱·카메라·보호구역) — 컷인 없이 가볍게 알리고 "아직 있나요?"도 묻지 않는다.
 * ttlMin = 수명(분). 마지막 제보·확인 뒤로 이만큼 새 제보가 없으면 길에서 지운다 (null = 지우지 않음).
 */
enum class HazardType(val label: String, val clip: String, val color: Color, val advice: String, val fixed: Boolean = false, val ttlMin: Int? = null) {
    POTHOLE("포트홀", "t_pothole", Color(0xFFFF8A3D), "a_slow", ttlMin = 7 * 24 * 60),
    DEBRIS("낙하물", "t_debris", Color(0xFFFF5A5F), "a_lane", ttlMin = 60),
    ACCIDENT("사고", "t_accident", Color(0xFFFF3B3B), "a_lane", ttlMin = 60),
    CONSTRUCTION("공사", "t_construction", Color(0xFFFFB020), "a_lane", ttlMin = 24 * 60),
    ICE("결빙", "t_ice", Color(0xFF7FD8FF), "a_slow", ttlMin = 120),
    HARD_BRAKE("급정거 다발", "t_brake", Color(0xFFFF6FB0), "a_slow", ttlMin = 15),
    RAIN("국지성 비", "t_rain", Color(0xFF5AA9FF), "a_slow", ttlMin = 30),
    CAMERA("단속카메라", "t_camera", Color(0xFF9B8CFF), "a_slow", fixed = true),
    BUMP("과속방지턱", "t_bump", Color(0xFFFFD23F), "a_slow", fixed = true),
    SCHOOL("어린이보호구역", "t_school", Color(0xFFFFB020), "a_slow", fixed = true),

    // ── 운전자가 말로 올리는 도로 상황 ──
    EMERGENCY("긴급차량", "t_emergency", Color(0xFFFF3B3B), "a_yield", ttlMin = 10),
    FIRE("차량 화재", "t_fire", Color(0xFFFF6A00), "a_lane", ttlMin = 60),
    BREAKDOWN("고장차", "t_breakdown", Color(0xFFFFB020), "a_lane", ttlMin = 30),
    ANIMAL("동물 출몰", "t_animal", Color(0xFFB07A3C), "a_slow", ttlMin = 30),
    PEDESTRIAN("보행자", "t_pedestrian", Color(0xFF3CB371), "a_slow", ttlMin = 10),
    FLOOD("침수", "t_flood", Color(0xFF3C8DFF), "a_slow", ttlMin = 3 * 60),
    FOG("짙은 안개", "t_fog", Color(0xFF9AA5B1), "a_slow", ttlMin = 60),
    JAM("정체", "t_jam", Color(0xFFFF8A3D), "a_slow", ttlMin = 20),
    SIGNAL("신호등 고장", "t_signal", Color(0xFFFFD23F), "a_slow", ttlMin = 2 * 60),
    ROCKFALL("낙석·산사태", "t_rockfall", Color(0xFF8D6E63), "a_lane", ttlMin = 6 * 60),
    WRONG_WAY("역주행", "t_wrongway", Color(0xFFFF1744), "a_slow", ttlMin = 10),
    ROAD_CLOSED("도로 통제", "t_closed", Color(0xFFFF5A5F), "a_lane", ttlMin = 3 * 60),

    // ── 운전자 날씨 제보 (기상청 기본 예보와 별도로, 지금 이 자리) ──
    HAIL("우박", "t_hail", Color(0xFFB3E5FC), "a_slow", ttlMin = 30),
    SNOW("폭설", "t_snow", Color(0xFFE3F2FD), "a_slow", ttlMin = 2 * 60),
    WIND("강풍", "t_wind", Color(0xFF80CBC4), "a_slow", ttlMin = 60),

    // ── 재난 ──
    TSUNAMI("해일", "t_tsunami", Color(0xFF1565C0), "a_slow", ttlMin = 6 * 60),
    WILDFIRE("산불", "t_wildfire", Color(0xFFE64A19), "a_slow", ttlMin = 12 * 60),
    AVALANCHE("눈사태", "t_avalanche", Color(0xFFB0BEC5), "a_slow", ttlMin = 12 * 60),
    ;

    companion object {
        /** 평소엔 숨기고 달리면서 1km 안에서만 보이는 것 (단속카메라·어린이보호구역) */
        val DRIVING_ONLY = setOf(CAMERA, SCHOOL)
        /** 하늘·주변 전체에 걸친 것 (길 위 한 점이 아니라 구간) — 높이 띄워 그린다 */
        val AREA = setOf(RAIN, FOG, HAIL, SNOW, WIND)
        /** 하늘에 띄워 그리는 것 (비구름만) — 나머지는 달리는 도로 위에 */
        val FLOATING = setOf(RAIN)
    }
}

/** 차로 글자: 0 = 갓길, null = 없음 */
fun laneText(lane: Int?): String = when (lane) {
    null -> ""
    0 -> "갓길 "
    else -> "${lane}차로 "
}

/** 누가 알렸나 — 우리만의 색: 사람 제보 + 차가 스스로 감지 */
enum class Source(val label: String) { DRIVER("운전자 제보"), AUTO("차량 자동 감지"), MINE("내 제보"), NAVI("내비 정보") }

/** 제보 처리 단계 — "접수 상황 빠른 반영" */
enum class ReportStage(val label: String) { RECEIVED("접수"), SHARED("공유"), CONFIRMED("확인"), RESOLVED("해결") }

/**
 * 도로 위 위험 하나.
 * atM = 내 차가 지금까지 달린 길 위의 위치(미터). 내 위치(posM)보다 크면 앞에 있다.
 * 시각은 모두 벽시계(ms): 처음 제보 · 다른 차에 공유 · 마지막 제보/확인. 마지막 확인 뒤 수명(ttlMin)이 지나면 소멸.
 */
data class Hazard(
    val id: String,
    val type: HazardType,
    val lane: Int?,
    val atM: Double,
    val reports: Int,
    val minutesAgo: Int,
    val source: Source,
    val stage: ReportStage = ReportStage.SHARED,
    val sharedTo: Int = 0,
    val confirms: Int = 0,
    val reportedAt: Long = System.currentTimeMillis() - minutesAgo * 60_000L,
    val sharedAt: Long? = if (stage == ReportStage.RECEIVED) null else reportedAt + 2_000L,
    val lastSeenAt: Long = reportedAt,
) {
    /** 소멸까지 남은 분 (지우지 않는 종류면 null) */
    fun lifeLeftMin(now: Long = System.currentTimeMillis()): Int? = type.ttlMin?.let { it - ((now - lastSeenAt) / 60_000L).toInt() }
    fun expired(now: Long = System.currentTimeMillis()): Boolean = type.ttlMin?.let { now - lastSeenAt > it * 60_000L } ?: false
}

/** 08:42 처럼 */
fun clockText(ms: Long): String = SimpleDateFormat("HH:mm", Locale.KOREA).format(Date(ms))

/** 방금 · 4분 전 · 2시간 전 · 3일 전 */
fun agoText(ms: Long, now: Long = System.currentTimeMillis()): String {
    val m = ((now - ms) / 60_000L).toInt()
    return when {
        m < 1 -> "방금"
        m < 60 -> "${m}분 전"
        m < 24 * 60 -> "${m / 60}시간 전"
        else -> "${m / (24 * 60)}일 전"
    }
}

/** 30분 · 1시간 · 3일 */
fun spanText(min: Int): String = when {
    min < 60 -> "${min}분"
    min < 24 * 60 -> "${min / 60}시간"
    else -> "${min / (24 * 60)}일"
}

/** TMI 한 줄 — 화면 카드 + 음성 */
enum class TmiKind(val label: String, val color: Color) {
    DANGER("위험", Color(0xFFFF5A5F)),
    LOCAL("지금 이 동네", Color(0xFF5AA9FF)),
    CAR("내 차 × 가는 길", Color(0xFFFFB020)),
    MINE("내 기여", Color(0xFF3DDC97)),
    BRIEF("앞길 TMI", Color(0xFF2F80ED)),
    SYSTEM("Pixel TMI", Color(0xFF00AAD2)),
}

data class TmiLine(
    val kind: TmiKind,
    val text: String,
    val clips: List<String>,
    val atMillis: Long = System.currentTimeMillis(),
)

/** 화면 효과 신호 — 위험 컷인, 코인 튀어나오기, 레벨 업, 제보 소멸, 도착 세레모니 */
sealed interface Fx {
    data class Danger(val hazard: Hazard) : Fx
    data class Coins(val amount: Int) : Fx
    data class LevelUp(val level: Int, val title: String) : Fx
    data class Expired(val hazard: Hazard) : Fx
    data class Arrived(val coins: Int) : Fx
}

/** 내비가 알려 주는 길 위 지점 (방지턱·카메라 등) */
data class RoadAlert(val id: String, val type: HazardType, val remainM: Int)

/** 지금 가장 가까운 위험에 대한 큰 경고 카드 */
data class Approach(val hazard: Hazard, val distanceM: Int)

/** 방금 지난 위험 — "아직 있나요?" */
data class VerifyAsk(val hazard: Hazard, val untilMillis: Long)

/** 보상 — 2번 아이디어에서 남긴 조각 */
data class Rewards(
    val coins: Int = 0,
    val helpedDrivers: Int = 0,
    val reportsToday: Int = 0,
) {
    val level: Int get() = LEVELS.indexOfLast { coins >= it } + 1
    val title: String get() = TITLES[(level - 1).coerceIn(0, TITLES.lastIndex)]
    val nextAt: Int? get() = LEVELS.getOrNull(level)
    val prevAt: Int get() = LEVELS[(level - 1).coerceIn(0, LEVELS.lastIndex)]

    companion object {
        val LEVELS = listOf(0, 60, 150, 280, 450)
        val TITLES = listOf("새내기 파수꾼", "도로 지킴이", "포트홀 헌터", "골목의 레이더", "도로의 수호자")
    }
}

/** 내비 상태 — 목적지가 있으면 "가는 길 TMI", 없으면 "내 주변 TMI" */
data class NaviState(
    val connected: Boolean = false,
    val address: String? = null,
    val destinationName: String? = null,
    val remainM: Int? = null,
    val remainSec: Int? = null,
) {
    val hasRoute: Boolean get() = destinationName != null && (remainM ?: 0) > 0
}

/** 화면에 그릴 전체 상태 */
data class TmiUi(
    val on: Boolean = true,
    val posM: Double = 0.0,
    val hazards: List<Hazard> = emptyList(),
    val approach: Approach? = null,
    val verify: VerifyAsk? = null,
    val myReport: Hazard? = null,
    /** 이번 주행에 내가 한 제보 모두 (최신이 앞) — 새로 제보해도 앞의 것이 길 위에 남는다. 시동(앱)이 꺼지면 사라진다 */
    val mine: List<Hazard> = emptyList(),
    val feed: List<TmiLine> = emptyList(),
    val rewards: Rewards = Rewards(),
    val fleetNearby: Int = 0,
    val listening: Boolean = false,
    val heard: String? = null,
    val parkedSummary: Boolean = false,
    val lastReportLatencyMs: Long? = null,
    /** 차는 서 있는데 내비가 길을 따라가는 중 (내비 모의 주행) */
    val naviMoving: Boolean = false,
    val naviSpeedKmh: Float = 0f,
    /** 뒤차가 제보한 긴급차량 — 뒤에서 다가와 나를 앞질러 간다 */
    val chaser: Hazard? = null,
    /** 내 제보 기록 (최신이 앞) */
    val history: List<ReportRecord> = emptyList(),
)

/** 내 제보 한 건의 기록 — '내 기록' 화면 */
data class ReportRecord(
    val id: String,
    val type: HazardType,
    val lane: Int?,
    val at: Long,
    val stage: ReportStage = ReportStage.RECEIVED,
    val reports: Int = 1,
    val sharedTo: Int = 0,
    val confirms: Int = 0,
    val coins: Int = 0,
)
