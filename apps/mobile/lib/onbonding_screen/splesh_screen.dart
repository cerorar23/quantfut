import 'dart:async';

import 'package:flutter/material.dart';

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
  Widget build(BuildContext context) => const Scaffold(
    backgroundColor: Color(0xff090f1a),
    body: SafeArea(
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Q.',
              style: TextStyle(
                color: Color(0xff00d58b),
                fontFamily: 'Gilroy ExtraBold',
                fontSize: 90,
              ),
            ),
            SizedBox(height: 12),
            Text(
              'QuantFut',
              style: TextStyle(
                color: Colors.white,
                fontFamily: 'Gilroy Bold',
                fontSize: 28,
              ),
            ),
            SizedBox(height: 16),
            Text(
              'FÚTBOL · NBA · ESTADÍSTICA',
              style: TextStyle(
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
