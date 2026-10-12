import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:gobet/widgets/countdown_timer.dart';

import 'package:provider/provider.dart';

class Top extends StatefulWidget {
  const Top({Key? key}) : super(key: key);

  @override
  _TopState createState() => _TopState();
}

class _TopState extends State<Top> {
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
              "Football,Champions League",
              "Splash FC",
              "UC Sampdoria",
              SizedBox(width: MediaQuery.of(context).size.width / 3),
              "image/logo2.png",
              "image/basketball.png",
              MediaQuery.of(context).size.height / 10,
              MediaQuery.of(context).size.height / 10,
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            League(
              "Premier League",
              "Fc Barcelona",
              "CF Premier",
              SizedBox(width: MediaQuery.of(context).size.width / 2),
              "image/logo3.png",
              "image/logo4.png",
              MediaQuery.of(context).size.height / 10,
              MediaQuery.of(context).size.height / 10,
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            League(
              "Football,Champions League",
              "Splash FC",
              "UC Sampdoria",
              SizedBox(width: MediaQuery.of(context).size.width / 3),
              "image/logo5.png",
              "image/logo6.png",
              MediaQuery.of(context).size.height / 10,
              MediaQuery.of(context).size.height / 10,
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            League(
              "Premier League",
              "Fc Barcelona",
              "CF Premier",
              SizedBox(width: MediaQuery.of(context).size.width / 2),
              "image/logo3.png",
              "image/logo4.png",
              MediaQuery.of(context).size.height / 10,
              MediaQuery.of(context).size.height / 10,
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
          ],
        ),
      ),
    );
  }

  Widget League(name1, name3, name4, siz, img1, img2, h1, h2) {
    return Container(
      height: MediaQuery.of(context).size.height / 4,
      width: MediaQuery.of(context).size.width,
      decoration: const BoxDecoration(
        borderRadius: BorderRadius.all(Radius.circular(15)),
        color: Color(0xff252a4a),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Padding(
                padding: const EdgeInsets.only(left: 10),
                child: Text(
                  name1,
                  style: const TextStyle(
                    color: Color(0xff8a9dcf),
                    fontSize: 12,
                    fontFamily: 'Gilroy Medium',
                  ),
                ),
              ),
              Container(
                height: MediaQuery.of(context).size.height / 23,
                width: MediaQuery.of(context).size.width / 15,
                decoration: const BoxDecoration(
                  borderRadius: BorderRadius.only(
                    bottomLeft: Radius.circular(20),
                    bottomRight: Radius.circular(15),
                  ),
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
                  child: Icon(
                    Icons.hourglass_top,
                    color: Colors.white,
                    size: 15,
                  ),
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
                    Image.asset(img1, height: h1),
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
                    const Text(
                      "Live",
                      style: TextStyle(
                        color: Colors.white,
                        fontFamily: 'Gilroy Medium',
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 70),
                    Container(
                      color: Colors.transparent,
                      width: MediaQuery.of(context).size.width / 4,
                      child: CountdownTimer(
                        textStyle: const TextStyle(
                          fontSize: 17,
                          color: Color(0xff4e80fe),
                          fontFamily: 'Gilroy Medium',
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
                        fontSize: 11,
                        fontFamily: 'Gilroy Medium',
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 100),
                    Score("1.01"),
                  ],
                ),
                Column(
                  children: [
                    Image.asset(img2, height: h2),
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
        border: Border.all(color: const Color(0xff8f94b0)),
        borderRadius: const BorderRadius.all(Radius.circular(20)),
      ),
      child: Center(
        child: Text(
          name,
          style: const TextStyle(
            color: Color(0xffe2e3e9),
            fontFamily: 'Gilroy Medium',
            fontSize: 15,
          ),
        ),
      ),
    );
  }
}
