import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/firebase_startup.dart';
import 'core/firebase_services.dart';
import 'core/firebase_access.dart';
import 'onbonding_screen/splesh_screen.dart';
import 'product/live_widgets.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  const app = QuantFutApp();
  runApp(firebaseEnabled ? const FirebaseStartup(child: app) : app);
}

class QuantFutApp extends StatelessWidget {
  const QuantFutApp({super.key});

  @override
  Widget build(BuildContext context) => MultiProvider(
    providers: [ChangeNotifierProvider(create: (_) => ColorNotifire())],
    child: MaterialApp(
      theme: liveTheme(),
      home: FirebaseServices.current == null
          ? Splesh_Screen()
          : const FirebaseAccountGate(),
      debugShowCheckedModeBanner: false,
    ),
  );
}
