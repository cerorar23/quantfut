import 'package:gobet/forget_password/create_account.dart';
import 'package:gobet/forget_password/profile/deposit.dart';
import 'package:gobet/forget_password/profile/withdraw.dart';
import 'package:gobet/sign_in/home_screen/matches/participated.dart';
import 'package:gobet/sign_in/home_screen/news/news.dart';
import 'package:gobet/sign_in/home_screen/statistic/statics.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../../log_in/login/login.dart';
import '../../sign_in/signup.dart';
import '../forgot_password.dart';
import 'exchange_history/exchange_history.dart';
import 'invites_friends/no_result.dart';
import 'message/message.dart';
import 'profile_settings/profile_setting.dart';
import 'wallet/wallet.dart';

class Profile extends StatefulWidget {
  const Profile({Key? key}) : super(key: key);

  @override
  _ProfileState createState() => _ProfileState();
}

class _ProfileState extends State<Profile> {
  late ColorNotifire notifire;

  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getlightblue,
      appBar: AppBar(
        backgroundColor: notifire.getlightblue,
        centerTitle: true,
        title: const Text(
          "Profile",
          style: TextStyle(
            fontFamily: 'Gilroy Medium',
            color: Color(0xfffffffd),
          ),
        ),
        actions: [
          GestureDetector(
            onTap: () {
              Navigator.push(
                context,
                PageTransition(type: PageTransitionType.fade, child: Message()),
              );
            },
            child: Image.asset(
              "image/message.png",
              height: MediaQuery.of(context).size.height / 25,
            ),
          ),
          SizedBox(width: 13),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            Container(
              width: MediaQuery.of(context).size.width,
              decoration: BoxDecoration(color: notifire.getprimerycolor),
              child: Column(
                children: [
                  SizedBox(height: MediaQuery.of(context).size.height / 35),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Row(
                      children: [
                        Image.asset(
                          "image/profile.png",
                          height: MediaQuery.of(context).size.height / 7,
                        ),
                        SizedBox(
                          width: MediaQuery.of(context).size.width / 100,
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              "Dylan Dybala",
                              style: TextStyle(
                                color: Color(0xfffefefe),
                                fontSize: 18,
                                fontFamily: 'Gilroy Bold',
                              ),
                            ),
                            SizedBox(
                              height: MediaQuery.of(context).size.height / 100,
                            ),
                            const Text(
                              "\$123,456.00",
                              style: TextStyle(
                                fontFamily: 'Gilroy Medium',
                                color: Color(0xfffefefe),
                                fontSize: 13,
                              ),
                            ),
                            SizedBox(
                              height: MediaQuery.of(context).size.height / 80,
                            ),
                            Row(
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
                                    height:
                                        MediaQuery.of(context).size.height / 25,
                                  ),
                                ),
                                SizedBox(width: 15),
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
                                    height:
                                        MediaQuery.of(context).size.height / 25,
                                  ),
                                ),
                              ],
                            ),
                            SizedBox(
                              height: MediaQuery.of(context).size.height / 80,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      img("Prediction", "3.45"),
                      img("Wins", "129"),
                      img("Winrate", "32%"),
                      img("Profit", "\$78"),
                    ],
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(height: MediaQuery.of(context).size.height / 30),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Container(
                    width: MediaQuery.of(context).size.width,
                    decoration: BoxDecoration(
                      borderRadius: const BorderRadius.all(Radius.circular(10)),
                      color: notifire.getprimerycolor,
                    ),
                    child: Column(
                      children: [
                        SizedBox(
                          height: MediaQuery.of(context).size.height / 70,
                        ),
                        quest("image/icon1.png", "My Quest"),
                        const Divider(thickness: 1, color: Color(0xff34395f)),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: Statics(),
                              ),
                            );
                          },
                          child: quest("image/icon2.png", "Statics"),
                        ),
                        const Divider(thickness: 1, color: Color(0xff34395f)),
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
                          child: quest("image/wallet.png", "Wallet"),
                        ),
                        SizedBox(
                          height: MediaQuery.of(context).size.height / 100,
                        ),
                      ],
                    ),
                  ),
                ),
                SizedBox(height: MediaQuery.of(context).size.height / 40),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Container(
                    width: MediaQuery.of(context).size.width,
                    decoration: BoxDecoration(
                      borderRadius: const BorderRadius.all(Radius.circular(10)),
                      color: notifire.getprimerycolor,
                    ),
                    child: Column(
                      children: [
                        SizedBox(
                          height: MediaQuery.of(context).size.height / 70,
                        ),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: No_result(),
                              ),
                            );
                          },
                          child: quest("image/icon4.png", "My Prediction"),
                        ),
                        const Divider(thickness: 1, color: Color(0xff34395f)),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: Exchange_history(),
                              ),
                            );
                          },
                          child: quest("image/icon5.png", "Exchange History"),
                        ),
                        const Divider(thickness: 1, color: Color(0xff34395f)),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: Message(),
                              ),
                            );
                          },
                          child: quest("image/icon6.png", "Message"),
                        ),
                        const Divider(thickness: 1, color: Color(0xff34395f)),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: News(),
                              ),
                            );
                          },
                          child: quest("image/icon7.png", "News"),
                        ),
                        const Divider(thickness: 1, color: Color(0xff34395f)),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: Profile_setting(),
                              ),
                            );
                          },
                          child: quest("image/icon8.png", "Setting Profile"),
                        ),
                        const Divider(thickness: 1, color: Color(0xff34395f)),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: Create_accout(),
                              ),
                            );
                          },
                          child: quest("image/icon9.png", "Create Account"),
                        ),
                        const Divider(thickness: 1, color: Color(0xff34395f)),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: Log_in(),
                              ),
                            );
                          },
                          child: quest("image/icon10.png", "Log In"),
                        ),
                        const Divider(thickness: 1, color: Color(0xff34395f)),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: Sign_up(),
                              ),
                            );
                          },
                          child: quest("image/icon11.png", "Sign Up"),
                        ),
                        const Divider(thickness: 1, color: Color(0xff34395f)),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: Forgot_password(),
                              ),
                            );
                          },
                          child: quest("image/icon12.png", "Forgot Password"),
                        ),
                        const Divider(thickness: 1, color: Color(0xff34395f)),
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: Participated(),
                              ),
                            );
                          },
                          child: quest("image/icon13.png", "Participate"),
                        ),
                        SizedBox(
                          height: MediaQuery.of(context).size.height / 100,
                        ),
                      ],
                    ),
                  ),
                ),
                SizedBox(height: MediaQuery.of(context).size.height / 30),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget img(name1, name2) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        children: [
          Text(
            name1,
            style: const TextStyle(
              color: Color(0xfffefefe),
              fontFamily: 'Gilroy Medium',
            ),
          ),
          SizedBox(height: MediaQuery.of(context).size.height / 80),
          Stack(
            children: [
              Image.asset(
                "image/circulimg.png",
                height: MediaQuery.of(context).size.height / 11,
              ),
              Padding(
                padding: const EdgeInsets.symmetric(
                  vertical: 23,
                  horizontal: 20,
                ),
                child: Text(
                  name2,
                  style: TextStyle(
                    color: notifire.getwhite,
                    fontFamily: 'Gilroy Bold',
                    fontSize: 17,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget quest(img, name) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 15),
      child: Container(
        color: notifire.getprimerycolor,
        height: MediaQuery.of(context).size.height / 35,
        child: Row(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Image.asset(img, color: Colors.white),
            ),
            SizedBox(width: MediaQuery.of(context).size.width / 30),
            Text(
              name,
              style: const TextStyle(
                fontFamily: 'Gilroy Medium',
                color: Color(0xfffffffc),
                fontSize: 13,
              ),
            ),
            Spacer(),
            const Icon(Icons.arrow_forward_ios, size: 17, color: Colors.white),
          ],
        ),
      ),
    );
  }
}
