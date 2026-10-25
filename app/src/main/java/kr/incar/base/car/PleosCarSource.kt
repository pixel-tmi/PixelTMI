package kr.incar.base.car

import ai.pleos.playground.vehicle.Vehicle
import ai.pleos.playground.vehicle.api.model.area.DoorArea
import ai.pleos.playground.vehicle.api.model.area.SeatArea
import ai.pleos.playground.vehicle.api.model.area.WindowArea
import ai.pleos.playground.vehicle.constant.area.DoorValue
import ai.pleos.playground.vehicle.constant.area.SeatValue
import ai.pleos.playground.vehicle.constant.area.TurnSignalValue
import ai.pleos.playground.vehicle.constant.area.WindowValue
import ai.pleos.playground.vehicle.constant.control.CruiseControl
import ai.pleos.playground.vehicle.constant.control.DrivingModeType
import ai.pleos.playground.vehicle.constant.control.LightState
import ai.pleos.playground.vehicle.constant.control.VehicleGear
import ai.pleos.playground.vehicle.constant.control.WiperState
import ai.pleos.playground.vehicle.listener.BrakePedalStatusListener
import ai.pleos.playground.vehicle.listener.CruiseControlStateListener
import ai.pleos.playground.vehicle.listener.DistanceDrivenListener
import ai.pleos.playground.vehicle.listener.DoorLockStateListener
import ai.pleos.playground.vehicle.listener.DoorPositionListener
import ai.pleos.playground.vehicle.listener.DrivingModeStateListener
import ai.pleos.playground.vehicle.listener.EvBatteryStateOfChargeListener
import ai.pleos.playground.vehicle.listener.FuelPercentListener
import ai.pleos.playground.vehicle.listener.GearSelectionListener
import ai.pleos.playground.vehicle.listener.HvacPowerStateListener
import ai.pleos.playground.vehicle.listener.HvacTemperatureListener
import ai.pleos.playground.vehicle.listener.LightStateListener
import ai.pleos.playground.vehicle.listener.RangeRemainingListener
import ai.pleos.playground.vehicle.listener.SeatBeltBuckledStateListener
import ai.pleos.playground.vehicle.listener.SteeringWheelAngleListener
import ai.pleos.playground.vehicle.listener.TurnSignalStateListener
import ai.pleos.playground.vehicle.listener.WindowPositionListener
import ai.pleos.playground.vehicle.listener.WiperStateListener
import android.content.Context
import android.os.SystemClock
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

/**
 * 실제 Pleos 차량(또는 Pleos 에뮬레이터)의 Vehicle SDK에서 값을 받아 CarState로 바꾼다.
 * 신호마다 따로 구독하고, 어떤 신호가 실패했는지 기록해 "이 차가 주는 값 / 안 주는 값"을 보여준다.
 * 차량 속도는 Vehicle SDK에 없어서 CarSpeedSource(안드로이드 표준 Car API)가 따로 채운다.
 */
class PleosCarSource(private val context: Context, @Suppress("unused") private val scope: CoroutineScope) : CarSource {

    private val vehicle = Vehicle(context.applicationContext)
    private val speed = CarSpeedSource(context) { kmh -> push("속도") { it.copy(speedKmh = kmh) } }
    private var initialized = false

    private val _state = MutableStateFlow(CarState())
    override val state: StateFlow<CarState> = _state.asStateFlow()

    private val _status = MutableStateFlow(SourceStatus(false, "Pleos 차량", "연결 전"))
    override val status: StateFlow<SourceStatus> = _status.asStateFlow()

    private val _signals = MutableStateFlow<Map<String, SignalHealth>>(emptyMap())
    /** 신호별 상태: 값이 들어왔는지, 실패했는지, 마지막 수신 간격 */
    val signals: StateFlow<Map<String, SignalHealth>> = _signals.asStateFlow()

