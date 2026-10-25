package kr.incar.base.rules

import kr.incar.base.car.Gear

/**
 * 베이스 동작 확인용 규칙. 아이디어가 정해지면 이 목록을 아이디어 규칙으로 바꾼다.
 * 문장은 TTS 발음을 위해 짧고 차분하게 쓴다.
 */
object SampleRules {
    val all = listOf(
        Rule(
            id = "belt",
            title = "안전벨트",
            condition = { it.moving && it.driverBeltFastened == false },
            message = { "운전석 안전벨트를 확인해 주세요." },
        ),
        Rule(
            id = "door_moving",
            title = "문 열림",
            condition = { it.moving && it.anyDoorOpen == true },
            message = { "문이 열린 채로 움직이고 있습니다." },
        ),
        Rule(
            id = "rain_lights",
            title = "빗길 전조등",
            condition = { it.wiperOn == true && it.headlightsOn == false },
            message = { "비가 오는 것 같습니다. 전조등을 켜시면 더 안전합니다." },
        ),
        Rule(
            id = "low_fuel",
            title = "연료 부족",
            condition = { (it.fuelPercent ?: 100f) < 15f },
            message = { s -> "연료가 얼마 남지 않았습니다. 약 ${s.fuelRangeKm?.toInt() ?: "-"}킬로미터 더 갈 수 있습니다." },
        ),
        Rule(
            id = "hot_cabin",
            title = "실내 온도",
            condition = { (it.cabinTempC ?: 0f) >= 28.5f },
            message = { "실내가 조금 덥습니다. 온도를 낮춰 드릴까요?" },
        ),
        Rule(
            id = "window_parked",
            title = "창문 열림",
            condition = { it.gear == Gear.P && (it.driverWindowPercent ?: 0) > 0 },
            message = { "주차 중인데 운전석 창문이 열려 있습니다." },
        ),
        Rule(
            id = "long_drive",
            title = "장거리 휴식",
            condition = { (it.tripKm ?: 0f) >= 150f },
            message = { "오래 운전하셨습니다. 다음 휴게소에서 잠시 쉬어 가시면 좋겠습니다." },
        ),
    )
}
