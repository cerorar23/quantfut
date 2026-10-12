import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import 'payment_success.dart';

class Refill_balance extends StatefulWidget {
  const Refill_balance({Key? key}) : super(key: key);

  @override
  _Refill_balanceState createState() => _Refill_balanceState();
}

class _Refill_balanceState extends State<Refill_balance> {
  bool isChecked = false;
  bool Checked = false;
  int val = -1;

  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      body: SingleChildScrollView(
        child: Column(
          children: [
            Stack(
              children: [
                Container(
                  height: MediaQuery.of(context).size.height / 3.6,
                  width: MediaQuery.of(context).size.width,
                  decoration: const BoxDecoration(
                    image: DecorationImage(
                      image: AssetImage("image/background.png"),
                      fit: BoxFit.cover,
                    ),
                    borderRadius: BorderRadius.only(
                      bottomLeft: Radius.circular(120),
                      bottomRight: Radius.circular(120),
                    ),
                  ),
                  child: Column(
                    children: [
                      SizedBox(height: MediaQuery.of(context).size.height / 25),
                      Row(
                        children: [
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 40,
                          ),
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
                            "Wallet",
                            style: TextStyle(color: Color(0xfffffffd)),
                          ),
                          const Spacer(),
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 12,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                Center(
                  child: Column(
                    children: [
                      SizedBox(
                        height: MediaQuery.of(context).size.height / 5.5,
                      ),
                      Container(
                        height: MediaQuery.of(context).size.height / 6.3,
                        width: MediaQuery.of(context).size.width / 2,
                        decoration: const BoxDecoration(
                          borderRadius: BorderRadius.all(Radius.circular(10)),
                          color: Color(0xff4c73e8),
                        ),
                        child: Column(
                          children: [
                            SizedBox(
                              height: MediaQuery.of(context).size.height / 70,
                            ),
                            Row(
                              children: [
                                const Spacer(),
                                Container(
                                  height:
                                      MediaQuery.of(context).size.height / 40,
                                  width: MediaQuery.of(context).size.width / 7,
                                  decoration: const BoxDecoration(
                                    borderRadius: BorderRadius.all(
                                      Radius.circular(10),
                                    ),
                                    color: Color(0xffd6dffc),
                                  ),
                                ),
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 30,
                                ),
                              ],
                            ),
                            SizedBox(
                              height: MediaQuery.of(context).size.height / 70,
                            ),
                            Row(
                              children: [
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 30,
                                ),
                                Container(
                                  height:
                                      MediaQuery.of(context).size.height / 40,
                                  width: MediaQuery.of(context).size.width / 10,
                                  decoration: const BoxDecoration(
                                    borderRadius: BorderRadius.all(
                                      Radius.circular(10),
                                    ),
                                    color: Color(0xffd6dffc),
                                  ),
                                ),
                              ],
                            ),
                            SizedBox(
                              height: MediaQuery.of(context).size.height / 80,
                            ),
                            Row(
                              children: [
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 30,
                                ),
                                Column(
                                  children: [
                                    const Text(
                                      "0000",
                                      style: TextStyle(
                                        fontFamily: 'Gilroy Medium',
                                        color: Color(0xffd6dffc),
                                      ),
                                    ),
                                    Container(
                                      height:
                                          MediaQuery.of(context).size.height /
                                          140,
                                      width:
                                          MediaQuery.of(context).size.width /
                                          13,
                                      decoration: const BoxDecoration(
                                        borderRadius: BorderRadius.all(
                                          Radius.circular(10),
                                        ),
                                        color: Color(0xffd6dffc),
                                      ),
                                    ),
                                  ],
                                ),
                                SizedBox(
                                  width:
                                      MediaQuery.of(context).size.width / 100,
                                ),
                                Column(
                                  children: [
                                    const Text(
                                      "0000",
                                      style: TextStyle(
                                        fontFamily: 'Gilroy Medium',
                                        color: Color(0xffd6dffc),
                                      ),
                                    ),
                                    Container(
                                      height:
                                          MediaQuery.of(context).size.height /
                                          140,
                                      width:
                                          MediaQuery.of(context).size.width /
                                          10,
                                      decoration: const BoxDecoration(
                                        borderRadius: BorderRadius.all(
                                          Radius.circular(10),
                                        ),
                                        color: Color(0xffd6dffc),
                                      ),
                                    ),
                                  ],
                                ),
                                SizedBox(
                                  width:
                                      MediaQuery.of(context).size.width / 100,
                                ),
                                Column(
                                  children: [
                                    const Text(
                                      "0000",
                                      style: TextStyle(
                                        fontFamily: 'Gilroy Medium',
                                        color: Color(0xffd6dffc),
                                      ),
                                    ),
                                    Container(
                                      height:
                                          MediaQuery.of(context).size.height /
                                          140,
                                      width:
                                          MediaQuery.of(context).size.width /
                                          13,
                                      decoration: const BoxDecoration(
                                        borderRadius: BorderRadius.all(
                                          Radius.circular(10),
                                        ),
                                        color: Color(0xffd6dffc),
                                      ),
                                    ),
                                  ],
                                ),
                                SizedBox(
                                  width:
                                      MediaQuery.of(context).size.width / 100,
                                ),
                                Column(
                                  children: [
                                    const Text(
                                      "0000",
                                      style: TextStyle(
                                        fontFamily: 'Gilroy Medium',
                                        color: Color(0xffd6dffc),
                                      ),
                                    ),
                                    Container(
                                      height:
                                          MediaQuery.of(context).size.height /
                                          140,
                                      width:
                                          MediaQuery.of(context).size.width /
                                          13,
                                      decoration: const BoxDecoration(
                                        borderRadius: BorderRadius.all(
                                          Radius.circular(10),
                                        ),
                                        color: Color(0xffd6dffc),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: const [
                          Text(
                            "Ballance",
                            style: TextStyle(
                              color: Color(0xfffffffd),
                              fontSize: 15,
                              fontFamily: 'Gilroy Bold',
                            ),
                          ),
                          Text(
                            " 0\$",
                            style: TextStyle(
                              color: Color(0xff816cfb),
                              fontSize: 15,
                              fontFamily: 'Gilroy Bold',
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 20),
                      const Text(
                        "Refill Your Balance",
                        style: TextStyle(
                          color: Color(0xfffffffd),
                          fontSize: 25,
                          fontFamily: 'Gilroy Bold',
                        ),
                      ),
                      SizedBox(
                        height: MediaQuery.of(context).size.height / 200,
                      ),
                      const Text(
                        "Choose a card for refill your balance",
                        style: TextStyle(
                          color: Color(0xfffffffd),
                          fontSize: 12,
                          fontFamily: 'Gilroy Medium',
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 20),
                      Container(
                        height: MediaQuery.of(context).size.height / 12,
                        width: MediaQuery.of(context).size.width / 1.5,
                        decoration: BoxDecoration(
                          border: Border.all(color: notifire.getmediumblue),
                          borderRadius: const BorderRadius.all(
                            Radius.circular(10),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              height: MediaQuery.of(context).size.height / 50,
                            ),
                            Row(
                              children: [
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 50,
                                ),
                                InkWell(
                                  onTap: () {
                                    setState(() {
                                      Checked = !Checked;
                                    });
                                  },
                                  child: Container(
                                    height:
                                        MediaQuery.of(context).size.height / 40,
                                    width:
                                        MediaQuery.of(context).size.width / 30,
                                    decoration: BoxDecoration(
                                      border: Border.all(
                                        color: notifire.getlightblue,
                                      ),
                                      shape: BoxShape.circle,
                                      color: notifire.getprimerycolor,
                                    ),
                                    child: Checked
                                        ? const Icon(
                                            Icons.check,
                                            size: 12.0,
                                            color: Colors.white,
                                          )
                                        : const Icon(
                                            Icons.check_box_outline_blank,
                                            size: 0,
                                            //color: Color(0xff202342),
                                          ),
                                  ),
                                ),
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 30,
                                ),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: const [
                                    Text(
                                      "John Doe",
                                      style: TextStyle(
                                        color: Color(0xffefeff1),
                                        fontFamily: 'Gilroy Medium',
                                        fontSize: 12,
                                      ),
                                    ),
                                    Text(
                                      "****  ****  ****  4444",
                                      style: TextStyle(
                                        color: Color(0xff8380b1),
                                        fontFamily: 'Gilroy Medium',
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                                Spacer(),
                                Image.asset("image/mastercard.png", height: 28),
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 80,
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 70),
                      Container(
                        height: MediaQuery.of(context).size.height / 12,
                        width: MediaQuery.of(context).size.width / 1.5,
                        decoration: BoxDecoration(
                          border: Border.all(color: notifire.getlightblue),
                          borderRadius: const BorderRadius.all(
                            Radius.circular(10),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              height: MediaQuery.of(context).size.height / 50,
                            ),
                            Row(
                              children: [
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 50,
                                ),
                                InkWell(
                                  onTap: () {
                                    setState(() {
                                      isChecked = !isChecked;
                                    });
                                  },
                                  child: Container(
                                    height:
                                        MediaQuery.of(context).size.height / 40,
                                    width:
                                        MediaQuery.of(context).size.width / 30,
                                    decoration: BoxDecoration(
                                      border: Border.all(
                                        color: notifire.getlightblue,
                                      ),
                                      shape: BoxShape.circle,
                                      color: notifire.getprimerycolor,
                                    ),
                                    child: isChecked
                                        ? const Icon(
                                            Icons.check,
                                            size: 12.0,
                                            color: Colors.white,
                                          )
                                        : const Icon(
                                            Icons.check_box_outline_blank,
                                            size: 0,
                                            //color: Color(0xff202342),
                                          ),
                                  ),
                                ),
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 30,
                                ),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: const [
                                    Text(
                                      "John Doe",
                                      style: TextStyle(
                                        fontFamily: 'Gilroy Medium',
                                        color: Color(0xffefeff1),
                                        fontSize: 12,
                                      ),
                                    ),
                                    Text(
                                      "****  ****  ****  4444",
                                      style: TextStyle(
                                        fontFamily: 'Gilroy Medium',
                                        color: Color(0xff8380b1),
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                                const Spacer(),
                                Image.asset("image/visa.png", height: 28),
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 80,
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 70),
                      const Text(
                        "+ Add another card",
                        style: TextStyle(
                          fontFamily: 'Gilroy Medium',
                          color: Color(0xffe2e3e9),
                          fontSize: 12,
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 8),
                      GestureDetector(
                        onTap: () {
                          Navigator.push(
                            context,
                            PageTransition(
                              type: PageTransitionType.fade,
                              child: Payment_success(),
                            ),
                          );
                        },
                        child: Container(
                          height: MediaQuery.of(context).size.height / 17,
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
                              "Confirm",
                              style: TextStyle(
                                color: Color(0xffe2e3e9),
                                fontFamily: 'Gilroy Medium',
                                fontSize: 17,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