    private val unregisters = mutableListOf<() -> Unit>()
    private val doorOpen = mutableMapOf<DoorValue, Boolean>()
    private var windowMax = 10

    private val driverSeat = SeatArea(SeatValue.ROW_1_LEFT)
    private val driverDoor = DoorArea(DoorValue.ROW_1_LEFT)
    private val driverWindow = WindowArea(WindowValue.ROW_1_LEFT)
    private val windshield = WindowArea(WindowValue.FRONT_WINDSHIELD)

    override fun start() {
        if (initialized) return
        // 갤럭시 탭처럼 차가 아닌 기기: Pleos SDK가 조용히 '연결됨'처럼 굴어도 차량 신호는 오지 않는다 → 처음부터 GPS + 화면 조작
        if (!CarSpeedSource.available) {
            _status.value = SourceStatus(false, "Pleos 차량", "차가 아닌 기기 → GPS + Pleos 화면 조작 모드")
            startGps()
            return
        }
        try {
            vehicle.initialize()
            initialized = true
            _status.value = SourceStatus(true, "Pleos 차량", "연결됨 · 신호 기다리는 중")
        } catch (e: Throwable) {
            // Pleos가 아닌 기기(갤럭시 탭 등): 차량 신호 대신 GPS 속도로 달린다
            _status.value = SourceStatus(false, "Pleos 차량", "연결 실패 → GPS 모드: ${e.message ?: e.javaClass.simpleName}")
            startGps()
            return
        }
        subscribeAll()
        speed.start { error -> mark("속도", error) }
    }

    /** 속도 권한을 받은 뒤 다시 구독 (첫 실행) */
    fun retrySpeed() {
        if (!initialized) return
        speed.stop()
        speed.start { error -> mark("속도", error) }
    }

    override fun stop() {
        speed.stop()
        gps?.let { l -> runCatching { context.getSystemService(android.location.LocationManager::class.java)?.removeUpdates(l) } }
        gps = null
        simHandler.removeCallbacks(simTick)
        simOn = false
        if (!initialized) return
        unregisters.forEach { runCatching(it) }
        unregisters.clear()
        runCatching { vehicle.release() }
        initialized = false
    }

