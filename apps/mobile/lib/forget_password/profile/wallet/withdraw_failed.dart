import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../utils/color_notifire.dart';

class Withdraw_failed extends StatefulWidget {
  const Withdraw_failed({Key? key}) : super(key: key);

  @override
  _Withdraw_failedState createState() => _Withdraw_failedState();
}

class _Withdraw_failedState extends State<Withdraw_failed> {
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
            Image.asset(
              "image/withdraw_failed.png",
              height: MediaQuery.of(context).size.height / 3,
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 10),
            Text(
              "Withdraw Failed",
              style: TextStyle(
                color: notifire.getwhite,
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
                    "So sorry! The system is overloaded",
                    style: TextStyle(color: notifire.getwhite),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 200),
                  Text(
                    "Please try again later",
                    style: TextStyle(color: notifire.getwhite),
                  ),
                ],
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 10),
            GestureDetector(
              onTap: () {
                // Navigator.push(context, MaterialPageRoute(builder: (context){
                //   return Withdraw_failed();
                // }));
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
