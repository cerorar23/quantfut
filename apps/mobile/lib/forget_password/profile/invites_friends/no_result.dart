import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class No_result extends StatefulWidget {
  const No_result({Key? key}) : super(key: key);

  @override
  _No_resultState createState() => _No_resultState();
}

class _No_resultState extends State<No_result> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      appBar: AppBar(
        backgroundColor: notifire.getprimerycolor,
        iconTheme: IconThemeData(color: Colors.white),
      ),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            height: MediaQuery.of(context).size.height / 3,
            decoration: BoxDecoration(
              color: notifire.getlightblue,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Image.asset(
                "image/search.png",
                height: MediaQuery.of(context).size.height / 4,
                color: Color(0xff7685b6),
              ),
            ),
          ),
          SizedBox(height: MediaQuery.of(context).size.height / 10),
          const Text(
            "No Results",
            style: TextStyle(
              color: Color(0xfff6f6f5),
              fontSize: 30,
              fontFamily: 'Gilroy Bold',
            ),
          ),
          SizedBox(height: MediaQuery.of(context).size.height / 70),
          const Text(
            "Sorry, there are no results for this search.",
            style: TextStyle(
              fontFamily: 'Gilroy Medium',
              color: Color(0xffe6eef7),
            ),
          ),
          const Text(
            "Please try another pharse",
            style: TextStyle(
              fontFamily: 'Gilroy Medium',
              color: Color(0xffe6eef7),
            ),
          ),
        ],
      ),
    );
  }
}
