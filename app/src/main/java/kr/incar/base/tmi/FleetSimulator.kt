package kr.incar.base.tmi

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * 시연용 가상 Pleos 차량 네트워크.
 * 실서비스에서는 서버가 하는 일(제보 모으기·주변 차에 뿌리기·다른 차의 확인)을 앱 안에서 흉내 낸다.
 * 숫자는 화면과 음성 파일(assets/voice/local_*.wav)이 같은 값을 쓰도록 여기 한곳에 둔다.
 */
class FleetSimulator(private val scope: CoroutineScope) {

    val nearbyCars = 23

    /** 출근길 경로 위에 이미 올라와 있는 다른 운전자들의 제보 */
    fun seedCommute(startM: Double): List<Hazard> = listOf(
        Hazard("h-cam", HazardType.CAMERA, lane = null, atM = startM + 700, reports = 0, minutesAgo = 0, source = Source.NAVI),
        Hazard("h-debris", HazardType.DEBRIS, lane = 2, atM = startM + 1500, reports = 8, minutesAgo = 4, source = Source.DRIVER, sharedTo = 52, confirms = 6),
        // 1시간 전 사고 제보 — 마지막 확인 뒤 새 제보가 없어 시연 시작 40초 뒤 수명(60분)이 끝나 소멸
        Hazard("h-acc", HazardType.ACCIDENT, lane = 1, atM = startM + 2800, reports = 3, minutesAgo = 60, source = Source.DRIVER, sharedTo = 44, confirms = 2,
            lastSeenAt = System.currentTimeMillis() - (60 * 60_000L - 40_000L)),
        Hazard("h-bump", HazardType.BUMP, lane = null, atM = startM + 3300, reports = 0, minutesAgo = 0, source = Source.NAVI),
        Hazard("h-work", HazardType.CONSTRUCTION, lane = 3, atM = startM + 4200, reports = 5, minutesAgo = 25, source = Source.DRIVER, sharedTo = 37, confirms = 4),
    )

    /**
     * 내비에 목적지가 찍히면: 그 길 위에 위험 제보를 흩어 놓는다 (시연 차량 네트워크 데이터).
     * 길이 짧아도 최소 간격을 두고, 끝 쪽엔 보호구역.
     */
    fun seedRoute(startM: Double, lengthM: Int): List<Hazard> {
        val len = lengthM.coerceAtLeast(2000).toDouble()
        fun at(f: Double) = startM + (len * f).coerceAtLeast(400.0)
        // 시연 때마다 5곳: 단속카메라 + 매번 다른 상황 4곳
        val always = listOf(Triple(HazardType.POTHOLE, 1, 3), Triple(HazardType.JAM, null, 5))   // 포트홀은 첫 취지 · 정체는 늘
        val pool = (always + listOf(
            Triple(HazardType.DEBRIS, 2, 6), Triple(HazardType.ACCIDENT, 1, 4),
            Triple(HazardType.CONSTRUCTION, 3, 5), Triple(HazardType.ANIMAL, null, 2), Triple(HazardType.FOG, null, 4),
            Triple(HazardType.BREAKDOWN, 0, 2), Triple(HazardType.FLOOD, 2, 3), Triple(HazardType.ICE, null, 3),
            Triple(HazardType.ROCKFALL, 2, 2), Triple(HazardType.SIGNAL, null, 3), Triple(HazardType.PEDESTRIAN, null, 2),
            Triple(HazardType.ROAD_CLOSED, 2, 3),
        ).shuffled().take(2)).shuffled()
        val spots = listOf(0.25, 0.45, 0.65, 0.85)
        return listOf(Hazard("r-cam", HazardType.CAMERA, lane = null, atM = at(0.10), reports = 0, minutesAgo = 0, source = Source.NAVI)) +
            pool.mapIndexed { i, (t, lane, n) ->
                Hazard("r-${t.name.lowercase()}", t, lane = lane, atM = at(spots[i]), reports = n, minutesAgo = 3 + i * 7, source = Source.DRIVER, sharedTo = 15 + n * 9, confirms = maxOf(1, n - 1))
            }
    }

