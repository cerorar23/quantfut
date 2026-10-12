import 'package:gobet/forget_password/profile/wallet/withdraw_failed.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../../../utils/color_notifire.dart';

class Withdraw_success extends StatefulWidget {
  const Withdraw_success({Key? key}) : super(key: key);

  @override
  _Withdraw_successState createState() => _Withdraw_successState();
}

class _Withdraw_successState extends State<Withdraw_success> {
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
                  child: const Icon(
                    Icons.arrow_back_sharp,
                    color: Color(0xfffffffd),
                  ),
                ),
              ],
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 30),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Image.asset(
                "image/credit-card.png",
                height: MediaQuery.of(context).size.height / 3,
              ),
            ),
            const Text(
              "\$ 25.00",
              style: TextStyle(
                color: Color(0xffF3CA41),
                fontSize: 20,
                fontWeight: FontWeight.w700,
                fontFamily: 'Gilroy Medium',
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            Container(
              color: Colors.transparent,
              child: Column(
                children: [
                  Text(
                    "You have successfully Withdraw \$ 25 into ",
                    style: TextStyle(color: notifire.getwhite),
                  ),
                  Text(
                    "your OTC Bank Account !",
                    style: TextStyle(color: notifire.getwhite),
                  ),
                ],
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 10),
            GestureDetector(
              onTap: () {
                Navigator.push(
                  context,
                  PageTransition(
                    type: PageTransitionType.fade,
                    child: Withdraw_failed(),
                  ),
                );
              },
              child: Image.asset(
                "image/button_done.png",
                height: MediaQuery.of(context).size.height / 18,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
