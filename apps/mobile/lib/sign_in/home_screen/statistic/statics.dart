import 'package:gobet/sign_in/home_screen/statistic/month.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:buttons_tabbar/buttons_tabbar.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../../../forget_password/profile/wallet/wallet.dart';
import 'day.dart';
import 'fl_chat.dart';

class Statics extends StatefulWidget {
  const Statics({Key? key}) : super(key: key);

  @override
  _StaticsState createState() => _StaticsState();
}

class _StaticsState extends State<Statics> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      // bottomNavigationBar: buildBottomNavigationBar(context),
      backgroundColor: notifire.getprimerycolor,
      appBar: AppBar(
        backgroundColor: notifire.getprimerycolor,
        iconTheme: IconThemeData(color: Colors.white),
        actions: [
          GestureDetector(
            onTap: () {
              Navigator.push(
                context,
                PageTransition(type: PageTransitionType.fade, child: Wallet()),
              );
            },
            child: Container(
              height: MediaQuery.of(context).size.height / 25,
              width: MediaQuery.of(context).size.width / 4.5,
              decoration: const BoxDecoration(
                color: Color(0xffC028F8),
                borderRadius: BorderRadius.all(Radius.circular(15)),
              ),
              child: Center(
                child: Row(
                  children: [
                    SizedBox(width: MediaQuery.of(context).size.width / 25),
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Image.asset("image/uil-wallet.png"),
                    ),
                    SizedBox(width: MediaQuery.of(context).size.width / 100),
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
          SizedBox(width: 18),
        ],
      ),
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
                      const Text(
                        "Statistic",
                        style: TextStyle(
                          color: Color(0xffe7e8ea),
                          fontSize: 25,
                          fontFamily: 'Gilroy Bold',
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 60),
                    ],
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(left: 20, right: 20),
              child: Container(
                color: Colors.transparent,
                height: MediaQuery.of(context).size.height / 1.2,
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
                                border: Border.all(
                                  color: const Color(0xff8f94b0),
                                ),
                                borderRadius: const BorderRadius.all(
                                  Radius.circular(5),
                                ),
                              ),
                              child: const Center(
                                child: Text(
                                  "Day",
                                  style: TextStyle(
                                    color: Color(0xffe2e3e9),
                                    fontFamily: 'Gilroy Bold',
                                    fontSize: 14,
                                  ),
                                ),
                              ),
                            ),
                          ),
                          Tab(
                            child: Container(
                              height: MediaQuery.of(context).size.height / 19,
                              width: MediaQuery.of(context).size.width / 3.8,
                              decoration: BoxDecoration(
                                border: Border.all(
                                  color: const Color(0xff8f94b0),
                                ),
                                borderRadius: const BorderRadius.all(
                                  Radius.circular(5),
                                ),
                              ),
                              child: const Center(
                                child: Text(
                                  "Week",
                                  style: TextStyle(
                                    color: Color(0xffe2e3e9),
                                    fontFamily: 'Gilroy Bold',
                                    fontSize: 14,
                                  ),
                                ),
                              ),
                            ),
                          ),
                          Tab(
                            child: Container(
                              height: MediaQuery.of(context).size.height / 19,
                              width: MediaQuery.of(context).size.width / 3.8,
                              decoration: BoxDecoration(
                                border: Border.all(
                                  color: const Color(0xff8f94b0),
                                ),
                                borderRadius: const BorderRadius.all(
                                  Radius.circular(5),
                                ),
                              ),
                              child: const Center(
                                child: Text(
                                  "Month",
                                  style: TextStyle(
                                    color: Color(0xffe2e3e9),
                                    fontFamily: 'Gilroy Bold',
                                    fontSize: 14,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const Expanded(
                        child: TabBarView(
                          children: <Widget>[Day(), Fl_chat(), Month()],
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
