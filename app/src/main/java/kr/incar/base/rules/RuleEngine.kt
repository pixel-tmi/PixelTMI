package kr.incar.base.rules

import kr.incar.base.car.CarState
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch

/**
 * "이런 상황이 되면 → 이렇게 안내한다" 한 줄.
 * 조건이 거짓에서 참으로 바뀌는 순간에만 한 번 울리고, cooldown 동안은 다시 울리지 않는다.
 */
data class Rule(
    val id: String,
    val title: String,
    val cooldownMs: Long = 60_000,
    val condition: (CarState) -> Boolean,
    val message: (CarState) -> String,
)

data class AssistantEvent(
    val atMillis: Long,
    val ruleId: String,
    val title: String,
    val message: String,
)

class RuleEngine(private val rules: List<Rule>, private val now: () -> Long = System::currentTimeMillis) {

    private val _events = MutableSharedFlow<AssistantEvent>(extraBufferCapacity = 32)
    val events: SharedFlow<AssistantEvent> = _events.asSharedFlow()

    private val wasTrue = mutableMapOf<String, Boolean>()
    private val lastFired = mutableMapOf<String, Long>()

    fun attach(scope: CoroutineScope, states: Flow<CarState>) {
        scope.launch { states.collect(::evaluate) }
    }

    /** 시나리오를 처음부터 다시 틀 때 기억을 지운다. */
    fun reset() {
        wasTrue.clear()
        lastFired.clear()
    }

    fun evaluate(state: CarState) {
        for (rule in rules) {
            val isTrue = runCatching { rule.condition(state) }.getOrDefault(false)
            val risingEdge = isTrue && wasTrue[rule.id] != true
            wasTrue[rule.id] = isTrue
            if (!risingEdge) continue
            val t = now()
            val last = lastFired[rule.id]
            if (last != null && t - last < rule.cooldownMs) continue
            lastFired[rule.id] = t
            _events.tryEmit(AssistantEvent(t, rule.id, rule.title, rule.message(state)))
        }
    }
}
