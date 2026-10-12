import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../../../forget_password/profile/wallet/wallet.dart';

class Sports extends StatefulWidget {
  const Sports({Key? key}) : super(key: key);

  @override
  _SportsState createState() => _SportsState();
}

class _SportsState extends State<Sports> {
  final int _numPages = 2;
  final PageController _pageController = PageController(initialPage: 0);

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  int _currentPage = 0;

  List<Widget> _buildPageIndicator() {
    List<Widget> list = [];
    for (int i = 0; i < _numPages; i++) {
      list.add(i == _currentPage ? _indicator(true) : _indicator(false));
    }
    return list;
  }

  Widget _indicator(bool isActive) {
    return AnimatedContainer(
      duration: const Duration(microseconds: 150),
      margin: const EdgeInsets.symmetric(horizontal: 3.0),
      height: 8.0,
      width: isActive ? 8.0 : 8.0,
      decoration: BoxDecoration(
        color: isActive ? const Color(0xff22c0ff) : const Color(0xff474e84),
        borderRadius: const BorderRadius.all(Radius.circular(12)),
      ),
    );
  }

  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return ScreenUtilInit(
      builder: (context, child) => Scaffold(
        // bottomNavigationBar: buildBottomNavigationBar(context),
        backgroundColor: notifire.getprimerycolor,
        body: AnnotatedRegion<SystemUiOverlayStyle>(
          value: SystemUiOverlayStyle.light,
          child: SingleChildScrollView(
            child: Container(
              color: Colors.transparent,
              height: MediaQuery.of(context).size.height,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  SizedBox(height: MediaQuery.of(context).size.height / 20),
                  Row(
                    children: [
                      const Spacer(),
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
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 25,
                                ),
                                Padding(
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 4,
                                  ),
                                  child: Image.asset("image/uil-wallet.png"),
                                ),
                                SizedBox(
                                  width:
                                      MediaQuery.of(context).size.width / 100,
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
                      SizedBox(width: MediaQuery.of(context).size.width / 30),
                    ],
                  ),
                  const Padding(
                    padding: EdgeInsets.only(left: 20),
                    child: Text(
                      "Sports",
                      style: TextStyle(
                        fontFamily: 'Gilroy Bold',
                        color: Color(0xffe7e8ea),
                        fontSize: 28,
                      ),
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 90),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Container(
                      color: Colors.transparent,
                      height: MediaQuery.of(context).size.height / 20,
                      child: TextField(
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
                          hintText: "Search..",
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
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Container(
                      height: MediaQuery.of(context).size.height / 5,
                      decoration: const BoxDecoration(
                        color: Color(0xff252a4a),
                        borderRadius: BorderRadius.all(Radius.circular(15)),
                      ),
                      child: Row(
                        children: [
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 20,
                          ),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              SizedBox(
                                height: MediaQuery.of(context).size.height / 30,
                              ),
                              const Text(
                                "Today Let's Bet",
                                style: TextStyle(
                                  fontFamily: 'Gilroy Bold',
                                  color: Color(0xfffffffd),
                                  fontWeight: FontWeight.w700,
                                  fontSize: 18,
                                ),
                              ),
                              SizedBox(
                                height: MediaQuery.of(context).size.height / 30,
                              ),
                              Text(
                                "flexible in your approach ",
                                style: TextStyle(
                                  color: Color(0xfffffffd),
                                  fontFamily: 'Gilroy Medium',
                                  fontWeight: FontWeight.w400,
                                  fontSize: 13.sp,
                                ),
                              ),
                              Text(
                                "to get the best results.",
                                style: TextStyle(
                                  fontFamily: 'Gilroy Medium',
                                  color: Color(0xfffffffd),
                                  fontWeight: FontWeight.w400,
                                  fontSize: 13.sp,
                                ),
                              ),
                            ],
                          ),
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 12,
                          ),
                          Column(
                            children: [
                              SizedBox(
                                height: MediaQuery.of(context).size.height / 70,
                              ),
                              Image.asset(
                                "image/football.png",
                                height: MediaQuery.of(context).size.height / 8,
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  Container(
                    color: Colors.transparent,
                    height: MediaQuery.of(context).size.height / 2.08,
                    child: PageView(
                      physics: const ClampingScrollPhysics(),
                      controller: _pageController,
                      onPageChanged: (int page) {
                        setState(() {
                          _currentPage = page;
                        });
                      },
                      children: <Widget>[
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 20),
                          child: Column(
                            children: [
                              SizedBox(
                                height: MediaQuery.of(context).size.height / 50,
                              ),
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Game(
                                    "Football",
                                    "image/football2.png",
                                    const EdgeInsets.all(7),
                                  ),
                                  Game(
                                    "Horse Racing",
                                    "image/house_racing.png",
                                    const EdgeInsets.all(5),
                                  ),
                                  Game(
                                    "Tennis",
                                    "image/tennis.png",
                                    const EdgeInsets.all(7),
                                  ),
                                ],
                              ),
                              SizedBox(
                                height: MediaQuery.of(context).size.height / 70,
                              ),
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Game(
                                    "Golf",
                                    "image/golf.png",
                                    const EdgeInsets.all(7),
                                  ),
                                  Game(
                                    "Boxing",
                                    "image/boxing.png",
                                    const EdgeInsets.all(5),
                                  ),
                                  Game(
                                    "Basketball",
                                    "image/basket_ball.png",
                                    const EdgeInsets.all(5),
                                  ),
                                ],
                              ),
                              SizedBox(
                                height: MediaQuery.of(context).size.height / 70,
                              ),
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Game(
                                    "Cricket",
                                    "image/cricket.png",
                                    const EdgeInsets.all(5),
                                  ),
                                  Game(
                                    "Ice Hockey",
                                    "image/ice_hockey.png",
                                    const EdgeInsets.all(5),
                                  ),
                                  Game(
                                    "Volleyball",
                                    "image/volleyball.png",
                                    const EdgeInsets.all(5),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 20),
                          child: Column(
                            children: [
                              SizedBox(
                                height: MediaQuery.of(context).size.height / 50,
                              ),
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Game(
                                    "Badminton",
                                    "image/badminton.png",
                                    const EdgeInsets.all(7),
                                  ),
                                  Game(
                                    "Darts",
                                    "image/darts.png",
                                    const EdgeInsets.all(7),
                                  ),
                                  Game(
                                    "Handball",
                                    "image/handball.png",
                                    const EdgeInsets.all(3),
                                  ),
                                ],
                              ),
                              SizedBox(
                                height: MediaQuery.of(context).size.height / 70,
                              ),
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Game(
                                    "Cycling",
                                    "image/cycling.png",
                                    const EdgeInsets.all(6),
                                  ),
                                  Game(
                                    "Water polo",
                                    "image/water_polo.png",
                                    const EdgeInsets.all(2),
                                  ),
                                  Game(
                                    "MMA",
                                    "image/mma.png",
                                    const EdgeInsets.all(5),
                                  ),
                                ],
                              ),
                              SizedBox(
                                height: MediaQuery.of(context).size.height / 70,
                              ),
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Game(
                                    "Futsal",
                                    "image/futsal.png",
                                    const EdgeInsets.all(5),
                                  ),
                                  Game(
                                    "Snooker",
                                    "image/snooker.png",
                                    const EdgeInsets.all(5),
                                  ),
                                  Game(
                                    "Rugby",
                                    "image/rugby.png",
                                    const EdgeInsets.all(7),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: _buildPageIndicator(),
                  ),
                  _currentPage != _numPages
                      ? const Expanded(
                          child: Align(
                            child: Padding(
                              padding: EdgeInsets.symmetric(horizontal: 20.0),
                            ),
                          ),
                        )
                      : const Text(''),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget Games() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          Container(
            height: MediaQuery.of(context).size.height / 7.5,
            width: MediaQuery.of(context).size.width / 4.5,
            decoration: const BoxDecoration(
              color: Color(0xff252a4a),
              borderRadius: BorderRadius.all(Radius.circular(15)),
            ),
            child: Center(
              child: Column(
                children: [
                  SizedBox(height: MediaQuery.of(context).size.height / 40),
                  Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: const Color(0xffabc1f3)),
                      shape: BoxShape.circle,
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(5),
                      child: Image.asset(
                        "image/games.png",
                        color: const Color(0xffabc1f3),
                      ),
                    ),
                    height: MediaQuery.of(context).size.height / 18,
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                  const Text(
                    "",
                    style: TextStyle(color: Color(0xffabc1f3), fontSize: 11),
                  ),
                ],
              ),
            ),
          ),
          Container(
            height: MediaQuery.of(context).size.height / 7.5,
            width: MediaQuery.of(context).size.width / 4.5,
            decoration: const BoxDecoration(
              color: Color(0xff252a4a),
              borderRadius: BorderRadius.all(Radius.circular(15)),
            ),
            child: Center(
              child: Column(
                children: [
                  SizedBox(height: MediaQuery.of(context).size.height / 40),
                  Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: const Color(0xffabc1f3)),
                      shape: BoxShape.circle,
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(5),
                      child: Image.asset(
                        "image/games.png",
                        color: const Color(0xffabc1f3),
                      ),
                    ),
                    height: MediaQuery.of(context).size.height / 1,
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                  const Text(
                    "esdw",
                    style: TextStyle(color: Color(0xffabc1f3), fontSize: 11),
                  ),
                ],
              ),
            ),
          ),
          Container(
            height: MediaQuery.of(context).size.height / 7.5,
            width: MediaQuery.of(context).size.width / 4.5,
            decoration: const BoxDecoration(
              color: Color(0xff252a4a),
              borderRadius: BorderRadius.all(Radius.circular(15)),
            ),
            child: Center(
              child: Column(
                children: [
                  SizedBox(height: MediaQuery.of(context).size.height / 40),
                  Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: const Color(0xffabc1f3)),
                      shape: BoxShape.circle,
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(5),
                      child: Image.asset(
                        "image/games.png",
                        color: const Color(0xffabc1f3),
                      ),
                    ),
                    height: MediaQuery.of(context).size.height / 18,
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                  const Text(
                    "Football",
                    style: TextStyle(color: Color(0xffabc1f3), fontSize: 11),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget Game(name, img, paddi) {
    return Container(
      height: MediaQuery.of(context).size.height / 7,
      width: MediaQuery.of(context).size.width / 3.5,
      decoration: const BoxDecoration(
        color: Color(0xff252a4a),
        borderRadius: BorderRadius.all(Radius.circular(15)),
      ),
      child: Column(
        children: [
          SizedBox(height: MediaQuery.of(context).size.height / 40),
          Center(
            child: Container(
              decoration: BoxDecoration(
                border: Border.all(color: const Color(0xffabc1f3)),
                shape: BoxShape.circle,
              ),
              child: Padding(padding: paddi, child: Image.asset(img)),
              height: MediaQuery.of(context).size.height / 15,
            ),
          ),
          SizedBox(height: MediaQuery.of(context).size.height / 100),
          Text(
            name,
            style: const TextStyle(
              color: Color(0xffabc1f3),
              fontSize: 11,
              fontFamily: 'Gilroy Medium',
            ),
          ),
        ],
      ),
    );
  }
}
