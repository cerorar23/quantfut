import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../sign_in/signup.dart';
import 'create_account.dart';

class Reset_password extends StatefulWidget {
  const Reset_password({Key? key}) : super(key: key);

  @override
  _Reset_passwordState createState() => _Reset_passwordState();
}

class _Reset_passwordState extends State<Reset_password> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return ScreenUtilInit(
      builder: (context, child) => Scaffold(
        backgroundColor: notifire.getprimerycolor,
        body: SingleChildScrollView(
          child: Column(
            children: [
              SizedBox(height: MediaQuery.of(context).size.height / 25),
              Row(
                children: [
                  SizedBox(width: MediaQuery.of(context).size.width / 40),
                  GestureDetector(
                    onTap: () {
                      Navigator.pop(context);
                    },
                    child: const Icon(
                      Icons.arrow_back_sharp,
                      color: Color(0xfffffffd),
                    ),
                  ),
                  const Spacer(),
                  const Text(
                    "Reset Password",
                    style: TextStyle(
                      fontFamily: 'Gilroy Medium',
                      color: Color(0xfffffffd),
                    ),
                  ),
                  const Spacer(),
                ],
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 20),
              const Text(
                "Check your email or phone number",
                style: TextStyle(
                  fontFamily: 'Gilroy Medium',
                  color: Color(0xffe0e1e4),
                ),
              ),
              const Text(
                "to retrieve your password.",
                style: TextStyle(
                  fontFamily: 'Gilroy Medium',
                  color: Color(0xffe0e1e4),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 20),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 30),
                child: Container(
                  color: Colors.transparent,
                  height: MediaQuery.of(context).size.height / 17,
                  width: MediaQuery.of(context).size.width / 1.1,
                  child: TextField(
                    style: TextStyle(color: notifire.getwhite),
                    textAlign: TextAlign.left,
                    decoration: InputDecoration(
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(30),
                        borderSide: const BorderSide(
                          width: 0,
                          style: BorderStyle.none,
                        ),
                      ),
                      fillColor: notifire.getlightblue,
                      hintStyle: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        color: notifire.getgrey,
                        fontSize: 12.sp,
                      ),
                      hintText: "New Password",
                      filled: true,
                      prefixIcon: Padding(
                        padding: const EdgeInsets.all(12.0),
                        child: Image.asset(
                          "image/password.png",
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 30),
                child: Container(
                  color: Colors.transparent,
                  height: MediaQuery.of(context).size.height / 17,
                  width: MediaQuery.of(context).size.width / 1.1,
                  child: TextField(
                    style: const TextStyle(color: Colors.white),
                    textAlign: TextAlign.left,
                    decoration: InputDecoration(
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(30),
                        borderSide: const BorderSide(
                          width: 0,
                          style: BorderStyle.none,
                        ),
                      ),
                      fillColor: notifire.getlightblue,
                      hintStyle: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        color: notifire.getgrey,
                        fontSize: 12.sp,
                      ),
                      hintText: "Confirm new password",
                      filled: true,
                      suffixIcon: const Icon(
                        Icons.remove_red_eye_outlined,
                        color: Color(0xffafb9cf),
                        size: 20,
                      ),
                      prefixIcon: Padding(
                        padding: const EdgeInsets.all(12.0),
                        child: Image.asset(
                          "image/password.png",
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 30),
                child: GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context,
                      PageTransition(
                        type: PageTransitionType.fade,
                        child: Create_accout(),
                      ),
                    );
                  },
                  child: Container(
                    height: MediaQuery.of(context).size.height / 17,
                    decoration: const BoxDecoration(
                      borderRadius: BorderRadius.all(Radius.circular(20)),
                      gradient: LinearGradient(
                        begin: Alignment.centerLeft,
                        end: Alignment.centerRight,
                        colors: [
                          Color(0xffDA22FF),
                          Color(0xff9733EE),
                          Color(0xffDA22FF),
                        ],
                      ),
                    ),
                    child: Center(
                      child: Text(
                        "Reset Password",
                        style: TextStyle(
                          color: const Color(0xffe2e3e9),
                          fontFamily: 'Gilroy Medium',
                          fontSize: 15.sp,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 1.8),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  GestureDetector(
                    onTap: () {
                      Navigator.push(
                        context,
                        PageTransition(
                          type: PageTransitionType.fade,
                          child: Sign_up(),
                        ),
                      );
                    },
                    child: Container(
                      height: MediaQuery.of(context).size.height / 30,
                      decoration: const BoxDecoration(
                        color: Colors.transparent,
                        border: Border(
                          bottom: BorderSide(
                            color: Color(0xff50579c),
                            width: 1,
                          ),
                        ),
                      ),
                      child: Center(
                        child: Text(
                          "Sign Up",
                          style: TextStyle(
                            fontFamily: 'Gilroy Medium',
                            color: const Color(0xff50579c),
                            fontSize: 12.sp,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
