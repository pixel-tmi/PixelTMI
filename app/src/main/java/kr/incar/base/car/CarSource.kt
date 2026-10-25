package kr.incar.base.car

import kotlinx.coroutines.flow.StateFlow

/** 차량 상태를 흘려주는 곳. 실제 Pleos 차량과 시연 시나리오가 같은 모양을 따른다. */
interface CarSource {
    val state: StateFlow<CarState>
    val status: StateFlow<SourceStatus>
    fun start()
    fun stop()
}

data class SourceStatus(
    val connected: Boolean,
    val label: String,
    val detail: String = "",
)
