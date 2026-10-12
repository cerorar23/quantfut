import 'dart:async';

import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'second_screen.dart';

class Splesh_Screen extends StatefulWidget {
  const Splesh_Screen({super.key});
  @override
  State<Splesh_Screen> createState() => _Splesh_ScreenState();
}

class _Splesh_ScreenState extends State<Splesh_Screen> {
  Timer? _navigationTimer;
  @override
  void initState() {
    super.initState();
    _navigationTimer = Timer(const Duration(seconds: 4), () {
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(builder: (_) => const SecondScreen()),
      );
    });
  }

  @override
  void dispose() {
    _navigationTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: const Color(0xff090f1a),
    body: SafeArea(
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Q.',
              style: TextStyle(
                color: Color(0xff00d58b),
                fontFamily: 'Gilroy ExtraBold',
                fontSize: 90,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'QuantFut',
              style: TextStyle(
                color: Colors.white,
                fontFamily: 'Gilroy Bold',
                fontSize: 28,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              context.l10n.splashTagline,
              style: const TextStyle(
                color: Color(0xffa0adbd),
                fontSize: 10,
                letterSpacing: 1.4,
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
