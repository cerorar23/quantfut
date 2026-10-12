import 'package:gobet/sign_in/home_screen/inplay/Inplay.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

class Congratulation_page extends StatefulWidget {
  const Congratulation_page({Key? key}) : super(key: key);

  @override
  _Congratulation_pageState createState() => _Congratulation_pageState();
}

class _Congratulation_pageState extends State<Congratulation_page> {
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
                SizedBox(width: MediaQuery.of(context).size.width / 20),
                GestureDetector(
                  onTap: () {
                    Navigator.pop(context);
                  },
                  child: Icon(Icons.arrow_back, color: Colors.white),
                ),
              ],
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 5),
            Center(
              child: Image.asset(
                "image/profile.png",
                height: MediaQuery.of(context).size.height / 5,
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 30),
            const Text(
              "Congratulations",
              style: TextStyle(
                color: Colors.white,
                fontFamily: 'Gilroy Bold',
                fontSize: 30,
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 100),
            const Text(
              "You won the matched & earned +500 free point",
              style: TextStyle(
                fontFamily: 'Gilroy Medium',
                color: Color(0xffaab7d4),
                fontSize: 10,
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 5.5),
            Container(
              height: MediaQuery.of(context).size.height / 23,
              width: MediaQuery.of(context).size.width / 1.5,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white),
                borderRadius: const BorderRadius.all(Radius.circular(20)),
              ),
              child: Row(
                children: [
                  SizedBox(width: MediaQuery.of(context).size.width / 5),
                  const Icon(Icons.share_outlined, color: Colors.white),
                  const Text(
                    "Share Results",
                    style: TextStyle(
                      fontFamily: 'Gilroy Bold',
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 30),
            GestureDetector(
              onTap: () {
                Navigator.push(
                  context,
                  PageTransition(
                    type: PageTransitionType.fade,
                    child: Inplay(),
                  ),
                );
              },
              child: Container(
                height: MediaQuery.of(context).size.height / 23,
                width: MediaQuery.of(context).size.width / 1.5,
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
                    "Return To Home",
                    style: TextStyle(
                      color: Colors.white,
                      fontFamily: 'Gilroy Bold',
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
