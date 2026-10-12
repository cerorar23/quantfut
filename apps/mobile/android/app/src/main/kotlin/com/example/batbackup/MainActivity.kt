package com.example.gobet

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import android.content.Intent
import android.net.Uri

class MainActivity: FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "quantfut/offers").setMethodCallHandler { call, result ->
            if (call.method != "open") { result.notImplemented() } else {
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
