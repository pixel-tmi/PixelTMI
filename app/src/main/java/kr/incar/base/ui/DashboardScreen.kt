package kr.incar.base.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kr.incar.base.AppViewModel
import kr.incar.base.Mode
import kr.incar.base.car.CarState
import kr.incar.base.car.Gear
import kr.incar.base.car.Scenarios
import kr.incar.base.rules.AssistantEvent
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun DashboardScreen(vm: AppViewModel) {
    val state by vm.state.collectAsStateWithLifecycle()
    val status by vm.status.collectAsStateWithLifecycle()
    val mode by vm.mode.collectAsStateWithLifecycle()
    val events by vm.events.collectAsStateWithLifecycle()
    val voiceStatus by vm.voice.status.collectAsStateWithLifecycle()
    val voiceLatency by vm.voice.lastLatencyMs.collectAsStateWithLifecycle()
    val step by vm.demo.currentStep.collectAsStateWithLifecycle()
    val playing by vm.demo.playing.collectAsStateWithLifecycle()
    val signals by vm.live.signals.collectAsStateWithLifecycle()

    Column(
        Modifier
            .fillMaxSize()
            .background(C.bg)
            .padding(24.dp)
    ) {
        // 상단 바
        Row(verticalAlignment = Alignment.CenterVertically) {
            Pill("← Pixel TMI", selected = true) { vm.showSignals(false) }
            Spacer(Modifier.width(16.dp))
            Text("차량 신호", color = C.text, fontSize = 30.sp, fontWeight = FontWeight.Black)
            Spacer(Modifier.width(24.dp))
            Mode.entries.forEach { m ->
                Pill(m.label, selected = m == mode) { vm.setMode(m) }
                Spacer(Modifier.width(10.dp))
            }
            Spacer(Modifier.weight(1f))
            Dot(if (status.connected) C.ok else C.bad)
            Spacer(Modifier.width(10.dp))
            Column {
                Text(status.label, color = C.text, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                if (status.detail.isNotBlank()) {
                    Text(status.detail, color = C.textSub, fontSize = 15.sp, fontWeight = FontWeight.SemiBold, maxLines = 1)
                }
            }
            Spacer(Modifier.width(24.dp))
            Column(horizontalAlignment = Alignment.End) {
                Text(voiceStatus, color = C.text, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                Text(
                    "음성 지연 " + (voiceLatency?.let { "${it}ms" } ?: "-"),
                    color = C.textSub, fontSize = 15.sp, fontWeight = FontWeight.SemiBold
                )
            }
            Spacer(Modifier.width(12.dp))
            Pill("말해 보기", selected = false) { vm.testVoice() }
        }

        Spacer(Modifier.height(20.dp))

        Row(Modifier.weight(1f)) {
            // 왼쪽: 차량 상태
            Column(Modifier.weight(0.6f).fillMaxHeight()) {
                Hero(state)
                Spacer(Modifier.height(16.dp))
                LazyVerticalGrid(
                    columns = GridCells.Adaptive(210.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.weight(1f),
                ) {
                    items(tiles(state)) { Tile(it) }
                }
            }

            Spacer(Modifier.width(20.dp))

            // 오른쪽: 코파일럿 안내 + 시나리오
            Column(Modifier.weight(0.4f).fillMaxHeight()) {
                Panel(Modifier.weight(1f)) {
                    Text("코파일럿 안내", color = C.text, fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
                    Spacer(Modifier.height(12.dp))
                    if (events.isEmpty()) {
                        Text("상황이 생기면 여기에 안내가 쌓입니다.", color = C.textSub, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                    }
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        items(events, key = { it.atMillis.toString() + it.ruleId }) { EventRow(it, first = it == events.first()) }
                    }
                }
                if (mode == Mode.LIVE) {
                    Spacer(Modifier.height(16.dp))
                    Panel(Modifier.weight(1f)) {
                        Text("신호 점검", color = C.text, fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
                        Spacer(Modifier.height(8.dp))
                        LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            items(signals.values.sortedBy { if (it.count > 0) 0 else if (it.error != null) 2 else 1 }, key = { it.name }) { s ->
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Dot(if (s.count > 0) C.ok else if (s.error != null) C.bad else C.warn)
                                    Spacer(Modifier.width(10.dp))
                                    Text(s.name, color = C.text, fontSize = 17.sp, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                                    Text(
                                        when {
                                            s.count > 0 -> "${s.count}회" + (s.gapMs?.let { " · ${it}ms" } ?: "")
                                            s.error != null -> "안 됨"
                                            else -> "값 없음"
                                        },
                                        color = C.textSub, fontSize = 16.sp, fontWeight = FontWeight.SemiBold,
                                    )
                                }
                            }
                        }
                    }
                }
                Spacer(Modifier.height(16.dp))
                Panel {
                    Text("시연 시나리오", color = C.text, fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
                    Spacer(Modifier.height(10.dp))
                    Scenarios.all.forEach { sc ->
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(12.dp))
                                .background(if (playing == sc) C.accent.copy(alpha = 0.18f) else C.panelHi)
                                .clickable { vm.play(sc) }
                                .padding(horizontal = 16.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text("▶", color = C.accent, fontSize = 20.sp, fontWeight = FontWeight.Black)
                            Spacer(Modifier.width(12.dp))
                            Column(Modifier.weight(1f)) {
                                Text(sc.title, color = C.text, fontSize = 19.sp, fontWeight = FontWeight.Bold)
                                Text(sc.summary, color = C.textSub, fontSize = 15.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            }
                        }
                        Spacer(Modifier.height(8.dp))
                    }
                    if (playing != null) {
                        Pill("멈춤", selected = false) { vm.stopScenario() }
                    }
                }
            }
        }

        // 하단 자막: 영상 촬영 때 지금 장면과 마지막 안내를 크게 보여준다
        Spacer(Modifier.height(16.dp))
        Row(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(C.panel)
                .padding(horizontal = 20.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (mode == Mode.DEMO && step != null) {
                Text(step!!, color = C.accent, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
                Spacer(Modifier.width(20.dp))
            }
            Text(
                events.firstOrNull()?.message ?: "",
                color = C.text, fontSize = 24.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis
            )
        }
    }
}

@Composable
private fun Hero(s: CarState) {
    Panel {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column {
                Text("속도", color = C.textSub, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(s.speedKmh?.toInt()?.toString() ?: "–", color = C.text, fontSize = 88.sp, fontWeight = FontWeight.Black)
                    Spacer(Modifier.width(8.dp))
                    Text("km/h", color = C.textSub, fontSize = 24.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 18.dp))
                }
            }
            Spacer(Modifier.weight(1f))
            Gear.entries.forEach { g ->
                val on = s.gear == g
                Box(
                    Modifier
                        .padding(horizontal = 6.dp)
                        .size(64.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .background(if (on) C.accent else C.panelHi),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(g.label, color = if (on) Color.White else C.textSub, fontSize = 30.sp, fontWeight = FontWeight.Black)
                }
            }
        }
    }
}

private enum class Tone { NORMAL, GOOD, WARN, BAD }

private data class TileData(val label: String, val value: String, val tone: Tone = Tone.NORMAL)

private fun onOff(v: Boolean?, on: String = "켜짐", off: String = "꺼짐") = when (v) { null -> "–"; true -> on; false -> off }

private fun tiles(s: CarState): List<TileData> = listOf(
    TileData("연료", s.fuelPercent?.let { "${it.toInt()}%" } ?: "–", if ((s.fuelPercent ?: 100f) < 15f) Tone.BAD else Tone.NORMAL),
    TileData("주행가능거리", s.fuelRangeKm?.let { "${it.toInt()} km" } ?: s.evRangeKm?.let { "${it.toInt()} km" } ?: "–"),
    TileData("배터리", s.evSocPercent?.let { "${it.toInt()}%" } ?: "–"),
    TileData("총 주행거리", s.odometerKm?.let { "%,d km".format(it.toInt()) } ?: "–"),
    TileData("이번 주행", s.tripKm?.let { "%.1f km".format(it) } ?: "–"),
    TileData("안전벨트", onOff(s.driverBeltFastened, "착용", "미착용"), if (s.driverBeltFastened == false && s.moving) Tone.BAD else Tone.NORMAL),
    TileData("문", onOff(s.anyDoorOpen, "열림", "닫힘"), if (s.anyDoorOpen == true) Tone.WARN else Tone.NORMAL),
    TileData("잠금", onOff(s.doorsLocked, "잠김", "풀림")),
    TileData("운전석 창문", s.driverWindowPercent?.let { if (it == 0) "닫힘" else "${it}% 열림" } ?: "–", if ((s.driverWindowPercent ?: 0) > 0) Tone.WARN else Tone.NORMAL),
    TileData("실내 온도", s.cabinTempC?.let { "%.1f°C".format(it) } ?: "–"),
    TileData("바깥 온도", s.outsideTempC?.let { "%.1f°C".format(it) } ?: "–"),
    TileData("공조", onOff(s.hvacOn)),
    TileData("전조등", onOff(s.headlightsOn)),
    TileData("와이퍼", onOff(s.wiperOn, "작동", "멈춤")),
    TileData("방향지시등", s.turnSignal?.label ?: "–"),
    TileData("주행 모드", s.driveMode ?: "–"),
    TileData("크루즈", onOff(s.cruiseOn)),
    TileData("주차 브레이크", onOff(s.parkingBrakeOn, "걸림", "풀림")),
    TileData("핸들 각도", s.steeringAngleDeg?.let { "${it.toInt()}°" } ?: "–"),
)

@Composable
private fun Tile(t: TileData) {
    val edge = when (t.tone) { Tone.BAD -> C.bad; Tone.WARN -> C.warn; Tone.GOOD -> C.ok; Tone.NORMAL -> C.line }
    Column(
        Modifier
            .clip(RoundedCornerShape(14.dp))
            .background(C.panel)
            .border(2.dp, edge, RoundedCornerShape(14.dp))
            .padding(horizontal = 16.dp, vertical = 14.dp)
    ) {
        Text(t.label, color = C.textSub, fontSize = 16.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(4.dp))
        Text(
            t.value,
            color = if (t.value == "–") C.textSub else C.text,
            fontSize = 26.sp, fontWeight = FontWeight.ExtraBold, maxLines = 1
        )
    }
}

private val timeFmt = SimpleDateFormat("HH:mm:ss", Locale.KOREA)

@Composable
private fun EventRow(e: AssistantEvent, first: Boolean) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(if (first) C.accent.copy(alpha = 0.16f) else C.panelHi)
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        Row {
            Text(e.title, color = C.accent, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
            Spacer(Modifier.weight(1f))
            Text(timeFmt.format(Date(e.atMillis)), color = C.textSub, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
        }
        Spacer(Modifier.height(4.dp))
        Text(e.message, color = C.text, fontSize = if (first) 21.sp else 18.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun Panel(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Column(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(C.panel)
            .padding(20.dp)
    ) { content() }
}

@Composable
private fun Pill(label: String, selected: Boolean, onClick: () -> Unit) {
    Box(
        Modifier
            .clip(RoundedCornerShape(50))
            .background(if (selected) C.accent else C.panelHi)
            .clickable(onClick = onClick)
            .padding(horizontal = 20.dp, vertical = 12.dp)
    ) {
        Text(label, color = if (selected) Color.White else C.text, fontSize = 18.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun Dot(color: Color) {
    Box(Modifier.size(14.dp).clip(CircleShape).background(color))
}