    private fun subscribeAll() {
        val gear = vehicle.getGear()
        val gearL = object : GearSelectionListener {
            override fun onSelected(gear: VehicleGear?) = push("기어") { it.copy(gear = gear?.toGear()) }
            override fun onFailed(exception: Exception) = mark("기어", exception)
        }
        sub("기어", { gear.registerGearSelection(gearL) }) { gear.unregisterGearSelection(gearL) }

        val brake = vehicle.getBrake()
        val brakeL = object : BrakePedalStatusListener {
            override fun onBrakePedalStatusUpdated(status: Boolean?) = push("브레이크 페달") { it.copy(brakePedalPressed = status) }
            override fun onFailed(exception: Exception) = mark("브레이크 페달", exception)
        }
        sub("브레이크 페달", { brake.registerBrakePedalStatus(brakeL) }) { brake.unregisterBrakePedalStatus(brakeL) }

        val fuel = vehicle.getFuel()
        val fuelL = object : FuelPercentListener {
            override fun onFuelPercentUpdated(percent: Int?) = push("연료") { it.copy(fuelPercent = percent?.toFloat()) }
            override fun onFailed(exception: Exception) = mark("연료", exception)
        }
        sub("연료", { fuel.registerFuelPercent(fuelL) }) { fuel.unregisterFuelPercent(fuelL) }

        val odo = vehicle.getOdometer()
        val rangeL = object : RangeRemainingListener {
            // SDK는 미터 단위로 준다 (에뮬레이터 500000 = 운전 화면 500km)
            override fun onRangeRemainingChanged(range: Float?) = push("주행가능거리") { it.copy(fuelRangeKm = range?.div(1000f)) }
            override fun onFailed(exception: Exception) = mark("주행가능거리", exception)
        }
        sub("주행가능거리", { odo.registerRangeRemainingListener(rangeL) }) { odo.unregisterRangeRemainingListener(rangeL) }
        val odoL = object : DistanceDrivenListener {
            override fun onDistanceDrivenUpdated(distance: Float?) = push("총 주행거리") { it.copy(odometerKm = distance) }
            override fun onFailed(exception: Exception) = mark("총 주행거리", exception)
        }
        sub("총 주행거리", { odo.registerDistanceDriven(odoL) }) { odo.unregisterDistanceDriven(odoL) }
        val tripL = object : DistanceDrivenListener {
            override fun onDistanceDrivenUpdated(distance: Float?) = push("이번 주행") { it.copy(tripKm = distance) }
            override fun onFailed(exception: Exception) = mark("이번 주행", exception)
        }
        sub("이번 주행", { odo.registerTripCurrentDrivingDistance(tripL) }) { odo.unregisterTripCurrentDrivingDistance(tripL) }

        val door = vehicle.getDoor()
        listOf(DoorValue.ROW_1_LEFT, DoorValue.ROW_1_RIGHT, DoorValue.ROW_2_LEFT, DoorValue.ROW_2_RIGHT).forEach { dv ->
            val area = DoorArea(dv)
            val l = object : DoorPositionListener {
                override fun onPositionUpdated(pos: Int?) {
                    doorOpen[dv] = (pos ?: 0) > 0
                    push("문 열림") { it.copy(anyDoorOpen = doorOpen.values.any { open -> open }) }
                }
                override fun onFailed(exception: Exception) = mark("문 열림", exception)
            }
            sub("문 열림", { door.registerDoorPosition(area, l) }) { door.unregisterDoorPosition(area, l) }
        }
        val lockL = object : DoorLockStateListener {
            override fun onDoorLockStateUpdated(locked: Boolean?) = push("문 잠금") { it.copy(doorsLocked = locked) }
            override fun onFailed(exception: Exception) = mark("문 잠금", exception)
        }
        sub("문 잠금", { door.registerDoorLockState(driverDoor, lockL) }) { door.unregisterDoorLockState(driverDoor, lockL) }

        val seat = vehicle.getSeat()
        val beltL = object : SeatBeltBuckledStateListener {
            override fun onSeatBeltBuckledStateUpdated(buckled: Boolean?) = push("안전벨트") { it.copy(driverBeltFastened = buckled) }
            override fun onFailed(exception: Exception) = mark("안전벨트", exception)
        }
        sub("안전벨트", { seat.registerSeatBeltBuckledState(driverSeat, beltL) }) { seat.unregisterSeatBeltBuckledState(driverSeat, beltL) }

        val window = vehicle.getWindow()
        runCatching {
            window.checkWindowPositionCapabilities(
                onComplete = { _, bounds -> (bounds[driverWindow]?.maxValue as? Number)?.toInt()?.takeIf { it > 0 }?.let { windowMax = it } },
                onFailed = { },
            )
        }
        val winL = object : WindowPositionListener {
            override fun onWindowPositionUpdated(pos: Int?) =
                push("운전석 창문") { it.copy(driverWindowPercent = pos?.let { p -> p * 100 / windowMax }) }
            override fun onFailed(exception: Exception) = mark("운전석 창문", exception)
        }
        sub("운전석 창문", { window.registerWindowPosition(driverWindow, winL) }) { window.unregisterWindowPosition(driverWindow, winL) }

        val hvac = vehicle.getHVAC()
        val powerL = object : HvacPowerStateListener {
            override fun onHvacPowerStateUpdated(on: Boolean?) = push("공조") { it.copy(hvacOn = on) }
            override fun onFailed(exception: Exception) = mark("공조", exception)
        }
        sub("공조", { hvac.registerHvacPowerState(driverSeat, powerL) }) { hvac.unregisterHvacPowerState(driverSeat, powerL) }
        val tempL = object : HvacTemperatureListener {
            override fun onHvacTemperatureUpdated(temperature: Float?) = push("실내 온도") { it.copy(cabinTempC = temperature) }
            override fun onFailed(exception: Exception) = mark("실내 온도", exception)
        }
        sub("실내 온도", { hvac.registerHvacTemperatureCurrent(driverSeat, tempL) }) { hvac.unregisterHvacTemperatureCurrent(driverSeat, tempL) }

        val light = vehicle.getLight()
        val lowBeamL = object : LightStateListener {
            override fun onLightStateUpdated(state: LightState?) = push("전조등") { it.copy(headlightsOn = state == LightState.ON) }
            override fun onFailed(exception: Exception) = mark("전조등", exception)
        }
        sub("전조등", { light.registerLowBeamLightState(lowBeamL) }) { light.unregisterLowBeamLightState(lowBeamL) }

        val wiper = vehicle.getWiper()
        val wiperL = object : WiperStateListener {
            override fun onWiperStateUpdated(state: WiperState?) = push("와이퍼") { it.copy(wiperOn = state == WiperState.ON) }
            override fun onFailed(exception: Exception) = mark("와이퍼", exception)
        }
        sub("와이퍼", { wiper.registerWiperState(windshield, wiperL) }) { wiper.unregisterWiperState(windshield, wiperL) }

        val turn = vehicle.getTurnSignal()
        val turnL = object : TurnSignalStateListener {
            override fun onTurnSignalStateUpdated(state: TurnSignalValue?) = push("방향지시등") {
                it.copy(turnSignal = when (state) { TurnSignalValue.LEFT -> TurnSignal.LEFT; TurnSignalValue.RIGHT -> TurnSignal.RIGHT; else -> TurnSignal.NONE })
            }
            override fun onFailed(exception: Exception) = mark("방향지시등", exception)
        }
        sub("방향지시등", { turn.registerTurnSignalState(turnL) }) { turn.unregisterTurnSignalState(turnL) }

        val drive = vehicle.getDrivingMode()
        val modeL = object : DrivingModeStateListener {
            override fun onDrivingModeStateUpdated(mode: DrivingModeType?) = push("주행 모드") { it.copy(driveMode = mode?.name) }
            override fun onFailed(exception: Exception) = mark("주행 모드", exception)
        }
        sub("주행 모드", { drive.registerDrivingModeState(modeL) }) { drive.unregisterDrivingModeState(modeL) }
        val cruiseL = object : CruiseControlStateListener {
            override fun onCruiseControlStateUpdated(state: CruiseControl?) = push("크루즈") { it.copy(cruiseOn = state == CruiseControl.ACTIVATED) }
            override fun onFailed(exception: Exception) = mark("크루즈", exception)
        }
        sub("크루즈", { drive.registerCruiseControlState(cruiseL) }) { drive.unregisterCruiseControlState(cruiseL) }

        val ev = vehicle.getEvBattery()
        val socL = object : EvBatteryStateOfChargeListener {
            override fun onEvBatteryStateOfChargeUpdated(soc: Int?) = push("배터리") { it.copy(evSocPercent = soc?.toFloat()) }
            override fun onFailed(exception: Exception) = mark("배터리", exception)
        }
        sub("배터리", { ev.registerEvBatteryStateOfCharge(socL) }) { ev.unregisterEvBatteryStateOfCharge(socL) }

        val wheel = vehicle.getSteeringWheel()
        val angleL = object : SteeringWheelAngleListener {
            override fun onSteeringWheelAngleUpdated(angle: Float?) = push("핸들 각도") { it.copy(steeringAngleDeg = angle) }
            override fun onFailed(exception: Exception) = mark("핸들 각도", exception)
        }
        sub("핸들 각도", { wheel.registerSteeringWheelAngle(angleL) }) { wheel.unregisterSteeringWheelAngle(angleL) }
    }

