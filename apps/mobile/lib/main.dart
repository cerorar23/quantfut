import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'onbonding_screen/splesh_screen.dart';
import 'product/live_widgets.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [ChangeNotifierProvider(create: (_) => ColorNotifire())],
      child: MaterialApp(
        theme: liveTheme(),
        home: Splesh_Screen(),
        debugShowCheckedModeBanner: false,
      ),
    ),
  );
}
