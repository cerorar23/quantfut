import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../../../forget_password/profile/wallet/wallet.dart';
import 'betting_know.dart';
import 'important_step.dart';

class News extends StatefulWidget {
  const News({Key? key}) : super(key: key);

  @override
  _NewsState createState() => _NewsState();
}

class _NewsState extends State<News> {
  late ColorNotifire notifire;

  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return ScreenUtilInit(
      builder: (context, child) => Scaffold(
        backgroundColor: notifire.getprimerycolor,
        appBar: AppBar(
          backgroundColor: notifire.getlightblue,
          iconTheme: IconThemeData(color: Colors.white),
          centerTitle: true,
          actions: [
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
            SizedBox(width: 15),
          ],
        ),
        body: SingleChildScrollView(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.only(left: 20),
                child: Row(
                  children: const [
                    Text(
                      "News",
                      style: TextStyle(
                        color: Color(0xffe7e8ea),
                        fontSize: 28,
                        fontFamily: 'Gilroy Bold',
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 90),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Container(
                  color: Colors.transparent,
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
                        fontFamily: 'Gilroy Medium',
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
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Row(
                    children: [
                      Lines(),
                      Lines(),
                      Lines(),
                      Lines(),
                      Lines(),
                      Lines(),
                    ],
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: const [
                    Icon(Icons.star, color: Colors.white),
                    Text(
                      " Popular Sights",
                      style: TextStyle(
                        fontFamily: 'Gilroy Bold',
                        color: Colors.white,
                      ),
                    ),
                    Spacer(),
                    Text(
                      "Show More",
                      style: TextStyle(fontSize: 11, color: Color(0xff8d9fd2)),
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      Popular_site(
                        "How to Get Started",
                        "With Sports Betting",
                        "image/img3.png",
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 30),
                      Popular_site(
                        "In this fun game ",
                        "with pre answers",
                        "image/i8.png",
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 30),
                      Popular_site(
                        "your team during a",
                        "With Sports Betting",
                        "image/i9.png",
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 30),
                      Popular_site(
                        "In this fun game ",
                        "with pre answers",
                        "image/i14.png",
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 30),
                      Popular_site(
                        "How to Get Started",
                        "With Sports Betting",
                        "image/i4.png",
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 30),
                      Popular_site(
                        "your team during a",
                        "With Sports Betting",
                        "image/i5.jpg",
                      ),
                    ],
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: const [
                    Text(
                      " Latest News",
                      style: TextStyle(
                        fontFamily: 'Gilroy Bold',
                        color: Colors.white,
                      ),
                    ),
                    Spacer(),
                    Text(
                      "Show More",
                      style: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        fontSize: 11,
                        color: Color(0xff8d9fd2),
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: [
                    Stack(
                      children: [
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              PageTransition(
                                type: PageTransitionType.fade,
                                child: Important_step(),
                              ),
                            );
                          },
                          child: Container(
                            color: Colors.transparent,
                            height: MediaQuery.of(context).size.height / 4.2,
                            width: MediaQuery.of(context).size.width / 2.9,
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(10),
                              child: Image.asset(
                                "image/i2.jpg",
                                fit: BoxFit.cover,
                              ),
                            ),
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              height: MediaQuery.of(context).size.height / 10,
                            ),
                            Text(
                              " The Basics of",
                              style: TextStyle(
                                color: Colors.white,
                                fontFamily: 'Gilroy Bold',
                                fontSize: 13.sp,
                              ),
                            ),
                            Text(
                              " Sports Betting",
                              style: TextStyle(
                                color: Colors.white,
                                fontFamily: 'Gilroy Bold',
                                fontSize: 13.sp,
                              ),
                            ),
                            SizedBox(
                              height: MediaQuery.of(context).size.height / 90,
                            ),
                            Text(
                              "  2 hours ago",
                              style: TextStyle(
                                color: const Color(0xff96a9de),
                                fontSize: 8.sp,
                                fontFamily: 'Gilroy Bold',
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    SizedBox(width: MediaQuery.of(context).size.width / 30),
                    Column(
                      children: [
                        Latest_news(
                          "  Your Guide To",
                          "  Online Betting",
                          "image/i6.jpg",
                        ),
                        SizedBox(
                          height: MediaQuery.of(context).size.height / 80,
                        ),
                        Latest_news(
                          "  Sports Betting",
                          "  Odds Particulars",
                          "image/i4.png",
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: const [
                    Text(
                      " Video",
                      style: TextStyle(
                        fontFamily: 'Gilroy Bold',
                        color: Colors.white,
                      ),
                    ),
                    Spacer(),
                    Text(
                      "Show More",
                      style: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        fontSize: 11,
                        color: Color(0xff8d9fd2),
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      GestureDetector(
                        onTap: () {
                          Navigator.push(
                            context,
                            PageTransition(
                              type: PageTransitionType.fade,
                              child: Betting_know(),
                            ),
                          );
                        },
                        child: Video(
                          "Make Money Making",
                          "Sports Bets",
                          "image/i11.png",
                        ),
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 30),
                      GestureDetector(
                        onTap: () {
                          Navigator.push(
                            context,
                            PageTransition(
                              type: PageTransitionType.fade,
                              child: Betting_know(),
                            ),
                          );
                        },
                        child: Video(
                          "Make Money Making",
                          "Sports Bets",
                          "image/i14.png",
                        ),
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 30),
                      GestureDetector(
                        onTap: () {
                          Navigator.push(
                            context,
                            PageTransition(
                              type: PageTransitionType.fade,
                              child: Betting_know(),
                            ),
                          );
                        },
                        child: Video(
                          "Make Money Making",
                          "Sports Bets",
                          "image/i11.png",
                        ),
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 30),
                      GestureDetector(
                        onTap: () {
                          Navigator.push(
                            context,
                            PageTransition(
                              type: PageTransitionType.fade,
                              child: Betting_know(),
                            ),
                          );
                        },
                        child: Video(
                          "Make Money Making",
                          "Sports Bets",
                          "image/i14.png",
                        ),
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 30),
                    ],
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: const [
                    Text(
                      " Tranding news",
                      style: TextStyle(
                        fontFamily: 'Gilroy Bold',
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Spacer(),
                    Text(
                      "Show More",
                      style: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        fontSize: 11,
                        color: Color(0xff8d9fd2),
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Column(
                  children: [
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          PageTransition(
                            type: PageTransitionType.fade,
                            child: Important_step(),
                          ),
                        );
                      },
                      child: Trading_news(
                        "Important Steps for",
                        "Sports Betting Deals",
                        "image/i1.jpg",
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 90),
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          PageTransition(
                            type: PageTransitionType.fade,
                            child: Important_step(),
                          ),
                        );
                      },
                      child: Trading_news(
                        "Sports Betting Deals",
                        "to succeed",
                        "image/i3.png",
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 90),
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          PageTransition(
                            type: PageTransitionType.fade,
                            child: Important_step(),
                          ),
                        );
                      },
                      child: Trading_news(
                        "Important Steps for",
                        "Sports Betting Deals",
                        "image/i5.jpg",
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 90),
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          PageTransition(
                            type: PageTransitionType.fade,
                            child: Important_step(),
                          ),
                        );
                      },
                      child: Trading_news(
                        "Important Steps for",
                        "Sports Betting Deals",
                        "image/i11.png",
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
            ],
          ),
        ),
      ),
    );
  }

  Widget Trading_news(name1, name2, img1) {
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xff2d325a),
        borderRadius: BorderRadius.all(Radius.circular(15)),
      ),
      height: MediaQuery.of(context).size.height / 10,
      child: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(15),
            child: Image.asset(img1, fit: BoxFit.cover),
          ),
          SizedBox(width: MediaQuery.of(context).size.width / 30),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(height: MediaQuery.of(context).size.height / 70),
              Text(
                name1,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 12.sp,
                  fontFamily: 'Gilroy Medium',
                ),
              ),
              Text(
                name2,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 12.sp,
                  fontFamily: 'Gilroy Medium',
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 70),
              Text(
                "Dec 30, 4:30 pm",
                style: TextStyle(
                  color: const Color(0xff98abdc),
                  fontSize: 8.sp,
                  fontFamily: 'Gilroy Medium',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget Video(name1, name2, img) {
    return Container(
      decoration: const BoxDecoration(
        borderRadius: BorderRadius.all(Radius.circular(15)),
        color: Color(0xff2d325a),
      ),
      height: MediaQuery.of(context).size.height / 3.8,
      width: MediaQuery.of(context).size.width / 2,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: const BorderRadius.all(Radius.circular(15)),
            child: Stack(
              children: [
                Image.asset(img, fit: BoxFit.cover),
                Center(
                  child: Column(
                    children: [
                      SizedBox(height: MediaQuery.of(context).size.height / 30),
                      Image.asset(
                        "image/video.png",
                        height: MediaQuery.of(context).size.height / 20,
                        color: const Color(0xffecedf3),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          SizedBox(height: MediaQuery.of(context).size.height / 60),
          Padding(
            padding: const EdgeInsets.only(left: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // SizedBox(
                //   height: MediaQuery.of(context).size.height / 70,
                // ),
                Text(
                  name1,
                  style: TextStyle(
                    fontSize: 13.sp,
                    color: Colors.white,
                    fontFamily: 'Gilroy Medium',
                  ),
                ),
                SizedBox(height: MediaQuery.of(context).size.height / 200),
                Text(
                  name2,
                  style: TextStyle(
                    fontSize: 13.sp,
                    color: Colors.white,
                    fontFamily: 'Gilroy Medium',
                  ),
                ),
                SizedBox(height: MediaQuery.of(context).size.height / 60),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget Latest_news(name1, name2, imgs) {
    return Stack(
      children: [
        GestureDetector(
          onTap: () {
            Navigator.push(
              context,
              PageTransition(
                type: PageTransitionType.fade,
                child: Important_step(),
              ),
            );
          },
          child: Container(
            color: Colors.transparent,
            height: MediaQuery.of(context).size.height / 9,
            width: MediaQuery.of(context).size.width / 2,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: Image.asset(imgs, fit: BoxFit.cover),
            ),
          ),
        ),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(height: MediaQuery.of(context).size.height / 60),
            Text(
              name1,
              style: TextStyle(
                color: Colors.white,
                fontFamily: 'Gilroy Bold',
                fontSize: 14.sp,
              ),
            ),
            Text(
              name2,
              style: TextStyle(
                color: Colors.white,
                fontFamily: 'Gilroy Bold',
                fontSize: 14.sp,
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 60),
            Text(
              "   2 hours ago",
              style: TextStyle(
                color: const Color(0xff96a9de),
                fontSize: 8.sp,
                fontFamily: 'Gilroy Bold',
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget Lines() {
    return Row(
      children: const [
        Text(
          "  |  ",
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: Colors.white,
            fontFamily: 'Gilroy Medium',
          ),
        ),
        Text(
          " The most epic match of the season",
          style: TextStyle(
            fontSize: 10,
            color: Colors.white,
            fontFamily: 'Gilroy Medium',
          ),
        ),
        Text(
          "/Dec 5, ",
          style: TextStyle(
            fontSize: 10,
            color: Color(0xffc2181a),
            fontFamily: 'Gilroy Medium',
          ),
        ),
      ],
    );
  }

  Widget Popular_site(name1, name2, img) {
    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          PageTransition(
            type: PageTransitionType.fade,
            child: Important_step(),
          ),
        );
      },
      child: Container(
        decoration: const BoxDecoration(
          borderRadius: BorderRadius.all(Radius.circular(15)),
          color: Color(0xff2d325a),
        ),
        height: MediaQuery.of(context).size.height / 3,
        width: MediaQuery.of(context).size.width / 2,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ClipRRect(
              borderRadius: const BorderRadius.all(Radius.circular(15)),
              child: Image.asset(img, fit: BoxFit.cover),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 60),
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // SizedBox(
                  //   height: MediaQuery.of(context).size.height / 70,
                  // ),
                  Text(
                    name1,
                    style: TextStyle(
                      fontSize: 14.sp,
                      color: Colors.white,
                      fontFamily: 'Gilroy Medium',
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 200),
                  Text(
                    name2,
                    style: TextStyle(
                      fontSize: 14.sp,
                      color: Colors.white,
                      fontFamily: 'Gilroy Medium',
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 80),
                  // SizedBox(
                  //   height: MediaQuery.of(context).size.height / 50,
                  // ),
                  Row(
                    children: [
                      Text(
                        " Dec 30,4:30pm",
                        style: TextStyle(
                          fontSize: 10.sp,
                          color: const Color(0xff9aaede),
                          fontFamily: 'Gilroy Medium',
                        ),
                      ),
                      const Spacer(),
                      Icon(
                        Icons.message_outlined,
                        size: 15.sp,
                        color: const Color(0xff9aaede),
                      ),
                      Text(
                        " 10",
                        style: TextStyle(
                          color: const Color(0xff9aaede),
                          fontSize: 10.sp,
                          fontFamily: 'Gilroy Bold',
                        ),
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 90),
                      Icon(
                        Icons.favorite_border,
                        size: 15.sp,
                        color: const Color(0xff9aaede),
                      ),
                      Text(
                        " 10",
                        style: TextStyle(
                          color: const Color(0xff9aaede),
                          fontSize: 10.sp,
                          fontFamily: 'Gilroy Bold',
                        ),
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 80),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
