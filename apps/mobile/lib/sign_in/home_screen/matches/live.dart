import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Live extends StatefulWidget {
  const Live({Key? key}) : super(key: key);

  @override
  _LiveState createState() => _LiveState();
}

class _LiveState extends State<Live> {
  late ColorNotifire notifire;
  int selected = 0;
  int selected1 = 0;
  bool _isVisible = false;
  bool _Visible = false;
  bool _show = false;
  bool _hide = false;
  bool _select = false;

  void showToast() {
    setState(() {
      _isVisible = !_isVisible;
    });
  }

  void Toast() {
    setState(() {
      _Visible = !_Visible;
    });
  }

  void Show() {
    setState(() {
      _show = !_show;
    });
  }

  void Hide() {
    setState(() {
      _hide = !_hide;
    });
  }

  void Select() {
    setState(() {
      _select = !_select;
    });
  }

  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      extendBodyBehindAppBar: false,
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
                                  "1",
                                  "0",
                                  "5 mins",
                                  _isVisible,
                                  showToast,
                                  "1.48",
                                  "Match Winner",
                                  "0.96",
                                  "0.96",
                                  "Team 1 accepts",
                                  "0.66",
                                  "0.32",
                                  "Ream 2 accepts",
                                  "0.52",
                                ),
                                SizedBox(
                                  height:
                                      MediaQuery.of(context).size.height / 100,
                                ),
                                League(
                                  "A-League B02",
                                  "Taurora",
                                  "Roshan",
                                  "image/logo_4.png",
                                  "image/logo_8.png",
                                  "0",
                                  "0",
                                  "30 mins",
                                  _hide,
                                  Hide,
                                  "1.48",
                                  "Match Winner",
                                  "0.96",
                                  "0.96",
                                  "Team 1 accepts",
                                  "0.66",
                                  "0.32",
                                  "Ream 2 accepts",
                                  "0.52",
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
                                  "Kingguin",
                                  "Kingdra",
                                  "image/logo_6.png",
                                  "image/logo_7.png",
                                  "0",
                                  "3",
                                  "40 mins",
                                  _Visible,
                                  Toast,
                                  "1.48",
                                  "Match Winner",
                                  "0.96",
                                  "0.96",
                                  "Team 1 accepts",
                                  "0.66",
                                  "0.32",
                                  "Ream 2 accepts",
                                  "0.52",
                                ),
                                SizedBox(
                                  height:
                                      MediaQuery.of(context).size.height / 100,
                                ),
                                League(
                                  "A-League B02",
                                  "Eclipse",
                                  "Secret",
                                  "image/logo_9.png",
                                  "image/logo_10.png",
                                  "1",
                                  "0",
                                  "5 mins",
                                  _show,
                                  Show,
                                  "1.48",
                                  "Match Winner",
                                  "0.96",
                                  "0.96",
                                  "Team 1 accepts",
                                  "0.66",
                                  "0.32",
                                  "Ream 2 accepts",
                                  "0.52",
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
          ],
        ),
      ),
    );
  }

  Widget League(
    name1,
    name2,
    name3,
    img1,
    img2,
    name4,
    name5,
    name6,
    visi,
    tap,
    name7,
    name8,
    name9,
    name10,
    name11,
    name12,
    name13,
    name14,
    name15,
  ) {
    return Stack(
      children: [
        Container(
          height: MediaQuery.of(context).size.height / 6,
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
                      SizedBox(
                        height: MediaQuery.of(context).size.height / 100,
                      ),
                      Text(
                        name2,
                        style: const TextStyle(
                          color: Colors.white,
                          fontFamily: 'Gilroy Medium',
                        ),
                      ),
                      SizedBox(
                        height: MediaQuery.of(context).size.height / 100,
                      ),
                    ],
                  ),
                  Column(
                    children: [
                      SizedBox(
                        height: MediaQuery.of(context).size.height / 100,
                      ),
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
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 20,
                          ),
                          Image.asset(
                            "image/icon_time.png",
                            height: MediaQuery.of(context).size.height / 40,
                          ),
                          SizedBox(
                            width: MediaQuery.of(context).size.width / 20,
                          ),
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
                      SizedBox(height: MediaQuery.of(context).size.height / 50),
                      Text(
                        name6,
                        style: TextStyle(
                          color: notifire.getgrey,
                          fontSize: 12,
                          fontFamily: 'Gilroy Medium',
                        ),
                      ),
                      SizedBox(
                        height: MediaQuery.of(context).size.height / 100,
                      ),
                    ],
                  ),
                  Column(
                    children: [
                      Image.asset(
                        img2,
                        height: MediaQuery.of(context).size.height / 15,
                      ),
                      SizedBox(
                        height: MediaQuery.of(context).size.height / 100,
                      ),
                      Text(
                        name3,
                        style: const TextStyle(
                          color: Colors.white,
                          fontFamily: 'Gilroy Medium',
                        ),
                      ),
                      SizedBox(
                        height: MediaQuery.of(context).size.height / 100,
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
        Column(
          children: [
            SizedBox(height: MediaQuery.of(context).size.height / 7.3),
            GestureDetector(
              onTap: tap,
              child: Center(
                child: Container(
                  height: MediaQuery.of(context).size.height / 20,
                  width: MediaQuery.of(context).size.width / 12,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: notifire.getlightblue,
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(10),
                    child: Image.asset(
                      "image/down_arrow.png",
                      color: notifire.getwhite,
                    ),
                  ),
                ),
              ),
            ),
            Visibility(
              visible: visi,
              child: Container(
                decoration: BoxDecoration(
                  color: notifire.getlightblue,
                  borderRadius: const BorderRadius.all(Radius.circular(15)),
                ),
                height: MediaQuery.of(context).size.height / 7.2,
                child: Column(
                  children: [
                    SizedBox(height: MediaQuery.of(context).size.height / 100),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        Text(
                          "1.48",
                          style: TextStyle(
                            color: notifire.getwhite,
                            fontFamily: "Gilroy Medium",
                          ),
                        ),
                        Text(
                          "Match Winner",
                          style: TextStyle(
                            color: notifire.getgrey,
                            fontFamily: "Gilroy Medium",
                          ),
                        ),
                        Text(
                          "1.48",
                          style: TextStyle(
                            color: notifire.getwhite,
                            fontFamily: "Gilroy Medium",
                          ),
                        ),
                      ],
                    ),
                    Divider(color: notifire.getmediumblue, thickness: 1),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        Text(
                          "1.48",
                          style: TextStyle(
                            color: notifire.getwhite,
                            fontFamily: "Gilroy Medium",
                          ),
                        ),
                        Text(
                          "Match Winner",
                          style: TextStyle(
                            color: notifire.getgrey,
                            fontFamily: "Gilroy Medium",
                          ),
                        ),
                        Text(
                          "1.48",
                          style: TextStyle(
                            color: notifire.getwhite,
                            fontFamily: "Gilroy Medium",
                          ),
                        ),
                      ],
                    ),
                    Divider(color: notifire.getmediumblue, thickness: 1),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        Text(
                          "1.48",
                          style: TextStyle(
                            color: notifire.getwhite,
                            fontFamily: "Gilroy Medium",
                          ),
                        ),
                        Text(
                          "Match Winner",
                          style: TextStyle(
                            color: notifire.getgrey,
                            fontFamily: "Gilroy Medium",
                          ),
                        ),
                        Text(
                          "1.48",
                          style: TextStyle(
                            color: notifire.getwhite,
                            fontFamily: "Gilroy Medium",
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
