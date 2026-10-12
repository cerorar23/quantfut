import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:provider/provider.dart';

class Day extends StatefulWidget {
  const Day({Key? key}) : super(key: key);

  @override
  _DayState createState() => _DayState();
}

class _DayState extends State<Day> {
  late ColorNotifire notifire;
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
              amount(
                "11.10.2020",
                "+54.30\$",
                const Color(0xff41ca7b),
                "image/football2.png",
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              amount(
                "10.11.2020",
                "-54.30\$",
                const Color(0xffca485e),
                "image/house_racing.png",
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              amount(
                "11.10.2020",
                "+54.30\$",
                const Color(0xff41ca7b),
                "image/tennis.png",
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              amount(
                "09.10.2020",
                "+54.30\$",
                const Color(0xff41ca7b),
                "image/golf.png",
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              amount(
                "21.09.2020",
                "-54.30\$",
                const Color(0xffca485e),
                "image/boxing.png",
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              amount(
                "29.08.2020",
                "+54.30\$",
                const Color(0xff41ca7b),
                "image/basket_ball.png",
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              amount(
                "28.08.2020",
                "-54.30\$",
                const Color(0xffca485e),
                "image/cricket.png",
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
              amount(
                "11.07.2020",
                "+54.30\$",
                const Color(0xff41ca7b),
                "image/ice_hockey.png",
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 60),
            ],
          ),
        ),
      ),
    );
  }

  Widget amount(name1, name2, crl, img) {
    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0xff404a6d)),
        borderRadius: const BorderRadius.all(Radius.circular(10)),
      ),
      height: MediaQuery.of(context).size.height / 15,
      child: Row(
        children: [
          SizedBox(width: MediaQuery.of(context).size.width / 40),
          Container(
            height: MediaQuery.of(context).size.height / 30,
            width: MediaQuery.of(context).size.width / 10,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xff9aabdf)),
            ),
            child: Padding(
              padding: const EdgeInsets.all(2),
              child: Image.asset(img),
            ),
          ),
          SizedBox(width: MediaQuery.of(context).size.width / 60),
          Text(
            name1,
            style: TextStyle(
              fontSize: 10.sp,
              color: const Color(0xffa9bff4),
              fontFamily: 'Gilroy Medium',
            ),
          ),
          const Spacer(),
          Text(
            name2,
            style: TextStyle(
              fontFamily: 'Gilroy Medium',
              fontSize: 10.sp,
              color: crl,
            ),
          ),
          SizedBox(width: MediaQuery.of(context).size.width / 30),
        ],
      ),
    );
  }
}
