import 'package:gobet/sign_in/home_screen/inplay/wins.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:buttons_tabbar/buttons_tabbar.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../../../forget_password/profile/wallet/wallet.dart';
import 'live_my_bets.dart';
import 'loses.dart';

class Inplay extends StatefulWidget {
  const Inplay({Key? key}) : super(key: key);

  @override
  _InplayState createState() => _InplayState();
}

class _InplayState extends State<Inplay> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      // bottomNavigationBar: buildBottomNavigationBar(context),
      backgroundColor: notifire.getprimerycolor,
      body: SingleChildScrollView(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.only(left: 20),
              child: Stack(
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(height: MediaQuery.of(context).size.height / 20),
                      Row(
                        children: [
                          const Spacer(),
                          GestureDetector(
                            onTap: () {
                              Navigator.push(
                                context,
                                PageTransition(
                                  type: PageTransitionType.fade,
                                  child: Wallet(),
                                ),
                              );
                            },
                            child: Container(
                              height: MediaQuery.of(context).size.height / 25,
                              width: MediaQuery.of(context).size.width / 4.5,
                              decoration: const BoxDecoration(
                                color: Color(0xffC028F8),
                                borderRadius: BorderRadius.all(
                                  Radius.circular(15),
                                ),
                              ),
                              child: Center(
                                child: Row(
                                  children: [
                                    SizedBox(
                                      width:
                                          MediaQuery.of(context).size.width /
                                          25,
                                    ),
                                    Padding(
                                      padding: const EdgeInsets.symmetric(
                                        vertical: 4,
                                      ),
                                      child: Image.asset(
                                        "image/uil-wallet.png",
                                      ),
                                    ),
                                    SizedBox(
                                      width:
                                          MediaQuery.of(context).size.width /
                                          100,
                                    ),
                                    const Text(
                                      "500\$",
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 11,
                                        fontFamily: 'Gilroy Bold',
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 30,
                          ),
                        ],
                      ),
                      const Text(
                        "My Bets",
                        style: TextStyle(
                          color: Color(0xffe7e8ea),
                          fontSize: 25,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 60),
                      Padding(
                        padding: const EdgeInsets.only(right: 20),
                        child: Container(
                          color: Colors.transparent,
                          height: MediaQuery.of(context).size.height / 20,
                          child: TextField(
                            textAlign: TextAlign.left,
                            decoration: InputDecoration(
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(5),
                                borderSide: const BorderSide(
                                  width: 0,
                                  style: BorderStyle.none,
                                ),
                              ),
                              filled: true,
                              hintStyle: const TextStyle(
                                color: Color(0xffe2e3e9),
                                fontSize: 12,
                              ),
                              hintText: "Search",
                              fillColor: const Color(0xff2f3a66),
                              prefixIcon: const Icon(
                                Icons.search,
                                color: Color(0xff989bb2),
                                size: 20,
                              ),
                              suffixIcon: const Icon(
                                Icons.mic,
                                color: Color(0xff989bb2),
                                size: 20,
                              ),
                            ),
                          ),
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 30),
                    ],
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(left: 20, right: 20),
              child: Container(
                color: Colors.transparent,
                height: MediaQuery.of(context).size.height / 0.8,
                width: MediaQuery.of(context).size.width,
                child: DefaultTabController(
                  length: 3,
                  child: Column(
                    children: <Widget>[
                      ButtonsTabBar(
                        backgroundColor: const Color(0xff4532b2),
                        unselectedBackgroundColor: notifire.getprimerycolor,
                        unselectedLabelStyle: const TextStyle(
                          color: Colors.black,
                        ),
                        labelStyle: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                        tabs: [
                          Tab(
                            child: Container(
                              height: MediaQuery.of(context).size.height / 19,
                              width: MediaQuery.of(context).size.width / 3.8,
                              decoration: BoxDecoration(
                                border: Border.all(color: Color(0xff8f94b0)),
                                borderRadius: const BorderRadius.all(
                                  Radius.circular(5),
                                ),
                              ),
                              child: Center(
                                child: Row(
                                  children: [
                                    SizedBox(
                                      width:
                                          MediaQuery.of(context).size.width /
                                          40,
                                    ),
                                    const Icon(
                                      Icons.fiber_manual_record_sharp,
                                      color: Colors.green,
                                    ),
                                    SizedBox(
                                      width:
                                          MediaQuery.of(context).size.width /
                                          40,
                                    ),
                                    const Text(
                                      "Live",
                                      style: TextStyle(
                                        color: Color(0xffe2e3e9),
                                        fontFamily: 'Gilroy Bold',
                                        fontSize: 15,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          Tab(
                            child: Container(
                              height: MediaQuery.of(context).size.height / 19,
                              width: MediaQuery.of(context).size.width / 3.8,
                              decoration: BoxDecoration(
                                border: Border.all(color: Color(0xff8f94b0)),
                                borderRadius: const BorderRadius.all(
                                  Radius.circular(5),
                                ),
                              ),
                              child: Center(
                                child: Row(
                                  children: [
                                    SizedBox(
                                      width:
                                          MediaQuery.of(context).size.width /
                                          40,
                                    ),
                                    Image.asset(
                                      "image/win.png",
                                      height:
                                          MediaQuery.of(context).size.height /
                                          50,
                                    ),
                                    SizedBox(
                                      width:
                                          MediaQuery.of(context).size.width /
                                          40,
                                    ),
                                    const Text(
                                      "Wins",
                                      style: TextStyle(
                                        color: Color(0xffe2e3e9),
                                        fontFamily: 'Gilroy Bold',
                                        fontSize: 15,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          Tab(
                            child: Container(
                              height: MediaQuery.of(context).size.height / 19,
                              width: MediaQuery.of(context).size.width / 3.8,
                              decoration: BoxDecoration(
                                border: Border.all(color: Color(0xff8f94b0)),
                                borderRadius: const BorderRadius.all(
                                  Radius.circular(5),
                                ),
                              ),
                              child: Center(
                                child: Row(
                                  children: [
                                    SizedBox(
                                      width:
                                          MediaQuery.of(context).size.width /
                                          40,
                                    ),
                                    Image.asset(
                                      "image/loss.png",
                                      height:
                                          MediaQuery.of(context).size.height /
                                          50,
                                    ),
                                    SizedBox(
                                      width:
                                          MediaQuery.of(context).size.width /
                                          40,
                                    ),
                                    const Text(
                                      "Loses",
                                      style: TextStyle(
                                        color: Color(0xffe2e3e9),
                                        fontFamily: 'Gilroy Bold',
                                        fontSize: 15,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const Expanded(
                        child: TabBarView(
                          children: <Widget>[Live_bets(), Wins(), Loses()],
                        ),
                      ),
                    ],
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