    private fun seedRouteOld(startM: Double, lengthM: Int): List<Hazard> {
        val len = lengthM.coerceAtLeast(2000).toDouble()
        fun at(f: Double) = startM + (len * f).coerceAtLeast(400.0)
        return listOf(
            Hazard("r-cam", HazardType.CAMERA, lane = null, atM = at(0.10), reports = 0, minutesAgo = 0, source = Source.NAVI),
            Hazard("r-debris", HazardType.DEBRIS, lane = 2, atM = at(0.22), reports = 6, minutesAgo = 7, source = Source.DRIVER, sharedTo = 48, confirms = 4),
            Hazard("r-pothole", HazardType.POTHOLE, lane = 1, atM = at(0.38), reports = 3, minutesAgo = 26 * 60, source = Source.DRIVER, sharedTo = 120, confirms = 9),
            Hazard("r-bump", HazardType.BUMP, lane = null, atM = at(0.52), reports = 0, minutesAgo = 0, source = Source.NAVI),
            Hazard("r-acc", HazardType.ACCIDENT, lane = 1, atM = at(0.66), reports = 4, minutesAgo = 12, source = Source.DRIVER, sharedTo = 63, confirms = 3),
            Hazard("r-work", HazardType.CONSTRUCTION, lane = 3, atM = at(0.80), reports = 5, minutesAgo = 40, source = Source.DRIVER, sharedTo = 37, confirms = 4),
            Hazard("r-school", HazardType.SCHOOL, lane = null, atM = at(0.93), reports = 0, minutesAgo = 0, source = Source.NAVI),
            Hazard("r-animal", HazardType.ANIMAL, lane = null, atM = at(0.30), reports = 2, minutesAgo = 6, source = Source.DRIVER, sharedTo = 22, confirms = 2),
            Hazard("r-amb", HazardType.EMERGENCY, lane = 1, atM = at(0.46), reports = 3, minutesAgo = 1, source = Source.DRIVER, sharedTo = 31, confirms = 2),
            Hazard("r-fog", HazardType.FOG, lane = null, atM = at(0.58), reports = 4, minutesAgo = 15, source = Source.DRIVER, sharedTo = 40, confirms = 3),
            Hazard("r-break", HazardType.BREAKDOWN, lane = 0, atM = at(0.73), reports = 2, minutesAgo = 9, source = Source.DRIVER, sharedTo = 18, confirms = 2),
            Hazard("r-flood", HazardType.FLOOD, lane = 2, atM = at(0.86), reports = 3, minutesAgo = 25, source = Source.DRIVER, sharedTo = 27, confirms = 2),
        )
    }

    /** 경로 앞쪽에 비 소식이 있는지 (다른 차들의 와이퍼 데이터) */
    val rainAhead = true

    /** 평화로울 때 꺼내는 동네 TMI — 차량 데이터를 모은 것 + 운전자 한마디 */
    val localPool: List<TmiLine> = listOf(
        TmiLine(TmiKind.LOCAL, "지금 이 근처에서 Pleos 차량 23대가 함께 달리고 있어요.", listOf("local_fleet")),
        TmiLine(TmiKind.LOCAL, "이 길은 아침 8시쯤 등교 차량이 많다는 제보가 있어요.", listOf("local_school")),
        TmiLine(TmiKind.LOCAL, "이 구간은 지금 평소보다 조금 느립니다.", listOf("local_slow")),
        TmiLine(TmiKind.LOCAL, "어제 이 동네 포트홀 제보 2건이 해결됐습니다.", listOf("local_resolved")),
        TmiLine(TmiKind.LOCAL, "근처 차량 10대 중 4대가 와이퍼를 켰습니다. 곧 비가 올 수 있어요.", listOf("local_wiper")),
    )

    /**
     * 서버에 제보를 보내고 받는 흉내. 단계가 바뀔 때마다 update를 부른다.
     * needed = 같은 지점 제보가 몇 건 모여야 다른 차에 공유하나 (혼자 한 제보는 바로 퍼뜨리지 않는다. 시연은 1건)
     */
    fun submit(h: Hazard, timeScale: Double, needed: Int, update: (Hazard) -> Unit) {
        scope.launch {
            delay(250) // 서버 접수 왕복 (시연 네트워크)
            var cur = h
            while (cur.reports < needed) {
                // 같은 지점에 다른 차량 제보(또는 급감속 감지)가 들어올 때까지 '확인 대기'
                delay((6000 / timeScale.coerceAtLeast(1.0)).toLong().coerceAtLeast(2500))
                cur = cur.copy(reports = cur.reports + 1, lastSeenAt = System.currentTimeMillis())
                update(cur)
            }
            val shared = cur.copy(stage = ReportStage.SHARED, sharedTo = SHARED_TO, sharedAt = System.currentTimeMillis())
            update(shared)
            delay((5000 / timeScale.coerceAtLeast(1.0)).toLong().coerceAtLeast(2500))
            update(shared.copy(stage = ReportStage.CONFIRMED, confirms = if (h.type == HazardType.HARD_BRAKE) 4 else 3, lastSeenAt = System.currentTimeMillis()))
        }
    }

    companion object {
        const val SHARED_TO = 41
        const val RAIN_SHARED_TO = 28
        const val HELPED_TODAY = 213
    }
}
