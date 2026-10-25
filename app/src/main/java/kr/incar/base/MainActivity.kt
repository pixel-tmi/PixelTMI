package kr.incar.base

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kr.incar.base.ui.DashboardScreen
import kr.incar.base.ui.InCarTheme
import kr.incar.base.ui.pixel.PixelScreen

class MainActivity : ComponentActivity() {

    /** 몸통은 앱 전체에 하나 (화면이 꺼져도 티미는 계속) */
    private val vm: AppGraph get() = (application as App).graph

    private val askPermissions = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
        if (result[SPEED_PERMISSION] == true) { vm.live.retrySpeed(); vm.setMode(Mode.LIVE) }
        if (result[Manifest.permission.ACCESS_FINE_LOCATION] == true) vm.live.retryGps()   // 갤럭시 탭 GPS 모드
        else if (result[Manifest.permission.ACCESS_COARSE_LOCATION] == true)
            android.widget.Toast.makeText(this, "정확한 위치를 켜 주세요 (속도·도착 판정에 필요해요)", android.widget.Toast.LENGTH_LONG).show()
        if (vm.tablet) { vm.openStage(); finish() }    // 탭: 허용이 끝나면 바로 Pleos 전용 앱 화면으로
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        (application as App).setOn(true)
        // 이 기기에 있는 권한만 묻는다 (갤럭시 탭엔 차량 속도 권한 자체가 없다)
        val missing = listOf(SPEED_PERMISSION, Manifest.permission.RECORD_AUDIO, Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION, "android.permission.POST_NOTIFICATIONS")
            .filter { runCatching { packageManager.getPermissionInfo(it, 0) }.isSuccess }
            .filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isNotEmpty()) askPermissions.launch(missing.toTypedArray())
        // 화면이 다시 만들어질 때(회전·크기 변경) 같은 명령이 또 실행되지 않게 처음 한 번만
        if (savedInstanceState == null) handle(intent)
        // TMI는 흘려들어도 되는 부가 정보 → 앱 화면은 띄우지 않고 티미만 메인 화면 위에 얹는다.
        // 패널은 티미 버튼을 길게 누를 때(panel=true)나 권한이 아직 없을 때만.
        val panel = intent.getBooleanExtra("panel", false) || missing.isNotEmpty() || !vm.pet.canShow()
        if (!panel) {
            // 탭: Pleos 전용 앱 화면을 열고 그 안에서만 펫을 띄운다 (앱 밖 탭 화면엔 안 뜬다). 차량: 다른 앱 위에.
            if (vm.tablet) vm.openStage() else vm.pet.show()
            finish()
            return
        }
        setContent {
            InCarTheme {
                val signals by vm.signalsScreen.collectAsStateWithLifecycle()
                if (signals) DashboardScreen(vm) else PixelScreen(vm)
            }
        }
    }

    /** 허용 화면에서 돌아왔을 때: 이제 띄울 수 있으면 펫을 띄우고 상주 서비스도 켠다 */
    override fun onResume() {
        super.onResume()
        if (vm.pet.canShow() && vm.pet.show()) kr.incar.base.pet.PetService.start(this)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handle(intent)
    }

    /**
     * 시연·테스트용 명령 (adb):
     *   am start -n kr.incar.base/.MainActivity --es say "1차로 포트홀"   ← 말한 것처럼 넣기
     *   am start -n kr.incar.base/.MainActivity --es demo commute          ← 출근길 시연 시작
     *   am start -n kr.incar.base/.MainActivity --es demo live             ← 실차 모드로
     *   am start -n kr.incar.base/.MainActivity --es pet on                ← 바탕화면 펫 켜기 (off = 끄기)
     *   am start -n kr.incar.base/.MainActivity --es mute on               ← 펫 소리 끄기 (off = 켜기)
     *   am start -n kr.incar.base/.MainActivity --es fx party              ← 도착 세레모니만 바로 (점검용, --el freeze 2000 = 2초 장면에서 멈춤, --es kind podium = 세레모니 종류 지정)
     *   am start -n kr.incar.base/.MainActivity --es char ufo              ← 캐릭터 바로 바꾸기 (점검용)
     *   --es act p_meat     ← 습성 동작 바로 (+ 고증 한 줄)       --es gear d|p     ← 가상 차 기어
     *   --es boost on|off   ← 과속 상황 켜기/끄기                 --es dest 잠실역  ← 목적지로 길안내 시작
     *   --es shop chars|records ← 캐릭터 고르기 / 내 기록 말풍선   (시연 영상 녹화용)
     */
    private fun handle(intent: Intent?) {
        intent ?: return
        DebugCommands.run(this, vm, intent)      // 녹화용 broadcast(DebugReceiver)와 같은 명령
        intent.removeExtra("say")
        intent.removeExtra("demo")
        intent.removeExtra("pet")
        intent.removeExtra("mute")
        intent.removeExtra("fx")
        intent.removeExtra("kind")
        intent.removeExtra("gear")
        intent.removeExtra("boost")
        intent.removeExtra("dest")
        intent.removeExtra("shop")
        intent.removeExtra("char")
        intent.removeExtra("act")
    }

    companion object {
        const val SPEED_PERMISSION = "android.car.permission.CAR_SPEED"
    }
}
