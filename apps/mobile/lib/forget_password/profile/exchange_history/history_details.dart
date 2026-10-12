import 'package:gobet/forget_password/profile/profile.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../utils/color_notifire.dart';

class History_details extends StatefulWidget {
  const History_details({Key? key}) : super(key: key);

  @override
  _History_detailsState createState() => _History_detailsState();
}

class _History_detailsState extends State<History_details> {
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
              color: notifire.getprimerycolor,
              height: MediaQuery.of(context).size.height / 9,
              child: Column(
                children: [
                  SizedBox(height: MediaQuery.of(context).size.height / 15),
                  Row(
                    children: [
                      SizedBox(width: MediaQuery.of(context).size.width / 30),
                      GestureDetector(
                        onTap: () {
                          Navigator.pop(context);
                        },
                        child: Icon(Icons.arrow_back, color: notifire.getwhite),
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 4.7),
                      Text(
                        "Exchange History Details",
                        style: TextStyle(
                          color: notifire.getwhite,
                          fontFamily: 'Gilroy Medium',
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 10),
            Center(
              child: Container(
                height: MediaQuery.of(context).size.height / 4.5,
                width: MediaQuery.of(context).size.width / 2,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.all(Radius.circular(10)),
                  color: notifire.getprimerycolor,
                ),
                child: Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(5),
                      child: Image.asset(
                        "image/h1.png",
                        height: MediaQuery.of(context).size.height / 6,
                      ),
                    ),
                    //SizedBox(height: MediaQuery.of(context).size.height / 200,),
                    Text(
                      "\$15 GIFT CARD",
                      style: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        color: notifire.getgrey,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 20),
            Text(
              "ZPlay Card",
              style: TextStyle(
                color: notifire.getwhite,
                fontSize: 15,
                fontFamily: 'Gilroy Medium',
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 60),
            const Text(
              "\$ 15.00",
              style: TextStyle(
                color: Color(0xffF3CA41),
                fontSize: 15,
                fontFamily: 'Gilroy Bold',
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 20),
            Container(
              color: Colors.transparent,
              height: MediaQuery.of(context).size.height / 10,
              child: Center(
                child: Column(
                  children: [
                    Text(
                      "You have changed your ZPlay Card",
                      style: TextStyle(
                        color: notifire.getwhite,
                        fontSize: 15,
                        fontFamily: 'Gilroy Medium',
                      ),
                    ),
                    Text(
                      "on 10:02 - August 17, 2018",
                      style: TextStyle(
                        color: notifire.getwhite,
                        fontSize: 15,
                        fontFamily: 'Gilroy Medium',
                      ),
                    ),
                  ],
                ),
              ),
            ),
            GestureDetector(
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => Profile()),
                );
              },
              child: Container(
                height: MediaQuery.of(context).size.height / 17,
                width: MediaQuery.of(context).size.width / 2,
                decoration: const BoxDecoration(
                  borderRadius: BorderRadius.all(Radius.circular(20)),
                  gradient: LinearGradient(
                    begin: Alignment.centerLeft,
                    end: Alignment.centerRight,
                    colors: [
                      Color(0xffDA22FF),
                      Color(0xff9733EE),
                      Color(0xffDA22FF),
                    ],
                  ),
                ),
                child: Center(
                  child: Text(
                    "Next Exchange",
                    style: TextStyle(
                      fontFamily: 'Gilroy Medium',
                      color: notifire.getwhite,
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
