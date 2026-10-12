import 'package:gobet/forget_password/profile/withdraw.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../deposit.dart';
import 'add_card.dart';

class Wallet extends StatefulWidget {
  const Wallet({Key? key}) : super(key: key);

  @override
  _WalletState createState() => _WalletState();
}

class _WalletState extends State<Wallet> {
  late ColorNotifire notifire;

  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getlightblue,
      appBar: AppBar(
        backgroundColor: notifire.getlightblue,
        iconTheme: IconThemeData(color: Colors.white),
        centerTitle: true,
        title: Text(
          "Wallet",
          style: TextStyle(
            color: notifire.getwhite,
            fontFamily: "Gilroy Medium",
          ),
        ),
        actions: [
          GestureDetector(
            onTap: () {
              Navigator.push(
                context,
                PageTransition(
                  type: PageTransitionType.fade,
                  child: Add_payment(),
                ),
              );
            },
            child: Image.asset(
              "image/icon_add.png",
              height: MediaQuery.of(context).size.height / 30,
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            Container(
              color: notifire.getprimerycolor,
              height: MediaQuery.of(context).size.height / 4.5,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: MediaQuery.of(context).size.width,
                    color: Colors.transparent,
                    child: Text(
                      "+\$4,689.00",
                      style: TextStyle(
                        color: notifire.getwhite,
                        fontSize: 30,
                        fontFamily: "Gilroy Medium",
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 80),
                  Text(
                    "Balance",
                    style: TextStyle(
                      color: notifire.getgrey,
                      fontFamily: "Gilroy Medium",
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            Row(
              children: [
                Spacer(),
                GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context,
                      PageTransition(
                        type: PageTransitionType.fade,
                        child: Add_payment(),
                      ),
                    );
                  },
                  child: Container(
                    height: MediaQuery.of(context).size.height / 20,
                    width: MediaQuery.of(context).size.width / 6,
                    color: Colors.transparent,
                    child: Center(
                      child: Text(
                        "ADD NEW +",
                        style: TextStyle(color: notifire.getgrey, fontSize: 11),
                      ),
                    ),
                  ),
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 30),
              ],
            ),
            Image.asset(
              "image/credit-card.png",
              height: MediaQuery.of(context).size.height / 4,
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 4.6),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context,
                      PageTransition(
                        type: PageTransitionType.fade,
                        child: Deposit(),
                      ),
                    );
                  },
                  child: Image.asset(
                    "image/depoist_large.png",
                    height: MediaQuery.of(context).size.height / 15,
                  ),
                ),
                GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context,
                      PageTransition(
                        type: PageTransitionType.fade,
                        child: Withdraw(),
                      ),
                    );
                  },
                  child: Image.asset(
                    "image/withdraw.png",
                    height: MediaQuery.of(context).size.height / 15,
                  ),
                ),
              ],
            ),
            SizedBox(height: 15),
          ],
        ),
      ),
    );
  }
}
