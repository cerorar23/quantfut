import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import 'password_succesfully.dart';

class Set_password extends StatefulWidget {
  const Set_password({Key? key}) : super(key: key);

  @override
  _Set_passwordState createState() => _Set_passwordState();
}

class _Set_passwordState extends State<Set_password> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
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
                const Icon(Icons.settings, color: Color(0xfffffffd)),
                SizedBox(width: MediaQuery.of(context).size.width / 40),
              ],
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 20),
            Image.asset(
              "image/img1.png",
              height: MediaQuery.of(context).size.height / 7,
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 20),
            const Text(
              "Set your Password",
              style: TextStyle(
                fontFamily: 'Gilroy Bold',
                color: Color(0xffe0e1e4),
                fontSize: 25,
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            const Text(
              "Enter your new password below,",
              style: TextStyle(
                fontFamily: 'Gilroy Medium',
                color: Color(0xffe0e1e4),
              ),
            ),
            const Text(
              "we're just being extra safe",
              style: TextStyle(
                fontFamily: 'Gilroy Medium',
                color: Color(0xffe0e1e4),
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 15),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 30),
              child: text2(),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 30),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 30),
              child: Container(
                color: Colors.transparent,
                height: MediaQuery.of(context).size.height / 17,
                child: TextField(
                  textAlign: TextAlign.left,
                  decoration: InputDecoration(
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(30),
                      borderSide: const BorderSide(
                        width: 0,
                        style: BorderStyle.none,
                      ),
                    ),
                    filled: true,
                    hintStyle: const TextStyle(
                      fontFamily: 'Gilroy Medium',
                      color: Color(0xffe2e3e9),
                      fontSize: 13,
                    ),
                    hintText: "Confirm Password",
                    fillColor: const Color(0xff2f3a66),
                    prefixIcon: const Icon(
                      Icons.lock_outline,
                      color: Color(0xff989bb2),
                      size: 20,
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
                      child: Password_success(),
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
                        Color(0xff3030b2),
                        Color(0xff322e9e),
                        Color(0xff4b32b4),
                        Color(0xff5233b4),
                        Color(0xff492f9a),
                      ],
                    ),
                  ),
                  child: const Center(
                    child: Text(
                      "Change Password",
                      style: TextStyle(
                        fontFamily: 'Gilroy Bold',
                        color: Color(0xffe2e3e9),

                        fontSize: 20,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget text2() {
    return Container(
      color: Colors.transparent,
      height: MediaQuery.of(context).size.height / 17,
      child: TextField(
        textAlign: TextAlign.left,
        decoration: InputDecoration(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(30),
            borderSide: const BorderSide(width: 0, style: BorderStyle.none),
          ),
          filled: true,
          hintStyle: const TextStyle(color: Color(0xffe2e3e9), fontSize: 13),
          hintText: "Password",
          fillColor: const Color(0xff2f3a66),
          suffixIcon: const Icon(
            Icons.remove_red_eye_outlined,
            color: Color(0xff989bb2),
            size: 20,
          ),
          prefixIcon: const Icon(
            Icons.lock_outline,
            color: Color(0xff989bb2),
            size: 20,
          ),
        ),
      ),
    );
  }
}
