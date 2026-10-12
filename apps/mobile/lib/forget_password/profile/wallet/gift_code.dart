import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../utils/color_notifire.dart';

class Gift_code extends StatefulWidget {
  const Gift_code({Key? key}) : super(key: key);

  @override
  _Gift_codeState createState() => _Gift_codeState();
}

class _Gift_codeState extends State<Gift_code> {
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
                const Spacer(),
                const Text(
                  "Redeem Gift Code",
                  style: TextStyle(
                    fontFamily: 'Gilroy Medium',
                    color: Color(0xfffffffd),
                  ),
                ),
                const Spacer(),
                SizedBox(width: MediaQuery.of(context).size.width / 12),
              ],
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 10),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 30),
              child: Container(
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
                    hintText: "Enter Code",
                    filled: true,
                    prefixIcon: Padding(
                      padding: const EdgeInsets.all(12.0),
                      child: Image.asset(
                        "image/gift_code.png",
                        color: Color(0xffafb9cf),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 20),
            GestureDetector(
              onTap: () {
                Navigator.pop(context);
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
                    "Go It",
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
