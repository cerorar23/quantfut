import 'package:gobet/forget_password/profile/wallet/wallet.dart';
import 'package:gobet/sign_in/home_screen/matches/finished.dart';
import 'package:gobet/sign_in/home_screen/matches/live.dart';
import 'package:gobet/sign_in/home_screen/matches/up_coming.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:buttons_tabbar/buttons_tabbar.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import 'all.dart';
import 'top.dart';

class Matches extends StatefulWidget {
  const Matches({Key? key}) : super(key: key);

  @override
  _MatchesState createState() => _MatchesState();
}

class _MatchesState extends State<Matches> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
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
                          const Text(
                            "Bet with GoBet",
                            style: TextStyle(
                              fontFamily: 'Gilroy Bold',
                              color: Color(0xffe7e8ea),
                              fontSize: 25,
                            ),
                          ),
                          Spacer(),
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
                      SizedBox(height: MediaQuery.of(context).size.height / 60),
                      Padding(
                        padding: const EdgeInsets.only(right: 20),
                        child: Container(
                          height: MediaQuery.of(context).size.height / 20,
                          child: TextField(
                            style: TextStyle(color: Colors.white),
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
                                fontFamily: 'Gilroy Medium',
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
                height: MediaQuery.of(context).size.height / 1.40,
                width: MediaQuery.of(context).size.width,
                child: DefaultTabController(
                  length: 5,
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
                                    Image.asset(
                                      "image/all.png",
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
                                      "All",
                                      style: TextStyle(
                                        color: Color(0xffe2e3e9),
                                        fontFamily: 'Gilroy Medium',
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
                                        fontFamily: 'Gilroy Medium',
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
                                      "image/top.png",
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
                                      "Top",
                                      style: TextStyle(
                                        color: Color(0xffe2e3e9),
                                        fontFamily: 'Gilroy Medium',
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
                              width: MediaQuery.of(context).size.width / 3,
                              decoration: BoxDecoration(
                                border: Border.all(color: Color(0xff8f94b0)),
                                borderRadius: const BorderRadius.all(
                                  Radius.circular(5),
                                ),
                              ),
                              child: Center(
                                child: SingleChildScrollView(
                                  scrollDirection: Axis.horizontal,
                                  child: Row(
                                    children: [
                                      SizedBox(
                                        width:
                                            MediaQuery.of(context).size.width /
                                            40,
                                      ),
                                      Image.asset(
                                        "image/upcoming.png",
                                        height:
                                            MediaQuery.of(context).size.height /
                                            50,
                                      ),
                                      SizedBox(
                                        width:
                                            MediaQuery.of(context).size.width /
                                            70,
                                      ),
                                      const Text(
                                        "Up coming",
                                        style: TextStyle(
                                          color: Color(0xffe2e3e9),
                                          fontFamily: 'Gilroy Medium',
                                          fontSize: 15,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                          Tab(
                            child: Container(
                              height: MediaQuery.of(context).size.height / 19,
                              width: MediaQuery.of(context).size.width / 3.7,
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
                                      "image/finish.png",
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
                                      "Finished",
                                      style: TextStyle(
                                        color: Color(0xffe2e3e9),
                                        fontFamily: 'Gilroy Medium',
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
                          children: <Widget>[
                            All(),
                            Live(),
                            Top(),
                            Up_coming(),
                            Finished(),
                          ],
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
