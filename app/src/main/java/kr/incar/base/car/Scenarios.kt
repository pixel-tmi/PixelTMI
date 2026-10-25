package kr.incar.base.car

data class ScenarioStep(
    val afterMs: Long,
    val label: String = "",
    val change: (CarState) -> CarState,
)

data class Scenario(
    val title: String,
    val summary: String,
    val initial: CarState,
    val steps: List<ScenarioStep>,
)

/** 시나리오를 읽기 쉽게 적기 위한 작은 도우미. */
class ScenarioBuilder(private val title: String, private val summary: String, private val initial: CarState) {
    private val steps = mutableListOf<ScenarioStep>()

    fun at(afterMs: Long, label: String = "", change: (CarState) -> CarState) {
        steps += ScenarioStep(afterMs, label, change)
    }

    /** 속도를 부드럽게 올리거나 내린다 (0.5초 간격). */
    fun ramp(toKmh: Float, overMs: Long, label: String = "") {
        val ticks = (overMs / 500).coerceAtLeast(1)
        for (i in 1..ticks) {
            // 남은 칸 수로 나눠 가면 상태를 따로 기억하지 않아도 직선으로 변한다 (재생을 반복해도 안전)
            val remaining = ticks - i + 1
            steps += ScenarioStep(500, if (i == 1L) label else "") { s ->
                val cur = s.speedKmh ?: 0f
                s.copy(speedKmh = cur + (toKmh - cur) / remaining)
            }
        }
    }

    fun build() = Scenario(title, summary, initial, steps.toList())
}

fun scenario(title: String, summary: String, initial: CarState, block: ScenarioBuilder.() -> Unit) =
    ScenarioBuilder(title, summary, initial).apply(block).build()

/** 아이디어가 정해지기 전까지 쓰는 공용 시나리오. 아이디어별 시나리오는 여기에 추가한다. */
object Scenarios {

    private val parked = CarState(
        speedKmh = 0f, gear = Gear.P, parkingBrakeOn = true, brakePedalPressed = false,
        fuelPercent = 34f, fuelRangeKm = 210f, odometerKm = 12480f, tripKm = 0f,
        anyDoorOpen = false, doorsLocked = true, driverWindowPercent = 0,
        cabinTempC = 27f, outsideTempC = 14f, hvacOn = false, headlightsOn = false,
        wiperOn = false, turnSignal = TurnSignal.NONE, driveMode = "COMFORT",
        cruiseOn = false, driverBeltFastened = false, steeringAngleDeg = 0f,
    )

    val commute = scenario("출근길", "탑승 → 출발 → 비 → 연료 부족 → 도착", parked) {
        at(1500, "운전자 탑승") { it.copy(doorsLocked = false, anyDoorOpen = true) }
        at(2000, "문 닫힘 · 공조 켜짐") { it.copy(anyDoorOpen = false, hvacOn = true) }
        at(2000, "벨트 안 맨 채 기어 D") { it.copy(gear = Gear.D, parkingBrakeOn = false) }
        ramp(18f, 3000, "출발")
        at(2500, "안전벨트 착용") { it.copy(driverBeltFastened = true) }
        ramp(62f, 5000, "간선도로 진입")
        at(3000, "비가 내림 · 와이퍼 작동") { it.copy(wiperOn = true) }
        at(4000, "전조등 켬") { it.copy(headlightsOn = true) }
        at(3000, "연료 부족 구간") { it.copy(fuelPercent = 12f, fuelRangeKm = 70f, tripKm = 18.4f) }
        at(1000, "우회전 준비") { it.copy(turnSignal = TurnSignal.RIGHT) }
        ramp(25f, 3000)
        at(1500) { it.copy(turnSignal = TurnSignal.NONE) }
        ramp(0f, 3000, "회사 도착")
        at(1500, "주차") { it.copy(gear = Gear.P, parkingBrakeOn = true, wiperOn = false) }
        at(2000, "창문 연 채 하차 준비") { it.copy(driverWindowPercent = 40, driverBeltFastened = false) }
    }

    val familyTrip = scenario("가족 나들이", "장거리 고속도로 · 휴게소 · 실내 온도", parked.copy(fuelPercent = 80f, fuelRangeKm = 560f)) {
        at(1500, "가족 탑승") { it.copy(doorsLocked = false, anyDoorOpen = true) }
        at(2000, "출발 준비") { it.copy(anyDoorOpen = false, driverBeltFastened = true, gear = Gear.D, parkingBrakeOn = false) }
        ramp(100f, 8000, "고속도로 진입")
        at(2000, "크루즈 켬") { it.copy(cruiseOn = true, driveMode = "ECO") }
        at(5000, "실내가 더워짐") { it.copy(cabinTempC = 29f) }
        at(4000, "1시간 50분 연속 주행") { it.copy(tripKm = 182f, fuelPercent = 58f, fuelRangeKm = 400f) }
        at(1000, "휴게소 진입") { it.copy(cruiseOn = false, turnSignal = TurnSignal.RIGHT) }
        ramp(0f, 5000)
        at(1000, "휴게소 주차") { it.copy(gear = Gear.P, parkingBrakeOn = true, turnSignal = TurnSignal.NONE) }
    }

    val all = listOf(commute, familyTrip)
}