    private inline fun sub(name: String, register: () -> Unit, noinline unregister: () -> Unit) {
        try {
            register()
            unregisters += unregister
            _signals.update { it + (name to (it[name] ?: SignalHealth(name))) }
        } catch (e: Throwable) {
            mark(name, e as? Exception ?: RuntimeException(e))
        }
    }

    // ── GPS 모드 (차량 SDK가 없는 기기): 속도는 GPS, 기어는 "달리는 중이면 D" ──
    private var gps: android.location.LocationListener? = null
    private var gpsSession = false
    private var stillSince = 0L

    /** 위치 권한을 나중에 받았을 때 다시 시도 */
    fun retryGps() { if ((!initialized || !CarSpeedSource.available) && gps == null) startGps() }

    /** 네이버 지도 목적지 도착: GPS 모드면 바로 주차로 본다 (도착 세레모니) */
    fun arrived() {
        if (!controllable || !gpsSession) return
        gpsSession = false
        stillSince = 0L
        if (manualGear != null) { manualGear = Gear.P; simKmh = 0f }
        push("GPS 속도") { it.copy(speedKmh = 0f, gear = Gear.P) }
    }

    // ── 탭 'Pleos 전용 앱' 화면 조작 = 가상 차량 ──
    // P·R·N·D·와이퍼·전조등·문·창문·온도를 Pleos 화면에서 누르면 바뀌고 TMI가 그대로 반응한다.
    // 실제로 달리면(GPS 시속 8km 넘음) GPS 속도·D가 우선, 서 있는데 D를 누르면 가상 주행 속도로 달린다.
    private var manualGear: Gear? = null
    private var lastRealMoveAt = 0L
    private var simKmh = 0f
    private var simPhase = 0.0
    private var simOn = false
    private val simHandler = android.os.Handler(android.os.Looper.getMainLooper())
    private val simTick = object : Runnable {
        override fun run() { if (stepSim()) simHandler.postDelayed(this, 500) else simOn = false }
    }

