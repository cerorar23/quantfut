import 'package:gobet/forget_password/profile/profile.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../log_in/login/login.dart';

class Sign_up extends StatefulWidget {
  const Sign_up({Key? key}) : super(key: key);

  @override
  _Sign_upState createState() => _Sign_upState();
}

class _Sign_upState extends State<Sign_up> {
  bool isChecked = false;

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
              SizedBox(height: MediaQuery.of(context).size.height / 20),
              Row(
                children: [
                  SizedBox(width: MediaQuery.of(context).size.width / 40),
                  GestureDetector(
                    onTap: () {
                      Navigator.pop(context);
                    },
                    child: Icon(Icons.arrow_back, color: Colors.white),
                  ),
                ],
              ),
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
              Textf("image/icon10.png", "User name", 14.5.toDouble()),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Textf("image/email.png", "Email", 15.toDouble()),
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
                      suffixIcon: const Icon(
                        Icons.remove_red_eye_outlined,
                        color: Color(0xffafb9cf),
                        size: 20,
                      ),
                      prefixIcon: Padding(
                        padding: const EdgeInsets.all(13),
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
              Textf("image/password.png", "Confirm password", 13.toDouble()),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              GestureDetector(
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => Profile()),
                  );
                },
                child: Center(
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
                        "Sign Up",
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
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
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
                          child: Log_in(),
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
                          "Sign in",
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

  Widget Textf(img, name1, paddi) {
    return Padding(
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
              borderSide: const BorderSide(width: 0, style: BorderStyle.none),
            ),
            fillColor: notifire.getlightblue,
            hintStyle: TextStyle(
              fontFamily: 'Gilroy Medium',
              color: notifire.getgrey,
              fontSize: 12.sp,
            ),
            hintText: name1,
            filled: true,
            prefixIcon: Padding(
              padding: EdgeInsets.all(paddi),
              child: Image.asset(img, color: Colors.white),
            ),
          ),
        ),
      ),
    );
  }
}

// Future<void> _showMyDialog() async {
//   return showDialog<void>( barrierColor: Colors.black54,
//     context: context,
//     barrierDismissible: false, // user must tap button!
//     builder: (BuildContext context) {
//       return AlertDialog(
//         shape: RoundedRectangleBorder(
//           borderRadius: BorderRadius.circular(10),
//         ),
//         backgroundColor: notifire.getlightblue,
//         content: SingleChildScrollView(
//           child: Container(
//             width: MediaQuery.of(context).size.width ,
//             child: Column(
//               crossAxisAlignment: CrossAxisAlignment.center,
//               children: [
//                 SizedBox(
//                   height: MediaQuery.of(context).size.height / 30,
//                 ),
//                 Image.asset(
//                   "image/img1.png",
//                   height: MediaQuery.of(context).size.height / 7,
//                   width: MediaQuery.of(context).size.width / 3,
//                 ),
//                 SizedBox(
//                   height: MediaQuery.of(context).size.height / 20,
//                 ),
//                 const Text(
//                   "Congratulations",
//                   style: TextStyle(fontFamily: 'Gilroy Medium',color: Color(0xff836df2), fontSize: 13),
//                 ),
//                 SizedBox(
//                   height: MediaQuery.of(context).size.height / 40,
//                 ),
//                 const Text(
//                   "Now you are registered",
//                   style: TextStyle(
//                       color: Color(0xfffefefc),
//                       fontSize: 20,
//                     fontFamily: 'Gilroy Bold',),
//                 ),
//                 SizedBox(
//                   height: MediaQuery.of(context).size.height / 40,
//                 ),
//                 const Text(
//                   "Get ready to play",
//                   style: TextStyle(fontFamily: 'Gilroy Medium',color: Color(0xfffefefc), fontSize: 13),
//                 ),
//                 SizedBox(
//                   height: MediaQuery.of(context).size.height / 12,
//                 ),
//                 GestureDetector(
//                   onTap: () {
//                     Navigator.push(context, MaterialPageRoute(builder: (context){
//                       return Matches();
//                     }));
//                   },
//                   child: sign("Start Now")  ),
//                 SizedBox(
//                   height: MediaQuery.of(context).size.height / 30,
//                 ),
//               ],
//             ),
//           ),
//         ),
//       );
//     },
//   );
// }
