package kr.incar.base.tmi

import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kr.incar.base.car.CarState
import kr.incar.base.car.DemoCarSource
import kr.incar.base.car.Gear
import kr.incar.base.car.TurnSignal

/**
 * PT·영상용 "출근길" 시연 (약 2분).
 * 사건은 시간이 아니라 길 위 위치(posM)를 기준으로 일어나서, 에뮬레이터가 느려도 순서가 안 꼬인다.
 *
 * 1. 시동 → 내 주변 TMI (평화로움 + 동네 TMI)
 * 2. 목적지 "회사" → 가는 길 TMI (위험 2곳 · 비 소식 × 워셔액 부족 · 연료 충분)
 * 3. 1.5km 낙하물: 500m·잠시 후 경고 → 지나면 "아직 있나요?" → 있어요
 * 4. 말로 제보 "1차로에 포트홀 있어" → 접수 → 41대 공유 → 3대 확인
 * 5. 급감속 → 차가 스스로 제보 → 같은 지점 4대 확인
 * 6. 와이퍼 → 비 감지 → 뒤차 28대에 공유
 * 7. 4.2km 공사: 경고 → 지나면 "없어졌어요"
 * 8. 도착·주차 → 정산 (213대 도움 · 레벨 업)
 */
class CommuteDemo(
    private val demo: DemoCarSource,
    private val engine: TmiEngine,
    private val fleet: FleetSimulator,
    private val showNavi: (NaviState) -> Unit,
) {
    fun play() = demo.runScript("출근길") {
        engine.timeScale = SCALE
        engine.demoMode = true            // 시연: 제보 1건으로 바로 공유
        engine.peacefulGapMs = 16_000
        engine.resetTrip(fleet.seedCommute(0.0))
        showNavi(NaviState(connected = true, address = "성남시 수정구 시흥동"))
        set(PARKED)

        step("시동 · 내 주변 TMI")
        delay(1500)
        engine.briefing()
        delay(9000)

        step("내비 목적지: 회사")
        val route = NaviState(connected = true, address = "성남시 수정구 시흥동", destinationName = "회사 (판교)", remainM = 4700, remainSec = 600)
        engine.onNavi(route)
        showNavi(route)
        delay(15000)

        step("출발")
        update { it.copy(driverBeltFastened = true, gear = Gear.D, parkingBrakeOn = false) }
        rampTo(60f, 3000)

        step("낙하물 접근")
        awaitPos(1560.0)
        awaitVerify()
        delay(2500)
        step("\"아직 있어요\" 터치")
        engine.answerVerify(true)
        delay(3000)

        step("말로 제보 (부르지 않고 바로)")
        engine.setListening(true)
        delay(800)
        engine.onUtterance("제보")
        delay(2400)
        engine.onUtterance("1차로에 포트홀 있어")
        engine.setListening(false)
        delay(9000)

        step("급감속")
        rampTo(14f, 750)
        delay(1500)
        rampTo(55f, 2500)
        delay(6000)

        step("소나기 제보 (말로)")                   // 비는 와이퍼가 아니라 제보·기상청 예보로만 (와이퍼는 워셔액일 수도 있어서)
        update { it.copy(wiperOn = true, headlightsOn = true) }
        engine.onUtterance("소나기 와요")
        delay(7000)

        step("공사 구간 접근")
        awaitPos(4230.0)
        awaitVerify()
        delay(2500)
        step("\"없어졌어요\" 터치")
        engine.answerVerify(false)
        delay(3500)

        step("회사 도착")
        update { it.copy(turnSignal = TurnSignal.RIGHT) }
        rampTo(0f, 6000) // 천천히 서야 급감속으로 잡히지 않는다
        update { it.copy(gear = Gear.P, parkingBrakeOn = true, wiperOn = false, turnSignal = TurnSignal.NONE) }
        step("주차 · 오늘의 정산")
    }

    private suspend fun awaitPos(m: Double) {
        engine.ui.first { it.posM >= m }
    }

    private suspend fun awaitVerify() {
        engine.ui.first { it.verify != null }
    }

    companion object {
        /** 시연 배속: 60km/h가 화면에선 240km/h처럼 빨리 감긴다 */
        const val SCALE = 4.0

        val PARKED = CarState(
            speedKmh = 0f, gear = Gear.P, parkingBrakeOn = true, fuelPercent = 62f, fuelRangeKm = 480f,
            odometerKm = 12480f, anyDoorOpen = false, doorsLocked = false, driverWindowPercent = 0,
            cabinTempC = 21f, hvacOn = true, headlightsOn = false, wiperOn = false, turnSignal = TurnSignal.NONE,
            driverBeltFastened = false, washerLow = true,
        )
    }
}
