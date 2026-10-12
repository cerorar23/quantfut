import 'package:gobet/forget_password/profile/wallet/gift_code.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import 'wallet/deposit_success.dart';

class Deposit extends StatefulWidget {
  const Deposit({Key? key}) : super(key: key);

  @override
  _DepositState createState() => _DepositState();
}

class _DepositState extends State<Deposit> {
  late ColorNotifire notifire;

  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      appBar: AppBar(
        backgroundColor: notifire.getlightblue,
        iconTheme: IconThemeData(color: Colors.white),
        centerTitle: true,
        title: Text(
          "Deposit",
          style: TextStyle(
            color: notifire.getwhite,
            fontFamily: 'Gilroy Medium',
            fontSize: 18,
          ),
        ),
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            SizedBox(height: MediaQuery.of(context).size.height / 10),
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
                      fontSize: 12,
                    ),
                    hintText: "Deposits ",
                    filled: true,
                    suffixIcon: Padding(
                      padding: const EdgeInsets.all(10.0),
                      child: Image.asset(
                        "image/doler.png",
                        color: Color(0xffafb9cf),
                      ),
                    ),
                    prefixIcon: Padding(
                      padding: const EdgeInsets.all(11.0),
                      child: Image.asset(
                        "image/deposits.png",
                        color: Color(0xffafb9cf),
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
                      fontSize: 12,
                    ),
                    hintText: "Choose Wallet",
                    filled: true,
                    prefixIcon: Padding(
                      padding: const EdgeInsets.all(12.0),
                      child: Image.asset(
                        "image/bank.png",
                        color: const Color(0xffafb9cf),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 20),
            GestureDetector(
              onTap: () {
                Navigator.push(
                  context,
                  PageTransition(
                    type: PageTransitionType.fade,
                    child: Deposit_success(),
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
                    colors: [Color(0xffE37FDE), Color(0xff7E87F1)],
                  ),
                ),
                child: Center(
                  child: Text(
                    "Deposit",
                    style: TextStyle(
                      fontFamily: 'Gilroy Medium',
                      color: notifire.getwhite,
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                    ),
                  ),
                ),
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 20),
            GestureDetector(
              onTap: () {
                Navigator.push(
                  context,
                  PageTransition(
                    type: PageTransitionType.fade,
                    child: Gift_code(),
                  ),
                );
              },
              child: Container(
                color: Colors.transparent,
                height: MediaQuery.of(context).size.height / 20,
                width: MediaQuery.of(context).size.width / 2,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      "or",
                      style: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        color: notifire.getwhite,
                        fontSize: 15,
                      ),
                    ),
                    SizedBox(width: MediaQuery.of(context).size.width / 100),
                    Text(
                      "Redeem Gift Code",
                      style: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        decoration: TextDecoration.underline,
                        color: notifire.getwhite,
                        fontSize: 15,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
