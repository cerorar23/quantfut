import 'package:gobet/forget_password/forgot_password.dart';
import 'package:gobet/forget_password/profile/profile_settings/user_profile_setting/term_policy/term_use.dart';
import 'package:gobet/sign_in/signup.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

class Log_in extends StatefulWidget {
  const Log_in({Key? key}) : super(key: key);

  @override
  _Log_inState createState() => _Log_inState();
}

class _Log_inState extends State<Log_in> {
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
        ),
        body: SingleChildScrollView(
          child: Column(
            children: [
              Stack(
                children: [
                  Center(
                    child: Image.asset(
                      "image/backphoto.png",
                      height: MediaQuery.of(context).size.height / 3,
                    ),
                  ),
                  Column(
                    children: [
                      SizedBox(height: MediaQuery.of(context).size.height / 20),
                      Stack(
                        children: [
                          Center(
                            child: Image.asset(
                              "image/award.png",
                              height: MediaQuery.of(context).size.height / 4,
                            ),
                          ),
                          Column(
                            children: [
                              SizedBox(
                                height: MediaQuery.of(context).size.height / 15,
                              ),
                              Center(
                                child: Image.asset(
                                  "image/circulimage.png",
                                  height:
                                      MediaQuery.of(context).size.height / 25,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ],
                  ),
                ],
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
                      hintText: "Email",
                      filled: true,
                      prefixIcon: Padding(
                        padding: const EdgeInsets.all(15.0),
                        child: Image.asset(
                          "image/email.png",
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
                      hintText: "Password",
                      filled: true,
                      suffixIcon: Icon(
                        Icons.remove_red_eye_outlined,
                        color: notifire.getgrey,
                        size: 20,
                      ),
                      prefixIcon: Icon(
                        Icons.lock_outline,
                        color: Colors.white,
                        size: 20.sp,
                      ),
                    ),
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Row(
                children: [
                  const Spacer(),
                  GestureDetector(
                    onTap: () {
                      Navigator.push(
                        context,
                        PageTransition(
                          type: PageTransitionType.fade,
                          child: Forgot_password(),
                        ),
                      );
                    },
                    child: Container(
                      height: MediaQuery.of(context).size.height / 30,
                      decoration: const BoxDecoration(
                        color: Colors.transparent,
                        border: Border(
                          bottom: BorderSide(
                            color: Color(0xffe2e3e9),
                            width: 1,
                          ),
                        ),
                      ),
                      child: Center(
                        child: Text(
                          "Forgot password?",
                          style: TextStyle(
                            fontFamily: 'Gilroy Medium',
                            color: const Color(0xffe2e3e9),
                            fontSize: 12.sp,
                          ),
                        ),
                      ),
                    ),
                  ),
                  SizedBox(width: MediaQuery.of(context).size.width / 10),
                ],
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Center(
                child: GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context,
                      PageTransition(
                        type: PageTransitionType.fade,
                        child: Term_of_use(),
                      ),
                    );
                  },
                  child: Container(
                    height: MediaQuery.of(context).size.height / 17,
                    width: MediaQuery.of(context).size.width / 1.2,
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
                        "Log In",
                        style: TextStyle(
                          fontFamily: 'Gilroy Medium',
                          color: notifire.getwhite,
                          fontWeight: FontWeight.bold,
                          fontSize: 15.sp,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 20),
              Text(
                "or by social accounts",
                style: TextStyle(
                  fontFamily: 'Gilroy Medium',
                  color: notifire.getgrey,
                  fontSize: 12.sp,
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    Image.asset(
                      "image/facebook.png",
                      height: MediaQuery.of(context).size.height / 15,
                    ),
                    img("image/google.png", Color(0xffed3068)),
                    Image.asset(
                      "image/twitter.png",
                      height: MediaQuery.of(context).size.height / 15,
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 15),
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

  Widget img(image, color) {
    return CircleAvatar(
      radius: MediaQuery.of(context).size.height / 30,
      backgroundColor: color,
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Image.asset(image, color: Color(0xfffefefd)),
      ),
    );
  }
}