    /** 과속 시연 (가상 주행을 시속 88km로) */
    @Volatile var simBoost = false
    fun toggleBoost() { simBoost = !simBoost }

    /** 화면에서 D를 눌러 가상 주행 중인가 (진짜로는 서 있음) */
    val simulating: Boolean get() = manualGear == Gear.D && SystemClock.elapsedRealtime() - lastRealMoveAt > 4000

    /** 화면에서 조작할 수 있나 (차가 아닌 기기 = 탭에서만) */
    val controllable: Boolean get() = !CarSpeedSource.available

    fun setGear(g: Gear) {
        if (!controllable) return
        if (g != Gear.D) simBoost = false
        manualGear = g
        gpsSession = g != Gear.P
        stillSince = 0L
        push("화면 조작") { it.copy(gear = g) }
        if (!simOn) { simOn = true; simHandler.post(simTick) }
    }

    fun toggleWiper() = control { it.copy(wiperOn = !(it.wiperOn ?: false)) }
    fun toggleLights() = control { it.copy(headlightsOn = !(it.headlightsOn ?: false)) }
    fun toggleDoor() = control { it.copy(anyDoorOpen = !(it.anyDoorOpen ?: false)) }
    fun toggleWindow() = control { it.copy(driverWindowPercent = if ((it.driverWindowPercent ?: 0) > 0) 0 else 40) }
    fun toggleHvac() = control { it.copy(hvacOn = !(it.hvacOn ?: false)) }
    fun nudgeTemp(d: Float) = control { it.copy(cabinTempC = ((it.cabinTempC ?: 22f) + d).coerceIn(16f, 30f), hvacOn = true) }

    private fun control(change: (CarState) -> CarState) { if (controllable) push("화면 조작", change) }

