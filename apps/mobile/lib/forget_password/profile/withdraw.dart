import 'package:gobet/forget_password/profile/wallet/withdraw_success.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

class Withdraw extends StatefulWidget {
  const Withdraw({Key? key}) : super(key: key);

  @override
  _WithdrawState createState() => _WithdrawState();
}

class _WithdrawState extends State<Withdraw> {
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
          "Withdraw",
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
                    hintText: "Amount Withdraw",
                    filled: true,
                    suffixIcon: Padding(
                      padding: const EdgeInsets.all(10.0),
                      child: Image.asset(
                        "image/doler.png",
                        color: const Color(0xffafb9cf),
                      ),
                    ),
                    prefixIcon: Padding(
                      padding: const EdgeInsets.all(11.0),
                      child: Image.asset(
                        "image/confirm.png",
                        color: const Color(0xffafb9cf),
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
                    child: Withdraw_success(),
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
                    "Withdraw Now",
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
          ],
        ),
      ),
    );
  }
}
