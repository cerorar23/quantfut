import 'package:gobet/forget_password/profile/wallet/wallet_refill_balance.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Card_detail extends StatefulWidget {
  const Card_detail({Key? key}) : super(key: key);

  @override
  _Card_detailState createState() => _Card_detailState();
}

class _Card_detailState extends State<Card_detail> {
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
                              fontFamily: 'Gilroy Bold',
                              color: Color(0xfffffffd),
                              fontSize: 15,
                            ),
                          ),
                          Text(
                            " 0\$",
                            style: TextStyle(
                              fontFamily: 'Gilroy Bold',
                              color: Color(0xff816cfb),
                              fontSize: 15,
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 20),
                      const Text(
                        "Enter Card Details",
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
                        "Please enter card information for",
                        style: TextStyle(
                          color: Color(0xfffffffd),
                          fontSize: 12,
                          fontFamily: 'Gilroy Medium',
                        ),
                      ),
                      const Text(
                        "refill your balance",
                        style: TextStyle(
                          color: Color(0xfffffffd),
                          fontSize: 12,
                          fontFamily: 'Gilroy Medium',
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 20),
                      Row(
                        children: [
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 8,
                          ),
                          const Text(
                            "Card Number",
                            style: TextStyle(
                              color: Color(0xfffffffd),
                              fontFamily: 'Gilroy Bold',
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 90),
                      Row(
                        children: [
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 8,
                          ),
                          Row(
                            children: [
                              const Text(
                                "****  ****  ****  4444",
                                style: TextStyle(
                                  color: Color(0xfffffffd),
                                  fontFamily: 'Gilroy Bold',
                                ),
                              ),
                              SizedBox(
                                width: MediaQuery.of(context).size.width / 2.6,
                              ),
                              Image.asset("image/mastercard.png", height: 28),
                            ],
                          ),
                        ],
                      ),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 30),
                        child: Divider(color: Color(0xff23294b), thickness: 2),
                      ),
                      Row(
                        children: [
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 8,
                          ),
                          Row(
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          const Text(
                                            "Expiration Date",
                                            style: TextStyle(
                                              color: Color(0xfffffffd),
                                              fontFamily: 'Gilroy Bold',
                                            ),
                                          ),
                                          SizedBox(
                                            height:
                                                MediaQuery.of(context)
                                                    .size
                                                    .height /
                                                70,
                                          ),
                                          const Text(
                                            "12/2028",
                                            style: TextStyle(
                                              color: Color(0xfffffffd),
                                              fontFamily: 'Gilroy Bold',
                                            ),
                                          ),
                                        ],
                                      ),
                                      SizedBox(
                                        width:
                                            MediaQuery.of(context).size.width /
                                            5,
                                      ),
                                      Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          const Text(
                                            "CCV",
                                            style: TextStyle(
                                              color: Color(0xfffffffd),
                                              fontFamily: 'Gilroy Bold',
                                            ),
                                          ),
                                          SizedBox(
                                            height:
                                                MediaQuery.of(context)
                                                    .size
                                                    .height /
                                                70,
                                          ),
                                          const Text(
                                            "***",
                                            style: TextStyle(
                                              color: Color(0xfffffffd),
                                              fontFamily: 'Gilroy Bold',
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                  SizedBox(
                                    height:
                                        MediaQuery.of(context).size.height /
                                        100,
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ],
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 30),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Container(
                              color: Colors.transparent,
                              width: MediaQuery.of(context).size.width / 2.5,
                              child: const Divider(
                                color: Color(0xff23294b),
                                thickness: 2,
                              ),
                            ),
                            Container(
                              color: Colors.transparent,
                              width: MediaQuery.of(context).size.width / 2.7,
                              child: const Divider(
                                color: Color(0xff23294b),
                                thickness: 2,
                              ),
                            ),
                          ],
                        ),
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 10),
                      SizedBox(height: MediaQuery.of(context).size.height / 8),
                      GestureDetector(
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) {
                                return Refill_balance();
                              },
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
