import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Notification_list extends StatefulWidget {
  const Notification_list({Key? key}) : super(key: key);

  @override
  _Notification_listState createState() => _Notification_listState();
}

class _Notification_listState extends State<Notification_list> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      body: SingleChildScrollView(
        child: Column(
          children: [
            SizedBox(height: MediaQuery.of(context).size.height / 30),
            Row(
              children: [
                SizedBox(width: MediaQuery.of(context).size.width / 30),
                GestureDetector(
                  onTap: () {
                    Navigator.pop(context);
                  },
                  child: const Icon(Icons.arrow_back, color: Colors.white),
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 3),
                const Text(
                  "Notification",
                  style: TextStyle(
                    fontFamily: 'Gilroy Medium',
                    color: Colors.white,
                    fontSize: 12,
                  ),
                ),
                const Spacer(),
                const Icon(
                  Icons.settings_outlined,
                  color: Colors.white,
                  size: 15,
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 40),
              ],
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            Container(
              color: Colors.transparent,
              height: MediaQuery.of(context).size.height / 1.1,
              child: SingleChildScrollView(
                child: Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.only(left: 15),
                      child: Row(
                        children: const [
                          Text(
                            "29 Jan 2020",
                            style: TextStyle(
                              fontFamily: 'Gilroy Medium',
                              color: Color(0xff979fdb),
                              fontSize: 10,
                            ),
                          ),
                        ],
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 50),
                    Not_list("Invited You"),
                    SizedBox(height: MediaQuery.of(context).size.height / 60),
                    Not_list("Bet Accepted"),
                    SizedBox(height: MediaQuery.of(context).size.height / 60),
                    Not_list("You Won"),
                    SizedBox(height: MediaQuery.of(context).size.height / 60),
                    Not_list("Counter Offer"),
                    SizedBox(height: MediaQuery.of(context).size.height / 60),
                    Not_list("Bet Canceled"),
                    SizedBox(height: MediaQuery.of(context).size.height / 60),
                    Not_list("Now Comment"),
                    SizedBox(height: MediaQuery.of(context).size.height / 60),
                    Not_list("Invited You"),
                    SizedBox(height: MediaQuery.of(context).size.height / 40),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget Not_list(name1) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        decoration: BoxDecoration(
          color: notifire.getlightblue,
          borderRadius: BorderRadius.all(const Radius.circular(15)),
        ),
        height: MediaQuery.of(context).size.height / 9,
        child: Column(
          children: [
            SizedBox(height: MediaQuery.of(context).size.height / 100),
            Row(
              children: [
                SizedBox(width: MediaQuery.of(context).size.width / 30),
                CircleAvatar(
                  backgroundColor: Colors.white,
                  radius: MediaQuery.of(context).size.height / 48,
                  child: CircleAvatar(
                    radius: MediaQuery.of(context).size.height / 50,
                    backgroundColor: Colors.white,
                    backgroundImage: const AssetImage("image/man.png"),
                  ),
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 50),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name1,
                      style: const TextStyle(color: Colors.white, fontSize: 15),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 100),
                    const Text(
                      "There are numberous success stories",
                      style: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        color: Colors.white,
                        fontSize: 12,
                      ),
                    ),
                    const Text(
                      "you will hear about bussinesses",
                      style: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        color: Colors.white,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                const Text(
                  "08:56PM",
                  style: TextStyle(
                    fontFamily: 'Gilroy Bold',
                    color: Color(0xff969ed4),
                    fontSize: 10,
                  ),
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 30),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
