import 'package:gobet/forget_password/profile/profile.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

class Invite_screen extends StatefulWidget {
  const Invite_screen({Key? key}) : super(key: key);

  @override
  _Invite_screenState createState() => _Invite_screenState();
}

class _Invite_screenState extends State<Invite_screen> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
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
                  child: const Icon(Icons.arrow_back, color: Color(0xfffffffd)),
                ),
                const Spacer(),
                const Text(
                  "Invite Friends",
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
            SizedBox(height: MediaQuery.of(context).size.height / 7),
            const Text(
              "Earn Bonus points",
              style: TextStyle(
                color: Color(0xffe0e1e4),
                fontSize: 25,
                fontFamily: 'Gilroy Bold',
              ),
            ),
            const Text(
              "inviting your friends",
              style: TextStyle(
                color: Color(0xffe0e1e4),
                fontSize: 25,
                fontFamily: 'Gilroy Bold',
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 6),
            Image.asset(
              "image/user1.png",
              height: MediaQuery.of(context).size.height / 7,
              color: Colors.white,
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 5),
            GestureDetector(
              onTap: () {
                Navigator.push(
                  context,
                  PageTransition(
                    type: PageTransitionType.fade,
                    child: Profile(),
                  ),
                );
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
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
                  child: const Center(
                    child: Text(
                      "Send Invitation",
                      style: TextStyle(
                        color: Color(0xffe2e3e9),
                        fontFamily: 'Gilroy Bold',
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
}
