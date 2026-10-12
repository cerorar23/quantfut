import 'package:gobet/forget_password/profile/profile_settings/invite_friends/invite_friend_screen.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../../exchange_history/chat_history.dart';
import 'notification/notification.dart';

class User_profile extends StatefulWidget {
  const User_profile({Key? key}) : super(key: key);

  @override
  _User_profileState createState() => _User_profileState();
}

class _User_profileState extends State<User_profile> {
  bool _switchValue = false;
  bool switchValue = false;

  late ColorNotifire notifire;

  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getlightblue,
      body: SingleChildScrollView(
        child: Column(
          children: [
            Container(
              height: MediaQuery.of(context).size.height / 3,
              color: notifire.getprimerycolor,
              child: Column(
                children: [
                  SizedBox(height: MediaQuery.of(context).size.height / 25),
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
                        "Profile Setting",
                        style: TextStyle(
                          fontFamily: 'Gilroy Medium',
                          color: Color(0xfffffffd),
                        ),
                      ),
                      const Spacer(),
                      Image.asset(
                        "image/change_profile.png",
                        height: MediaQuery.of(context).size.height / 25,
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 40),
                    ],
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 60),
                  Image.asset(
                    "image/profile.png",
                    height: MediaQuery.of(context).size.height / 8,
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 90),
                  const Text(
                    "Dylan Dybala",
                    style: TextStyle(
                      color: Color(0xfffeffff),
                      fontFamily: 'Gilroy Bold',
                      fontSize: 16,
                    ),
                  ),
                  const Text(
                    "Designer",
                    style: TextStyle(
                      fontFamily: 'Gilroy Medium',
                      color: Color(0xfffeffff),
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            Column(
              children: [
                SizedBox(height: MediaQuery.of(context).size.height / 20),
                cards("My Quest", "image/icon17.png"),
                SizedBox(height: MediaQuery.of(context).size.height / 40),
                Row(
                  children: [
                    SizedBox(width: MediaQuery.of(context).size.width / 20),
                    Text("GENERAL", style: TextStyle(color: notifire.getgrey)),
                  ],
                ),
                SizedBox(height: MediaQuery.of(context).size.height / 40),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Container(
                    decoration: BoxDecoration(
                      color: notifire.getprimerycolor,
                      borderRadius: const BorderRadius.all(Radius.circular(15)),
                    ),
                    child: Column(
                      children: [
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: Notifications(),
                              ),
                            );
                          },
                          child: Container(
                            decoration: BoxDecoration(
                              borderRadius: const BorderRadius.all(
                                Radius.circular(10),
                              ),
                              color: notifire.getprimerycolor,
                            ),
                            height: MediaQuery.of(context).size.height / 15,
                            child: Row(
                              children: [
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 40,
                                ),
                                Padding(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 12,
                                    vertical: 18,
                                  ),
                                  child: Image.asset(
                                    "image/icon18.png",
                                    color: Colors.white,
                                  ),
                                ),
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 40,
                                ),
                                const Text(
                                  "Notification",
                                  style: TextStyle(
                                    fontFamily: 'Gilroy Medium',
                                    color: Color(0xffeff0f3),
                                  ),
                                ),
                                const Spacer(),
                                Transform.scale(
                                  scale: 0.7,
                                  child: CupertinoSwitch(
                                    thumbColor: const Color(0xff7E87F1),
                                    activeTrackColor: const Color(0xffE37FDE),
                                    value: _switchValue,
                                    onChanged: (value) {
                                      setState(() {
                                        _switchValue = value;
                                      });
                                    },
                                  ),
                                ),
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 40,
                                ),
                              ],
                            ),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 15),
                          child: Divider(
                            color: notifire.getlightblue,
                            thickness: 1,
                          ),
                        ),
                        GestureDetector(
                          onTap: () {},
                          child: Container(
                            decoration: BoxDecoration(
                              borderRadius: const BorderRadius.all(
                                Radius.circular(10),
                              ),
                              color: notifire.getprimerycolor,
                            ),
                            height: MediaQuery.of(context).size.height / 15,
                            child: Row(
                              children: [
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 40,
                                ),
                                Padding(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 12,
                                    vertical: 18,
                                  ),
                                  child: Image.asset(
                                    "image/icon19.png",
                                    color: Colors.white,
                                  ),
                                ),
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 40,
                                ),
                                const Text(
                                  "Face ID",
                                  style: TextStyle(
                                    fontFamily: 'Gilroy Medium',
                                    color: Color(0xffeff0f3),
                                  ),
                                ),
                                const Spacer(),
                                Transform.scale(
                                  scale: 0.7,
                                  child: CupertinoSwitch(
                                    thumbColor: const Color(0xff7E87F1),
                                    activeTrackColor: const Color(0xffE37FDE),
                                    value: switchValue,
                                    onChanged: (value) {
                                      setState(() {
                                        switchValue = value;
                                      });
                                    },
                                  ),
                                ),
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 40,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                SizedBox(height: MediaQuery.of(context).size.height / 80),
                cards("Language", "image/icon20.png"),
                SizedBox(height: MediaQuery.of(context).size.height / 80),
                GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context,
                      PageTransition(
                        type: PageTransitionType.fade,
                        child: Invite_screen(),
                      ),
                    );
                  },
                  child: cards("Feedback", "image/icon21.png"),
                ),
                SizedBox(height: MediaQuery.of(context).size.height / 80),
                GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context,
                      PageTransition(
                        type: PageTransitionType.fade,
                        child: Chat_history(),
                      ),
                    );
                  },
                  child: cards("Message", "image/icon6.png"),
                ),
                SizedBox(height: MediaQuery.of(context).size.height / 80),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget cards(name, img) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Container(
            decoration: BoxDecoration(
              borderRadius: const BorderRadius.all(Radius.circular(10)),
              color: notifire.getprimerycolor,
            ),
            height: MediaQuery.of(context).size.height / 15,
            child: Row(
              children: [
                SizedBox(width: MediaQuery.of(context).size.width / 40),
                Padding(
                  padding: const EdgeInsets.symmetric(
                    vertical: 18,
                    horizontal: 10,
                  ),
                  child: Image.asset(img, color: Colors.white),
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 40),
                Text(name, style: const TextStyle(color: Color(0xffeff0f3))),
                const Spacer(),
                const Icon(
                  Icons.arrow_forward_ios,
                  size: 17,
                  color: Color(0xffeff0f3),
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 40),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
