import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../../../utils/color_notifire.dart';
import 'history_details.dart';

class Exchange_history extends StatefulWidget {
  const Exchange_history({Key? key}) : super(key: key);

  @override
  _Exchange_historyState createState() => _Exchange_historyState();
}

class _Exchange_historyState extends State<Exchange_history> {
  late ColorNotifire notifire;

  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getlightblue,
      appBar: AppBar(
        backgroundColor: notifire.getlightblue,
        iconTheme: IconThemeData(color: Colors.white),
        centerTitle: true,
        title: Text(
          "Exchange History",
          style: TextStyle(
            color: notifire.getwhite,
            fontFamily: 'Gilroy Medium',
            fontSize: 18,
          ),
        ),
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            SizedBox(height: MediaQuery.of(context).size.height / 20),
            history(
              "ZPlay Card",
              "image/h1.png",
              "10:02 - Aug 17, 2018",
              "\$15 GIFT CARD",
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 30),
            history(
              "ZPlay Game Card",
              "image/h2.png",
              "12:02 - Aug 29, 2018",
              "\$15 GIFT CARD",
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 30),
            history(
              "Dragon Hammer",
              "image/h3.png",
              "12:02 - Sept 29, 2018",
              "",
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 30),
            history(
              "BoloBala Shield ",
              "image/h4.png",
              "11:16 - July 27, 2018",
              "",
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 30),
            history(
              "Dragon Shield ",
              "image/h5.png",
              "13:02 - July 15, 2018",
              "",
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 30),
          ],
        ),
      ),
    );
  }

  Widget history(name1, img, name2, name3) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: GestureDetector(
        onTap: () {
          Navigator.push(
            context,
            PageTransition(
              type: PageTransitionType.fade,
              child: History_details(),
            ),
          );
        },
        child: Container(
          decoration: BoxDecoration(
            borderRadius: const BorderRadius.all(Radius.circular(10)),
            color: notifire.getmediumblue,
          ),
          height: MediaQuery.of(context).size.height / 6.5,
          child: Column(
            children: [
              Row(
                children: [
                  Container(
                    height: MediaQuery.of(context).size.height / 6.5,
                    width: MediaQuery.of(context).size.width / 4,
                    decoration: BoxDecoration(
                      borderRadius: const BorderRadius.all(Radius.circular(10)),
                      color: notifire.getprimerycolor,
                    ),
                    child: Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(5),
                          child: Image.asset(
                            img,
                            height: MediaQuery.of(context).size.height / 9,
                          ),
                        ),
                        //SizedBox(height: MediaQuery.of(context).size.height / 200,),
                        Text(
                          name3,
                          style: TextStyle(
                            color: notifire.getgrey,
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                  ),
                  SizedBox(width: MediaQuery.of(context).size.width / 80),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name1,
                        style: TextStyle(
                          color: notifire.getwhite,
                          fontFamily: 'Gilroy Bold',
                          fontSize: 14,
                        ),
                      ),
                      SizedBox(
                        height: MediaQuery.of(context).size.height / 300,
                      ),
                      Text(
                        name2,
                        style: TextStyle(
                          color: notifire.getgrey,
                          fontFamily: 'Gilroy Medium',
                          fontSize: 13,
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 20),
                      const Text(
                        "-\$15.00",
                        style: TextStyle(
                          color: Color(0xffF3CA41),
                          fontFamily: 'Gilroy Medium',
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
