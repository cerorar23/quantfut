import 'dart:async';

import 'package:clock/clock.dart';
import 'package:flutter/material.dart';

/// Counts down to an absolute deadline, so delayed ticks do not accumulate drift.
class CountdownTimer extends StatefulWidget {
  const CountdownTimer({
    super.key,
    required this.endTime,
    this.onEnd,
    this.textStyle,
  });

  final int endTime;
  final VoidCallback? onEnd;
  final TextStyle? textStyle;

  @override
  State<CountdownTimer> createState() => _CountdownTimerState();
}

class _CountdownTimerState extends State<CountdownTimer>
    with WidgetsBindingObserver {
  Timer? _timer;
  int _seconds = 0;
  bool _ended = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _start();
  }

  @override
  void didUpdateWidget(CountdownTimer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.endTime != widget.endTime) {
      _start();
    }
  }

  void _start() {
    _timer?.cancel();
    _ended = false;
    _seconds = _remainingSeconds();
    if (_seconds > 0) {
      _timer = Timer.periodic(const Duration(seconds: 1), (_) => _tick());
    } else {
      // Notify after the initial build, not while the parent is building.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && _remainingSeconds() == 0) _finish();
      });
    }
  }

  int _remainingSeconds() {
    final milliseconds = widget.endTime - clock.now().millisecondsSinceEpoch;
    return milliseconds <= 0 ? 0 : (milliseconds / 1000).ceil();
  }

  void _tick() {
    final seconds = _remainingSeconds();
    if (seconds != _seconds) {
      setState(() => _seconds = seconds);
    }
    if (seconds == 0) _finish();
  }

  void _finish() {
    _timer?.cancel();
    if (_ended) return;
    _ended = true;
    widget.onEnd?.call();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _tick();
  }

  @override
  void dispose() {
    _timer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final days = _seconds ~/ Duration.secondsPerDay;
    final hours = (_seconds ~/ Duration.secondsPerHour) % Duration.hoursPerDay;
    final minutes = (_seconds ~/ Duration.secondsPerMinute) % 60;
    final seconds = _seconds % 60;
    String pad(int value) => value.toString().padLeft(2, '0');
    final time = '${pad(hours)}:${pad(minutes)}:${pad(seconds)}';
    return Text(days > 0 ? '${days}d $time' : time, style: widget.textStyle);
  }
}
