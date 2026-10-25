package kr.incar.base.car

/**
 * 앱이 바라보는 차량 상태 한 장면.
 * 값이 null이면 "이 차(또는 에뮬레이터)가 그 값을 주지 않음"이라는 뜻이다.
 */
data class CarState(
    val speedKmh: Float? = null,
    val gear: Gear? = null,
    val parkingBrakeOn: Boolean? = null,
    val brakePedalPressed: Boolean? = null,
    val fuelPercent: Float? = null,
    val fuelRangeKm: Float? = null,
    val evSocPercent: Float? = null,
    val evRangeKm: Float? = null,
    val charging: Boolean? = null,
    val odometerKm: Float? = null,
    val tripKm: Float? = null,
    val anyDoorOpen: Boolean? = null,
    val doorsLocked: Boolean? = null,
    val driverWindowPercent: Int? = null,
    val cabinTempC: Float? = null,
    val outsideTempC: Float? = null,
    val hvacOn: Boolean? = null,
    val headlightsOn: Boolean? = null,
    val wiperOn: Boolean? = null,
    val turnSignal: TurnSignal? = null,
    val driveMode: String? = null,
    val cruiseOn: Boolean? = null,
    val driverBeltFastened: Boolean? = null,
    val steeringAngleDeg: Float? = null,
    val washerLow: Boolean? = null,
) {
    val moving: Boolean get() = (speedKmh ?: 0f) > 3f
}

enum class Gear(val label: String) { P("P"), R("R"), N("N"), D("D") }

enum class TurnSignal(val label: String) { NONE("꺼짐"), LEFT("좌"), RIGHT("우"), HAZARD("비상등") }
