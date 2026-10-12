import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import 'match.dart';

class All extends StatefulWidget {
  const All({Key? key}) : super(key: key);

  @override
  _AllState createState() => _AllState();
}

class _AllState extends State<All> {
  late ColorNotifire notifire;
  int _selectedIndex = -1;

  List imgs = [
    "image/football2.png",
    "image/house_racing.png",
    "image/tennis.png",
    "image/futsal.png",
    "image/boxing.png",
    "image/basket_ball.png",
    "image/cricket.png",
    "image/ice_hockey.png",
    "image/volleyball.png",
    "image/badminton.png",
    "image/darts.png",
    "image/handball.png",
    "image/cycling.png",
    "image/water_polo.png",
    "image/mma.png",
    "image/futsal.png",
    "image/snooker.png",
    "image/rugby.png",
  ];

  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return ScreenUtilInit(
      builder: (context, child) => Scaffold(
        backgroundColor: notifire.getprimerycolor,
        body: SingleChildScrollView(
          child: Column(
            children: [
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Padding(
                padding: const EdgeInsets.only(right: 20),
                child: Stack(
                  children: [
                    Container(
                      height: MediaQuery.of(context).size.height / 5,
                      width: MediaQuery.of(context).size.width,
                      decoration: const BoxDecoration(
                        borderRadius: BorderRadius.all(Radius.circular(20)),
                        color: Color(0xff252a4a),
                      ),
                      child: Row(
                        children: [
                          Column(
                            children: [
                              Padding(
                                padding: const EdgeInsets.only(left: 20),
                                child: Row(
                                  children: [
                                    Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        SizedBox(
                                          height:
                                              MediaQuery.of(context)
                                                  .size
                                                  .height /
                                              30,
                                        ),
                                        Row(
                                          children: const [
                                            Text(
                                              "Bets is the activity",
                                              style: TextStyle(
                                                color: Color(0xffdfe0e4),
                                                fontSize: 18,
                                                fontFamily: 'Gilroy ExtraBold',
                                              ),
                                            ),
                                          ],
                                        ),
                                        SizedBox(
                                          height:
                                              MediaQuery.of(context)
                                                  .size
                                                  .height /
                                              40,
                                        ),
                                        Text(
                                          "Cash Out betting lets the",
                                          style: TextStyle(
                                            fontFamily: 'Gilroy Bold',
                                            color: Color(0xffdfe0e4),
                                            fontSize: 13.sp,
                                          ),
                                        ),
                                        Text(
                                          "User of a betting take profit",
                                          style: TextStyle(
                                            fontFamily: 'Gilroy Bold',
                                            color: Color(0xffdfe0e4),
                                            fontSize: 13.sp,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 15,
                          ),
                          Image.asset(
                            "image/football.png",
                            height: MediaQuery.of(context).size.height / 5,
                            width: MediaQuery.of(context).size.width / 5,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Row(
                children: const [
                  Text(
                    "In-Play",
                    style: TextStyle(
                      fontFamily: 'Gilroy Bold',
                      color: Color(0xffe7e8ea),
                      fontSize: 25,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              Container(
                color: Colors.transparent,
                height: MediaQuery.of(context).size.height / 10,
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: 18,
                  itemBuilder: (context, index) {
                    return GestureDetector(
                      onTap: () {
                        setState(() {
                          _selectedIndex = index;
                        });
                      },
                      child: Row(
                        children: [
                          Container(
                            height: MediaQuery.of(context).size.height / 10,
                            width: MediaQuery.of(context).size.width / 9,
                            decoration: BoxDecoration(
                              color: _selectedIndex == index
                                  ? const Color(0xff8160DE)
                                  : Colors.transparent,
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white),
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(5),
                              child: Image.asset(imgs[index].toString()),
                            ),
                          ),
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 40,
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
              Row(
                children: const [
                  Text(
                    "Live Now",
                    style: TextStyle(
                      fontFamily: 'Gilroy Bold',
                      color: Color(0xffe7e8ea),
                      fontSize: 25,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          PageTransition(
                            type: PageTransitionType.fade,
                            child: Live_match(),
                          ),
                        );
                      },
                      child: Sports(
                        "image/basketball.png",
                        "image/logo_9.png",
                        MediaQuery.of(context).size.height / 18,
                        MediaQuery.of(context).size.height / 22,
                      ),
                    ),
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          PageTransition(
                            type: PageTransitionType.fade,
                            child: Live_match(),
                          ),
                        );
                      },
                      child: Sports(
                        "image/logo2.png",
                        "image/logo3.png",
                        MediaQuery.of(context).size.height / 18,
                        MediaQuery.of(context).size.height / 16,
                      ),
                    ),
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          PageTransition(
                            type: PageTransitionType.fade,
                            child: Live_match(),
                          ),
                        );
                      },
                      child: Sports(
                        "image/logo4.png",
                        "image/logo5.png",
                        MediaQuery.of(context).size.height / 14,
                        MediaQuery.of(context).size.height / 16,
                      ),
                    ),
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          PageTransition(
                            type: PageTransitionType.fade,
                            child: Live_match(),
                          ),
                        );
                      },
                      child: Sports(
                        "image/logo6.png",
                        "image/logo7.png",
                        MediaQuery.of(context).size.height / 18,
                        MediaQuery.of(context).size.height / 19,
                      ),
                    ),
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          PageTransition(
                            type: PageTransitionType.fade,
                            child: Live_match(),
                          ),
                        );
                      },
                      child: Sports(
                        "image/logo8.png",
                        "image/logo9.png",
                        MediaQuery.of(context).size.height / 14,
                        MediaQuery.of(context).size.height / 18,
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Row(
                children: const [
                  Text(
                    "International Matches",
                    style: TextStyle(
                      fontFamily: 'Gilroy Bold',
                      color: Color(0xffe7e8ea),
                      fontSize: 25,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              GestureDetector(
                onTap: () {
                  Navigator.push(
                    context,
                    PageTransition(
                      type: PageTransitionType.fade,
                      child: Live_match(),
                    ),
                  );
                },
                child: League(
                  "The International 2022",
                  "image/logo_1.png",
                  "image/logo_2.png",
                  "Natus",
                  "Flatic",
                  "04/06 12:00 B03",
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              GestureDetector(
                onTap: () {
                  Navigator.push(
                    context,
                    PageTransition(
                      type: PageTransitionType.fade,
                      child: Live_match(),
                    ),
                  );
                },
                child: League(
                  "Premier Bets League",
                  "image/logo_6.png",
                  "image/logo_4.png",
                  "Premier",
                  "League",
                  "05/06 11:00 B03",
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget Sports(img1, img2, h1, h2) {
    return Row(
      children: [
        Container(
          height: MediaQuery.of(context).size.height / 12,
          width: MediaQuery.of(context).size.width / 2.5,
          decoration: BoxDecoration(
            borderRadius: const BorderRadius.all(Radius.circular(15)),
            color: notifire.getmediumblue,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Image.asset(img1, height: h1),
              Column(
                children: const [
                  Text(
                    "vs",
                    style: TextStyle(
                      fontFamily: 'Gilroy Medium',
                      color: Colors.white,
                    ),
                  ),
                  Text(
                    "0:0",
                    style: TextStyle(
                      fontSize: 18,
                      color: Color(0xff4e80fe),
                      fontFamily: 'Gilroy Bold',
                    ),
                  ),
                  Text(
                    "21.16",
                    style: TextStyle(
                      fontFamily: 'Gilroy Medium',
                      color: Colors.white,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
              Image.asset(img2, height: h2),
            ],
          ),
        ),
        SizedBox(width: MediaQuery.of(context).size.width / 50),
      ],
    );
  }

  Widget League(name1, img1, img2, name2, name3, name4) {
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
              SizedBox(width: MediaQuery.of(context).size.width / 10),
              Text(
                name1,
                style: TextStyle(color: notifire.getwhite, fontSize: 14.sp),
              ),
            ],
          ),
          SizedBox(height: MediaQuery.of(context).size.height / 50),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              Column(
                children: [
                  Image.asset(
                    img1,
                    height: MediaQuery.of(context).size.height / 15,
                    width: MediaQuery.of(context).size.width / 7,
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 70),
                  Text(
                    name2,
                    style: TextStyle(
                      color: Colors.white,
                      fontFamily: 'Gilroy Medium',
                      fontSize: 16.sp,
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                ],
              ),
              Column(
                children: [
                  SizedBox(height: MediaQuery.of(context).size.height / 70),
                  Text(
                    "1  -  0",
                    style: TextStyle(
                      color: Colors.white,
                      fontFamily: 'Gilroy Bold',
                      fontSize: 22.sp,
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 60),
                  Image.asset(
                    "image/live.png",
                    height: MediaQuery.of(context).size.height / 30,
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                ],
              ),
              Column(
                children: [
                  Image.asset(
                    img2,
                    height: MediaQuery.of(context).size.height / 15,
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 70),
                  Text(
                    name3,
                    style: TextStyle(
                      color: Colors.white,
                      fontFamily: 'Gilroy Medium',
                      fontSize: 16.sp,
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                ],
              ),
            ],
          ),
          Divider(color: notifire.getlightblue, thickness: 1),
          SizedBox(height: MediaQuery.of(context).size.height / 100),
          Text(
            name4,
            style: TextStyle(color: notifire.getwhite, fontSize: 12.sp),
          ),
        ],
      ),
    );
  }
}
