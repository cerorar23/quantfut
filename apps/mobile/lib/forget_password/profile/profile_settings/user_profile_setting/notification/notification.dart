import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import 'notification_list.dart';

class Notifications extends StatefulWidget {
  const Notifications({Key? key}) : super(key: key);

  @override
  _NotificationsState createState() => _NotificationsState();
}

class _NotificationsState extends State<Notifications> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            children: [
              SizedBox(height: MediaQuery.of(context).size.height / 10),
              Container(
                decoration: BoxDecoration(
                  color: notifire.getlightblue,
                  borderRadius: const BorderRadius.all(Radius.circular(10)),
                ),
                height: MediaQuery.of(context).size.height / 1.2,
                width: MediaQuery.of(context).size.width,
                child: Column(
                  children: [
                    SizedBox(height: MediaQuery.of(context).size.height / 10),
                    Center(
                      child: Image.asset(
                        "image/notification.png",
                        height: MediaQuery.of(context).size.height / 4,
                        color: const Color(0xff91a2d4),
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 10),
                    const Text(
                      "Enable notifications",
                      style: TextStyle(
                        color: Color(0xfff6f6f5),
                        fontSize: 30,
                        fontFamily: 'Gilroy Bold',
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 70),
                    const Text(
                      "Enable push notifications to let",
                      style: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        color: Color(0xffe6eef7),
                      ),
                    ),
                    const Text(
                      "send you news and updates.",
                      style: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        color: Color(0xffe6eef7),
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 10),
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          PageTransition(
                            type: PageTransitionType.fade,
                            child: Notification_list(),
                          ),
                        );
                      },
                      child: Container(
                        height: MediaQuery.of(context).size.height / 23,
                        width: MediaQuery.of(context).size.width / 3,
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
                            "Enable",
                            style: TextStyle(
                              color: Color(0xffe2e3e9),
                              fontFamily: 'Gilroy Bold',
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 40),
                    GestureDetector(
                      onTap: () {
                        Navigator.pop(context);
                      },
                      child: Container(
                        color: Colors.transparent,
                        height: MediaQuery.of(context).size.height / 23,
                        width: MediaQuery.of(context).size.width / 3,
                        child: const Center(
                          child: Text(
                            "Cancel",
                            style: TextStyle(
                              color: Color(0xffe2e3e9),
                              fontFamily: 'Gilroy Medium',
                              fontSize: 14,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 10),
            ],
          ),
        ),
      ),
    );
  }
}
