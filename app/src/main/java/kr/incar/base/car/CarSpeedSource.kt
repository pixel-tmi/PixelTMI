package kr.incar.base.car

import android.car.Car
import android.car.VehiclePropertyIds
import android.car.hardware.CarPropertyValue
import android.car.hardware.property.CarPropertyManager
import android.content.Context
import kotlin.math.abs

/**
 * 차량 속도. Pleos Vehicle SDK에는 속도 API가 없어서 안드로이드 오토모티브 표준 Car API로 읽는다.
 * android.car.permission.CAR_SPEED 런타임 허용이 필요하다 (MainActivity에서 요청).
 * 갤럭시 탭처럼 차가 아닌 기기엔 android.car 자체가 없으므로, Car 쪽 클래스는 start() 안에서만 만든다
 * (만들어 두기만 해도 클래스를 못 찾아 앱이 죽는다).
 */
class CarSpeedSource(private val context: Context, private val onSpeedKmh: (Float) -> Unit) {

    private var car: Car? = null
    private var manager: CarPropertyManager? = null
    private var callback: CarPropertyManager.CarPropertyEventCallback? = null

    fun start(onError: (Exception) -> Unit) {
        if (!available) {
            onError(IllegalStateException("이 기기엔 차량 속도(android.car)가 없음"))
            return
        }
        try {
            val cb = object : CarPropertyManager.CarPropertyEventCallback {
                override fun onChangeEvent(value: CarPropertyValue<*>) {
                    (value.value as? Float)?.let { onSpeedKmh(abs(it) * 3.6f) } // m/s → km/h
                }
                override fun onErrorEvent(propertyId: Int, areaId: Int) = Unit
            }
            callback = cb
            val c = Car.createCar(context.applicationContext)
            car = c
            val m = c.getCarManager(Car.PROPERTY_SERVICE) as CarPropertyManager
            manager = m
            val ok = m.registerCallback(cb, VehiclePropertyIds.PERF_VEHICLE_SPEED, CarPropertyManager.SENSOR_RATE_NORMAL)
            if (!ok) onError(IllegalStateException("속도 구독 거부됨"))
        } catch (e: Throwable) {
            onError(e as? Exception ?: RuntimeException(e))
        }
    }

    fun stop() {
        callback?.let { cb -> runCatching { manager?.unregisterCallback(cb) } }
        runCatching { car?.disconnect() }
        manager = null
        car = null
        callback = null
    }

    companion object {
        /** 이 기기에 차량 API가 있나 (Pleos·안드로이드 오토모티브만) */
        val available: Boolean by lazy { runCatching { Class.forName("android.car.Car") }.isSuccess }
    }
}
