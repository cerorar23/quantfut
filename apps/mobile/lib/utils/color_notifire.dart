import 'package:gobet/utils/color.dart';
import 'package:flutter/cupertino.dart';

class ColorNotifire with ChangeNotifier {
  bool IsDark = false;
  set isDark(value) {
    IsDark = value;
  }

  get getprimerycolor => IsDark ? darkPrimeryColor : PrimeryColor;
  get getlightblue => IsDark ? darkblue : lightblue;
  get getmediumblue => IsDark ? darkmediumblue : mediumblue;
  get getwhite => IsDark ? darkwhite : white;
  get getlightgrey => IsDark ? darkgrey : lightgrey;
  get getgrey => IsDark ? darkg : grey;
}
