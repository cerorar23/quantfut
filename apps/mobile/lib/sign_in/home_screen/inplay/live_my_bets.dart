import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:gobet/widgets/countdown_timer.dart';

import 'package:provider/provider.dart';

class Live_bets extends StatefulWidget {
  const Live_bets({Key? key}) : super(key: key);

  @override
  _Live_betsState createState() => _Live_betsState();
}

class _Live_betsState extends State<Live_bets> {
  int endTime = DateTime.now().millisecondsSinceEpoch + 7200 * 12000;

  void onEnd() {
    debugPrint('onEnd');
  }

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
            League(
              "Football, Champions ",
              "Splash FC",
              "UC Sampdoria",
              "image/basketball.png",
              "image/logo2.png",
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            League(
              "Premier League",
              "Fc Barcelona",
              "Pf Premier",
              "image/logo3.png",
              "image/logo4.png",
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            League(
              "Football,Champions League",
              "Fc Barcelona",
              "UC Sampdoria",
              "image/logo5.png",
              "image/logo6.png",
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            League(
              "Premier League",
              "Fc Barcelona",
              "Pf Premier",
              "image/logo12.png",
              "image/logo15.png",
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
          ],
        ),
      ),
    );
  }

  Widget League(name1, name3, name4, img1, img2) {
    return Container(
      height: MediaQuery.of(context).size.height / 4,
      width: MediaQuery.of(context).size.width,
      decoration: const BoxDecoration(
        borderRadius: BorderRadius.all(Radius.circular(15)),
        color: Color(0xff252a4a),
      ),
      child: Column(
        children: [
          SizedBox(height: MediaQuery.of(context).size.height / 70),
          Row(
            children: [
              SizedBox(width: MediaQuery.of(context).size.width / 20),
              Text(
                name1,
                style: const TextStyle(
                  color: Color(0xff8a9dcf),
                  fontFamily: 'Gilroy Medium',
                  fontSize: 12,
                ),
              ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 5),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  children: [
                    Image.asset(
                      img1,
                      height: MediaQuery.of(context).size.height / 10,
                    ),
                    Text(
                      name3,
                      style: const TextStyle(
                        color: Colors.white,
                        fontFamily: 'Gilroy Medium',
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 100),
                    Score("2.42"),
                  ],
                ),
                Column(
                  children: [
                    SizedBox(height: MediaQuery.of(context).size.height / 100),
                    const Text("Live", style: TextStyle(color: Colors.white)),
                    SizedBox(height: MediaQuery.of(context).size.height / 70),
                    Container(
                      color: Colors.transparent,
                      width: MediaQuery.of(context).size.width / 4,
                      child: CountdownTimer(
                        textStyle: const TextStyle(
                          fontSize: 17,
                          fontFamily: 'Gilroy Medium',
                          color: Color(0xff4e80fe),
                          fontWeight: FontWeight.w500,
                        ),
                        onEnd: onEnd,
                        endTime: endTime,
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 50),
                    const Text(
                      "21.16",
                      style: TextStyle(
                        color: Colors.white,
                        fontFamily: 'Gilroy Medium',
                        fontSize: 11,
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 100),
                    Score("1.01"),
                  ],
                ),
                Column(
                  children: [
                    Image.asset(
                      img2,
                      height: MediaQuery.of(context).size.height / 10,
                    ),
                    Text(
                      name4,
                      style: const TextStyle(
                        color: Colors.white,
                        fontFamily: 'Gilroy Medium',
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 100),
                    Score("1.79"),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget Score(name) {
    return Container(
      height: MediaQuery.of(context).size.height / 23,
      width: MediaQuery.of(context).size.width / 5,
      decoration: BoxDecoration(
        border: Border.all(color: Color(0xff8f94b0)),
        borderRadius: const BorderRadius.all(Radius.circular(20)),
      ),
      child: Center(
        child: Text(
          name,
          style: const TextStyle(
            color: Color(0xffe2e3e9),
            fontFamily: 'Gilroy Medium',
            fontWeight: FontWeight.w500,
            fontSize: 15,
          ),
        ),
      ),
    );
  }
}
