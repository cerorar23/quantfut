import 'package:gobet/forget_password/reset_password.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../sign_in/signup.dart';

class Forgot_password extends StatefulWidget {
  const Forgot_password({Key? key}) : super(key: key);

  @override
  _Forgot_passwordState createState() => _Forgot_passwordState();
}

class _Forgot_passwordState extends State<Forgot_password> {
  late ColorNotifire notifire;

  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return ScreenUtilInit(
      builder: (context, child) => Scaffold(
        backgroundColor: notifire.getprimerycolor,
        appBar: AppBar(
          backgroundColor: notifire.getlightblue,
          iconTheme: IconThemeData(color: Colors.white),
          centerTitle: true,
          title: const Text(
            "Forgot Password",
            style: TextStyle(
              fontFamily: 'Gilroy Medium',
              color: Color(0xfffffffd),
              fontSize: 18,
            ),
          ),
          actions: [
            const Icon(Icons.settings, color: Color(0xfffffffd)),
            SizedBox(width: 15),
          ],
        ),
        body: SingleChildScrollView(
          child: Column(
            children: [
              SizedBox(height: MediaQuery.of(context).size.height / 20),
              const Text(
                "Enter your email address and we will",
                style: TextStyle(
                  fontFamily: 'Gilroy Medium',
                  color: Color(0xffe0e1e4),
                ),
              ),
              const Text(
                "send you a link to reset your password.",
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
                  child: TextField(
                    style: TextStyle(color: Colors.white),
                    textAlign: TextAlign.left,
                    decoration: InputDecoration(
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(30),
                      ),
                      filled: true,
                      hintStyle: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        color: notifire.getgrey,
                        fontSize: 12.sp,
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderSide: const BorderSide(color: Color(0xff9733EE)),
                        borderRadius: BorderRadius.circular(30),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderSide: const BorderSide(color: Color(0xff9733EE)),
                        borderRadius: BorderRadius.circular(30),
                      ),
                      hintText: "Email or phone number",
                      fillColor: notifire.getprimerycolor,
                      prefixIcon: Padding(
                        padding: const EdgeInsets.all(15),
                        child: Image.asset(
                          "image/email.png",
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
                        child: Reset_password(),
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
                  Text(
                    "Don't have an account ? ",
                    style: TextStyle(color: notifire.getgrey),
                  ),
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
