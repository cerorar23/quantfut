package com.saptain.quantfut

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import android.content.Intent
import android.net.Uri
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import android.os.Bundle
import com.tapjoy.TJActionRequest
import com.tapjoy.TJConnectListener
import com.tapjoy.TJError
import com.tapjoy.TJPlacement
import com.tapjoy.TJPlacementListener
import com.tapjoy.Tapjoy
import com.tapjoy.TapjoyConnectFlag
import java.util.Hashtable

class MainActivity: FlutterActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getSystemService(NotificationManager::class.java).createNotificationChannel(
                NotificationChannel("quantfut_predictions", "Avisos de QuantFut", NotificationManager.IMPORTANCE_DEFAULT)
            )
        }
    }
    // El user_id (uid del monedero) llega al servidor como `snuid` en el callback S2S;
    // debe fijarse en el connect, antes de pedir cualquier placement.
    private fun openTapjoy(sdkKey: String, userId: String, placementName: String, result: MethodChannel.Result) {
        if (sdkKey.isEmpty() || userId.isEmpty() || placementName.isEmpty()) {
            result.error("tapjoy_config", "Tapjoy sin configurar", null); return
        }
        var answered = false
        fun reply(error: String?) {
            if (answered) return
            answered = true
            if (error == null) result.success(true) else result.error("tapjoy", error, null)
        }
        fun request() {
            val placement = Tapjoy.getPlacement(placementName, object : TJPlacementListener {
                override fun onRequestSuccess(p: TJPlacement) {
                    if (!p.isContentAvailable) reply("No hay ofertas disponibles ahora")
                }
                override fun onRequestFailure(p: TJPlacement, e: TJError) { reply(e.message) }
                override fun onContentReady(p: TJPlacement) { p.showContent(); reply(null) }
                override fun onContentShow(p: TJPlacement) {}
                override fun onContentDismiss(p: TJPlacement) {}
                override fun onPurchaseRequest(p: TJPlacement, r: TJActionRequest, productId: String) {}
                override fun onRewardRequest(p: TJPlacement, r: TJActionRequest, itemId: String, quantity: Int) {}
                override fun onClick(p: TJPlacement) {}
            })
            placement.requestContent()
        }
        if (Tapjoy.isConnected()) { request(); return }
        val flags = Hashtable<String, Any>()
        flags[TapjoyConnectFlag.USER_ID] = userId
        Tapjoy.connect(applicationContext, sdkKey, flags, object : TJConnectListener() {
            override fun onConnectSuccess() { request() }
            override fun onConnectWarning(code: Int, message: String?) {}
            override fun onConnectFailure(code: Int, message: String?) { reply(message ?: "Sin conexión con Tapjoy") }
        })
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "quantfut/offers").setMethodCallHandler { call, result ->
            if (call.method == "tapjoy") {
                openTapjoy(call.argument("sdk_key") ?: "", call.argument("user_id") ?: "",
                    call.argument("placement") ?: "", result)
            } else if (call.method != "open") { result.notImplemented() } else {
                val uri = Uri.parse(call.argument<String>("url") ?: "")
                if (uri.scheme != "https" || uri.host !in setOf("wall.revenueuniverse.com", "web.bitlabs.ai")) {
                    result.error("invalid_url", "Proveedor no autorizado", null)
                } else {
                    try { startActivity(Intent(Intent.ACTION_VIEW, uri)); result.success(true) }
                    catch (e: Exception) { result.error("no_browser", "No se pudo abrir el navegador", null) }
                }
            }
        }
    }
}
