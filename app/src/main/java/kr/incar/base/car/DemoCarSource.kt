package kr.incar.base.car

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 시연 모드: 정해진 시나리오대로 차량 상태를 바꿔 가며 흘려준다.
 * 에뮬레이터 값이 마음대로 안 바뀌어도 PT·영상에서 같은 장면을 매번 재현할 수 있다.
 */
class DemoCarSource(private val scope: CoroutineScope) : CarSource {

    private val _state = MutableStateFlow(CarState())
    override val state: StateFlow<CarState> = _state.asStateFlow()

    private val _status = MutableStateFlow(SourceStatus(true, "시연 시나리오", "대기 중"))
    override val status: StateFlow<SourceStatus> = _status.asStateFlow()

    private val _step = MutableStateFlow<String?>(null)
    val currentStep: StateFlow<String?> = _step.asStateFlow()

    private val _playing = MutableStateFlow<Scenario?>(null)
    val playing: StateFlow<Scenario?> = _playing.asStateFlow()

    private var job: Job? = null

    override fun start() = Unit

    override fun stop() {
        job?.cancel()
        job = null
        _playing.value = null
        _step.value = null
        _status.value = SourceStatus(true, "시연 시나리오", "멈춤")
    }

    /** 스크립트형 시연: 차량 상태를 직접 바꿔 가며 진행한다 (Pixel TMI 출근길) */
    fun runScript(title: String, block: suspend DemoCarSource.() -> Unit) {
        stop()
        _status.value = SourceStatus(true, "시연 시나리오", title)
        job = scope.launch {
            block()
            _status.value = SourceStatus(true, "시연 시나리오", "$title · 끝")
        }
    }

    fun set(s: CarState) { _state.value = s }
    fun update(change: (CarState) -> CarState) { _state.value = change(_state.value) }
    fun step(label: String) { _step.value = label }

    /** 속도를 부드럽게 바꾼다 (0.25초 간격) */
    suspend fun rampTo(kmh: Float, overMs: Long) {
        val ticks = (overMs / 250).coerceAtLeast(1)
        for (i in 1..ticks) {
            val cur = _state.value.speedKmh ?: 0f
            update { it.copy(speedKmh = cur + (kmh - cur) / (ticks - i + 1)) }
            kotlinx.coroutines.delay(250)
        }
    }

    fun play(scenario: Scenario) {
        stop()
        _playing.value = scenario
        _state.value = scenario.initial
        job = scope.launch {
            for ((index, step) in scenario.steps.withIndex()) {
                delay(step.afterMs)
                _state.value = step.change(_state.value)
                if (step.label.isNotBlank()) _step.value = step.label
                _status.value = SourceStatus(true, "시연 시나리오", "${scenario.title} · ${index + 1}/${scenario.steps.size}")
            }
            _status.value = SourceStatus(true, "시연 시나리오", "${scenario.title} · 끝")
            _playing.value = null
        }
    }
}
