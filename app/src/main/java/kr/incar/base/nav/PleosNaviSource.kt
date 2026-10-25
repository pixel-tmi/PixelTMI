package kr.incar.base.nav

import ai.pleos.playground.navi.constants.NaviErrorCode
import ai.pleos.playground.navi.constants.NavigationStatus
import ai.pleos.playground.navi.data.CurrentLocationInfo
import ai.pleos.playground.navi.data.DestinationArrivedInfo
import ai.pleos.playground.navi.data.DestinationInfo
import ai.pleos.playground.navi.data.RouteStartInfo
import ai.pleos.playground.navi.helper.NaviHelper
import ai.pleos.playground.navi.helper.listener.NaviHelperEventListener
import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kr.incar.base.tmi.NaviState

/**
 * 차량 기본 내비(NaviHelper)에서 현재 위치·주소와 목적지를 받는다.
 * 목적지가 있으면 "가는 길 TMI", 없으면 "내 주변 TMI".
 */
class PleosNaviSource(context: Context, private val scope: CoroutineScope) {

    private val navi = NaviHelper(context.applicationContext)
    private var poll: Job? = null

    private val _state = MutableStateFlow(NaviState())
    val state: StateFlow<NaviState> = _state.asStateFlow()

    /** 목적지에 도착한 순간 (경로는 바로 지워지므로 따로 알린다 → 주차 때 도착 세레모니) */
    val arrivals = kotlinx.coroutines.flow.MutableSharedFlow<String>(extraBufferCapacity = 1)

    private val listener = object : NaviHelperEventListener {
        override fun onCurrentLocationInfo(info: CurrentLocationInfo) {
            _state.update { it.copy(connected = true, address = info.address.ifBlank { it.address }) }
        }
        override fun onDestinationInfo(info: DestinationInfo) {
            _state.update {
                if (info.remainDistance > 0) it.copy(destinationName = info.name, remainM = info.remainDistance, remainSec = info.remainTime)
                else it.copy(destinationName = null, remainM = null, remainSec = null)
            }
        }
        override fun onRouteStarted(info: RouteStartInfo) = refresh()
        override fun onDestinationChanged() = refresh()
        override fun onRouteEnded() = clearRoute()
        override fun onRouteCancelled() = clearRoute()
        override fun onDestinationArrived(info: DestinationArrivedInfo) { arrivals.tryEmit(_state.value.destinationName ?: ""); clearRoute() }
        override fun onNavigationStatus(status: NavigationStatus) {
            if (status == NavigationStatus.FREE_DRIVE) clearRoute()
        }
        override fun onError(code: NaviErrorCode) {
            Log.w(TAG, "navi error $code")
        }
    }

    fun start() {
        runCatching {
            navi.initialize({
                navi.addListener(listener)
                _state.update { it.copy(connected = true) }
                refresh()
            }, { e -> Log.w(TAG, "navi init failed", e) })
        }.onFailure { Log.w(TAG, "navi init threw", it) }
        poll = scope.launch(Dispatchers.IO) {   // 내비 조회도 화면 줄 밖에서
            while (isActive) {
                // 길 안내 중엔 2초마다 (내비 모의 주행의 남은 거리를 부드럽게 따라가려고), 아니면 5초
                delay(if (_state.value.hasRoute) 2000 else 5000)
                refresh()
            }
        }
    }

    private fun refresh() {
        runCatching {
            navi.getCurrentLocationInfo()
            navi.getDestinationInfo()
        }
    }

    /** 말로 정한 목적지를 차량 내비(현대·기아)에 바로 넣는다 */
    fun routeTo(name: String, lat: Double, lng: Double): Boolean = runCatching {
        navi.requestRoute(ai.pleos.playground.navi.data.RouteInfo(lat, lng, null, null, name, "", "", "0",
            ai.pleos.playground.navi.constants.RouteOption.RECOMMENDED, "", false))
    }.onFailure { Log.w(TAG, "차량 내비 목적지 넣기 실패", it) }.isSuccess

    private fun clearRoute() = _state.update { it.copy(destinationName = null, remainM = null, remainSec = null) }

    fun stop() {
        poll?.cancel()
        runCatching { navi.removeListener(listener) }
        runCatching { navi.release() }
    }

    companion object {
        private const val TAG = "PleosNavi"
    }
}
