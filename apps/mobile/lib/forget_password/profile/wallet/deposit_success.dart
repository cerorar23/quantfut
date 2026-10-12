import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../utils/color_notifire.dart';

class Deposit_success extends StatefulWidget {
  const Deposit_success({Key? key}) : super(key: key);

  @override
  _Deposit_successState createState() => _Deposit_successState();
}

class _Deposit_successState extends State<Deposit_success> {
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
                "image/voucher.png",
                height: MediaQuery.of(context).size.height / 3,
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            const Text(
              "\$ 4.000",
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
                    "You have successfully deposited funds in ",
                    style: TextStyle(color: notifire.getwhite),
                  ),
                  Text(
                    "your wallet !",
                    style: TextStyle(color: notifire.getwhite),
                  ),
                ],
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 5),
            Image.asset(
              "image/button_done.png",
              height: MediaQuery.of(context).size.height / 18,
            ),
          ],
        ),
      ),
    );
  }
}