    /** 0.5초마다: D면 시속 30~46km 사이로 출렁이며 달리고, R은 천천히, P·N이면 멈춘다. 계속 돌아야 하면 true */
    private fun stepSim(): Boolean {
        val g = manualGear ?: return false
        if (SystemClock.elapsedRealtime() - lastRealMoveAt < 4000) return true   // 진짜로 달리는 중 → GPS가 속도를 준다
        simPhase += 0.08
        val target = when (g) {
            Gear.D -> if (simBoost) 88f + 4f * kotlin.math.sin(simPhase).toFloat() else 52f + 6f * kotlin.math.sin(simPhase).toFloat()
            Gear.R -> 6f
            else -> 0f
        }
        simKmh += (target - simKmh).coerceIn(-9f, 4f)
        if (target == 0f && simKmh < 0.6f) simKmh = 0f
        push("가상 주행") { it.copy(speedKmh = simKmh) }
        return !(target == 0f && simKmh == 0f)
    }

    private fun startGps() {
        if (gps != null) return
        val lm = context.getSystemService(android.location.LocationManager::class.java) ?: return
        if (context.checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            _status.value = SourceStatus(false, "GPS 모드", "위치 권한이 필요해요")
            return
        }
        val l = android.location.LocationListener { loc ->
            val kmh = if (loc.hasSpeed()) loc.speed * 3.6f else 0f
            val now = SystemClock.elapsedRealtime()
            // 시속 8km를 넘으면 주행 시작, 3분 넘게 서 있으면 주차로 본다 (신호 대기는 주행 중)
            if (kmh > 8f) { gpsSession = true; stillSince = 0L; lastRealMoveAt = now; manualGear = null } else if (stillSince == 0L) stillSince = now
            if (manualGear == null && gpsSession && stillSince != 0L && now - stillSince > 180_000) gpsSession = false
            // 화면에서 기어를 골라 가상 주행 중이면(진짜로는 서 있음) 속도·기어는 가상 쪽이 쥔다
            if (manualGear == null) push("GPS 속도") { it.copy(speedKmh = kmh, gear = if (gpsSession) Gear.D else Gear.P) }
        }
        runCatching {
            lm.requestLocationUpdates(android.location.LocationManager.GPS_PROVIDER, 1000L, 0f, l, android.os.Looper.getMainLooper())
            gps = l
            _status.value = SourceStatus(true, "GPS 모드", "GPS 속도로 달려요")
        }.onFailure { _status.value = SourceStatus(false, "GPS 모드", "GPS 시작 실패: ${it.javaClass.simpleName}") }
    }

    private fun push(name: String, change: (CarState) -> CarState) {
        _state.update(change)
        val now = SystemClock.elapsedRealtime()
        _signals.update { map ->
            val old = map[name] ?: SignalHealth(name)
            map + (name to old.copy(count = old.count + 1, lastAt = now, gapMs = if (old.lastAt == 0L) null else now - old.lastAt, error = null))
        }
        refreshStatus()
    }

    private fun mark(name: String, e: Exception) {
        Log.w(TAG, "$name 실패: ${e.message}", e)
        _signals.update { map -> map + (name to (map[name] ?: SignalHealth(name)).copy(error = e.message ?: e.javaClass.simpleName)) }
        refreshStatus()
    }

    private fun refreshStatus() {
        val all = _signals.value.values
        val ok = all.count { it.count > 0 }
        val bad = all.count { it.error != null && it.count == 0 }
        _status.value = SourceStatus(initialized, "Pleos 차량", "값 받는 신호 ${ok}개 · 실패 ${bad}개")
    }

    private fun VehicleGear.toGear(): Gear? = when (this) {
        VehicleGear.GEAR_PARK -> Gear.P
        VehicleGear.GEAR_REVERSE -> Gear.R
        VehicleGear.GEAR_NEUTRAL -> Gear.N
        VehicleGear.GEAR_UNKNOWN -> null
        else -> Gear.D
    }

    companion object {
        const val TAG = "PleosCarSource"
    }
}

data class SignalHealth(
    val name: String,
    val count: Int = 0,
    val lastAt: Long = 0L,
    val gapMs: Long? = null,
    val error: String? = null,
)
