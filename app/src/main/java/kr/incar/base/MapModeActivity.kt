package kr.incar.base

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.Settings

/**
 * 탭 아이콘 'TMI 지도' — 고른 길안내 앱(네이버 지도·카카오맵·티맵)을 열고,
 * 그 지도 앱이 맨 앞에 있을 때만 캐릭터가 지도 위로 따라 나온다 (홈·다른 앱에선 숨음).
 * 끄기: 캐릭터 톱니 > ■ 종료, 또는 알림창 '끄기 (완전히)' → 소리까지 완전히 꺼진다.
 * 필요한 허용(다른 앱 위 표시 · 사용 정보 접근 · 마이크·위치·알림)이 없으면 한국어로 안내하고 설정 화면으로 보낸다.
 */
class MapModeActivity : Activity() {

    private val vm: AppGraph get() = (application as App).graph
    private var asked = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        (application as App).setOn(true)
    }

    override fun onResume() {
        super.onResume()
        // 1) 그 자리에서 물을 수 있는 허용 (마이크·위치·알림) — 한 번만 묻고 결과와 상관없이 다음으로
        val runtime = listOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION, "android.permission.POST_NOTIFICATIONS")
            .filter { runCatching { packageManager.getPermissionInfo(it, 0) }.isSuccess }
            .filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (runtime.isNotEmpty() && !asked) {
            asked = true
            requestPermissions(runtime.toTypedArray(), 1)
            return
        }
        // 2) 설정 화면에서만 켤 수 있는 허용
        when {
            !Settings.canDrawOverlays(this) -> guide(
                "지도 위에 캐릭터를 띄우려면\n'다른 앱 위에 표시'를 허용해 주세요.",
                Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")),
            )
            !kr.incar.base.nav.ForegroundWatcher(this).granted() -> guide(
                "지도 앱이 앞에 있을 때만 캐릭터를 보이려면\n'사용 정보 접근'에서 Pixel TMI를 허용해 주세요.\n(홈 화면에선 숨기기 위해 필요해요)",
                Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS),
            )
            else -> { vm.startMapMode(); finish() }
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) vm.live.retryGps()
    }

    private var dialog: AlertDialog? = null

    private fun guide(msg: String, settings: Intent) {
        if (dialog?.isShowing == true) return
        dialog = AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
            .setTitle("허용이 필요해요")
            .setMessage(msg)
            .setPositiveButton("설정 열기") { _, _ -> runCatching { startActivity(settings) } }
            .setNegativeButton("취소") { _, _ -> (application as App).setOn(false); finish() }
            .setCancelable(false)
            .show()
    }
}
