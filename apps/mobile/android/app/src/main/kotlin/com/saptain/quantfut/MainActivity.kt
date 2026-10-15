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
import android.os.Handler
import android.os.Looper
import com.google.android.gms.ads.identifier.AdvertisingIdClient
import com.tapjoy.TJActionRequest
import com.tapjoy.TJConnectListener
import com.tapjoy.TJError
import com.tapjoy.TJPlacement
import com.tapjoy.TJPlacementListener
import com.tapjoy.Tapjoy
import com.tapjoy.TapjoyConnectFlag
import java.util.Hashtable

class MainActivity: FlutterActivity() {
    private var offerInFlight = false
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
            result.error("tapjoy_config", null, null); return
        }
        if (offerInFlight) {
            result.error("tapjoy_busy", null, null); return
        }
        offerInFlight = true
        var answered = false
        val handler = Handler(Looper.getMainLooper())
        lateinit var timeout: Runnable
        // Los errores del SDK pueden contener el HTML completo de una respuesta.
        // Solo cruzan el canal códigos, nunca cuerpos ni URLs del proveedor.
        fun reply(error: String?, sdkCode: Int? = null) {
            handler.post {
                if (!answered) {
                    answered = true
                    offerInFlight = false
                    handler.removeCallbacks(timeout)
                    if (error == null) result.success(true)
                    else result.error(error, null, sdkCode?.let { mapOf("sdk_code" to it) })
                }
            }
        }
        timeout = Runnable { reply("tapjoy_timeout") }
        handler.postDelayed(timeout, 45000)
        fun request() {
            if (answered) return
            val placement = Tapjoy.getPlacement(placementName, object : TJPlacementListener {
                override fun onRequestSuccess(p: TJPlacement) {
                    if (!p.isContentAvailable) reply("tapjoy_unavailable")
                }
                override fun onRequestFailure(p: TJPlacement, e: TJError) { reply("tapjoy_request", e.code) }
                override fun onContentReady(p: TJPlacement) {
                    handler.post {
                        if (!answered) {
                            try { p.showContent() }
                            catch (e: Exception) { reply("tapjoy_request") }
                        }
                    }
                }
                override fun onContentShow(p: TJPlacement) { reply(null) }
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
        Tapjoy.connect(this, sdkKey, flags, object : TJConnectListener() {
            override fun onConnectSuccess() { request() }
            override fun onConnectWarning(code: Int, message: String?) {}
            override fun onConnectFailure(code: Int, message: String?) { reply("tapjoy_connect", code) }
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
        // ID de publicidad para Meta (madid). Nunca en el hilo principal. Si la persona limito o
        // borro el ID en los ajustes del telefono, no se devuelve (politica de Google Play).
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "quantfut/device").setMethodCallHandler { call, result ->
            if (call.method != "advertising") { result.notImplemented(); return@setMethodCallHandler }
            Thread {
                val info = try { AdvertisingIdClient.getAdvertisingIdInfo(applicationContext) } catch (e: Exception) { null }
                val limited = info?.isLimitAdTrackingEnabled ?: true
                val id = info?.id?.takeIf { !limited && it != "00000000-0000-0000-0000-000000000000" }
                runOnUiThread {
                    result.success(mapOf("id" to id, "limited" to limited,
                        "model" to Build.MODEL, "os" to Build.VERSION.RELEASE))
                }
            }.start()
        }
    }
}
