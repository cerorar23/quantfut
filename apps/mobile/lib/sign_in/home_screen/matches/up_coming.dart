import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import '../../../utils/color_notifire.dart';
import 'match.dart';

class Up_coming extends StatefulWidget {
  const Up_coming({Key? key}) : super(key: key);

  @override
  _Up_comingState createState() => _Up_comingState();
}

class _Up_comingState extends State<Up_coming> {
  late ColorNotifire notifire;
  int selected = 0;
  int selected1 = 0;

  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      body: SingleChildScrollView(
        child: Column(
          children: [
            SizedBox(height: MediaQuery.of(context).size.height / 40),
            Container(
              color: Colors.transparent,
              child: SingleChildScrollView(
                child: Column(
                  children: [
                    ListView.builder(
                      key: Key('builder ${selected.toString()}'),
                      padding: EdgeInsets.only(left: 0, right: 0),
                      shrinkWrap: true,
                      physics: NeverScrollableScrollPhysics(),
                      itemCount: 1,
                      itemBuilder: (context, index) {
                        return Column(
                          children: <Widget>[
                            ExpansionTile(
                              key: Key(index.toString()),
                              collapsedIconColor: Colors.blue,
                              //attention
                              initiallyExpanded: index == selected,
                              title: Container(
                                height: MediaQuery.of(context).size.height / 20,
                                decoration: BoxDecoration(
                                  borderRadius: const BorderRadius.all(
                                    Radius.circular(10),
                                  ),
                                  color: notifire.getlightblue,
                                ),
                                child: Row(
                                  children: [
                                    Padding(
                                      padding: const EdgeInsets.only(
                                        left: 15,
                                        bottom: 5,
                                        top: 5,
                                        right: 10,
                                      ),
                                      child: Image.asset(
                                        "image/icon_cup_1.png",
                                      ),
                                    ),
                                    Text(
                                      " Dota PIT Minor Qualifier",
                                      style: TextStyle(
                                        color: notifire.getwhite,
                                        fontSize: 14,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              children: <Widget>[
                                League(
                                  "A-League B02",
                                  "Natus",
                                  "Fnatic",
                                  "image/logo_1.png",
                                  "image/logo_2.png",
                                  "0",
                                  "0",
                                  "Today, 30 minutes left",
                                ),
                                SizedBox(
                                  height:
                                      MediaQuery.of(context).size.height / 70,
                                ),
                                League(
                                  "A-League B02",
                                  "Taurora",
                                  "Roshan",
                                  "image/logo_4.png",
                                  "image/logo_8.png",
                                  "0",
                                  "0",
                                  "Fri, April 04 22:00",
                                ),
                              ],
                              onExpansionChanged: ((newState) {
                                if (newState) {
                                  setState(() {
                                    Duration(seconds: 20000);
                                    selected = index;
                                  });
                                } else {
                                  setState(() {
                                    selected = -1;
                                  });
                                }
                              }),
                            ),
                          ],
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
            Container(
              color: Colors.transparent,
              child: SingleChildScrollView(
                child: Column(
                  children: [
                    ListView.builder(
                      key: Key('builder ${selected.toString()}'),
                      padding: EdgeInsets.only(left: 0, right: 0),
                      shrinkWrap: true,
                      physics: NeverScrollableScrollPhysics(),
                      itemCount: 1,
                      itemBuilder: (context, index) {
                        return Column(
                          children: <Widget>[
                            ExpansionTile(
                              key: Key(index.toString()),
                              collapsedIconColor: Colors.blue,
                              //attention
                              initiallyExpanded: index == selected1,
                              title: Container(
                                height: MediaQuery.of(context).size.height / 20,
                                decoration: BoxDecoration(
                                  borderRadius: const BorderRadius.all(
                                    Radius.circular(10),
                                  ),
                                  color: notifire.getlightblue,
                                ),
                                child: Row(
                                  children: [
                                    Padding(
                                      padding: const EdgeInsets.only(
                                        left: 15,
                                        bottom: 5,
                                        top: 5,
                                        right: 10,
                                      ),
                                      child: Image.asset(
                                        "image/icon_cup_1.png",
                                      ),
                                    ),
                                    Text(
                                      " The International 2018",
                                      style: TextStyle(
                                        color: notifire.getwhite,
                                        fontSize: 14,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              children: <Widget>[
                                League(
                                  "A-League B02",
                                  "Eclipse",
                                  "Secret",
                                  "image/logo_12.png",
                                  "image/logo_13.png",
                                  "0",
                                  "0",
                                  "Today, 2 hours left",
                                ),
                                SizedBox(
                                  height:
                                      MediaQuery.of(context).size.height / 70,
                                ),
                                League(
                                  "A-League B02",
                                  "Kingguin",
                                  "Kingdra",
                                  "image/logo_6.png",
                                  "image/logo_7.png",
                                  "0",
                                  "0",
                                  "Fri, April 04 00:00",
                                ),
                                SizedBox(
                                  height:
                                      MediaQuery.of(context).size.height / 70,
                                ),
                              ],
                              onExpansionChanged: ((newState) {
                                if (newState) {
                                  setState(() {
                                    Duration(seconds: 20000);
                                    selected1 = index;
                                  });
                                } else {
                                  setState(() {
                                    selected1 = -1;
                                  });
                                }
                              }),
                            ),
                          ],
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
            // ExpansionTile(
            //   trailing: (isscroll == true)
            //       ? const Icon(
            //     Icons.keyboard_arrow_down,
            //     size: 25,
            //     color: Colors.blue,
            //   )
            //       : const Icon(Icons.arrow_forward_ios, size: 20, color: Colors.blue),
            //   onExpansionChanged: (value) {
            //     setState(() {
            //       isscroll = value;
            //     });
            //   },
            //   tilePadding: EdgeInsets.all(0),
            //   title: Container(
            //     height: MediaQuery.of(context).size.height / 20,
            //     decoration: BoxDecoration(
            //       borderRadius: const BorderRadius.all(
            //         Radius.circular(10),
            //       ),
            //       color: notifire.getlightblue,
            //     ),
            //     child: Row(
            //       children: [
            //         Padding(
            //           padding: const EdgeInsets.only(
            //               left: 15, bottom: 5, top: 5, right: 10),
            //           child: Image.asset("image/icon_cup_1.png"),
            //         ),
            //         Text(
            //           " Dota PIT Minor Qualifier",
            //           style: TextStyle(color: notifire.getwhite, fontSize: 14),
            //         ),
            //       ],
            //     ),
            //   ),
            //   children: [
            //     League("A-League B02", "Natus", "Fnatic", "image/logo_1.png",
            //         "image/logo_2.png", "0", "0", "Today, 30 minutes left",),
            //     SizedBox(
            //       height: MediaQuery.of(context).size.height / 70,
            //     ),
            //     League("A-League B02", "Taurora", "Roshan", "image/logo_4.png",
            //         "image/logo_8.png", "0", "0", "Fri, April 04 22:00",),
            //   ],
            // ),
            // ExpansionTile(
            //   trailing: (isExpand == true)
            //       ? const Icon(
            //     Icons.keyboard_arrow_down,
            //     size: 25,
            //     color: Colors.blue,
            //   )
            //       : const Icon(Icons.arrow_forward_ios, size: 20, color: Colors.blue),
            //   onExpansionChanged: (value) {
            //     setState(() {
            //       isExpand = value;
            //     });
            //   },
            //   tilePadding: const EdgeInsets.all(0),
            //   title: Container(
            //     height: MediaQuery.of(context).size.height / 20,
            //     decoration: BoxDecoration(
            //       borderRadius: const BorderRadius.all(
            //         Radius.circular(10),
            //       ),
            //       color: notifire.getlightblue,
            //     ),
            //     child: Row(
            //       children: [
            //         Padding(
            //           padding: const EdgeInsets.only(
            //               left: 15, bottom: 5, top: 5, right: 10),
            //           child: Image.asset("image/icon_cup_1.png"),
            //         ),
            //         Text(
            //           " The International 2018",
            //           style: TextStyle(color: notifire.getwhite, fontSize: 14),
            //         ),
            //       ],
            //     ),
            //   ),
            //   children: [
            //     League("A-League B02", "Eclipse", "Secret", "image/logo_12.png",
            //         "image/logo_13.png", "0", "0", "Today, 2 hours left",),
            //     SizedBox(
            //       height: MediaQuery.of(context).size.height / 70,
            //     ),
            //     League("A-League B02", "Kingguin", "Kingdra", "image/logo_6.png",
            //         "image/logo_7.png", "0", "0", "Fri, April 04 00:00",),
            //     SizedBox(
            //       height: MediaQuery.of(context).size.height / 70,
            //     ),
            //   ],
            // ),
          ],
        ),
      ),
    );
  }

  Widget League(name1, name2, name3, img1, img2, name4, name5, name6) {
    return Container(
      height: MediaQuery.of(context).size.height / 5.5,
      width: MediaQuery.of(context).size.width,
      decoration: const BoxDecoration(
        borderRadius: BorderRadius.all(Radius.circular(15)),
        color: Color(0xff252a4a),
      ),
      child: Column(
        children: [
          SizedBox(height: MediaQuery.of(context).size.height / 70),
          Center(
            child: Text(
              name1,
              style: TextStyle(
                color: notifire.getwhite,
                fontSize: 17,
                fontFamily: 'Gilroy Bold',
              ),
            ),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              Column(
                children: [
                  Image.asset(
                    img1,
                    height: MediaQuery.of(context).size.height / 15,
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                  Text(
                    name2,
                    style: const TextStyle(
                      color: Colors.white,
                      fontFamily: 'Gilroy Medium',
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                ],
              ),
              Column(
                children: [
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                  Row(
                    children: [
                      Text(
                        name4,
                        style: TextStyle(
                          fontSize: 20,
                          color: notifire.getwhite,
                          fontFamily: 'Gilroy Bold',
                        ),
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 20),
                      Text(
                        "-",
                        style: TextStyle(
                          fontSize: 20,
                          color: notifire.getwhite,
                          fontFamily: 'Gilroy Bold',
                        ),
                      ),
                      SizedBox(width: MediaQuery.of(context).size.width / 20),
                      Text(
                        name5,
                        style: TextStyle(
                          fontSize: 20,
                          color: notifire.getwhite,
                          fontFamily: 'Gilroy Bold',
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
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
                    child: Image.asset(
                      "image/bet_now.png",
                      height: MediaQuery.of(context).size.height / 30,
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                  Text(
                    name6,
                    style: TextStyle(
                      color: notifire.getgrey,
                      fontSize: 12,
                      fontFamily: 'Gilroy Medium',
                    ),
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
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                  Text(
                    name3,
                    style: const TextStyle(
                      color: Colors.white,
                      fontFamily: 'Gilroy Medium',
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
