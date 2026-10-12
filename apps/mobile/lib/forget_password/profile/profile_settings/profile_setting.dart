import 'package:gobet/forget_password/profile/profile_settings/user_profile_setting/user_profile.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

class Profile_setting extends StatefulWidget {
  const Profile_setting({Key? key}) : super(key: key);

  @override
  _Profile_settingState createState() => _Profile_settingState();
}

class _Profile_settingState extends State<Profile_setting> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      appBar: AppBar(
        backgroundColor: notifire.getlightblue,
        iconTheme: IconThemeData(color: Colors.white),
        centerTitle: true,
        title: Text(
          "Profile Setting",
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
            Column(
              children: [
                Stack(
                  children: [
                    Center(
                      child: Image.asset(
                        "image/profile.png",
                        height: MediaQuery.of(context).size.height / 5,
                      ),
                    ),
                    Column(
                      children: [
                        SizedBox(
                          height: MediaQuery.of(context).size.height / 8,
                        ),
                        Row(
                          children: [
                            SizedBox(
                              width: MediaQuery.of(context).size.width / 1.9,
                            ),
                            Image.asset(
                              "image/icon_camera bold.png",
                              height: MediaQuery.of(context).size.height / 20,
                            ),
                          ],
                        ),
                        Column(
                          children: [
                            Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 20,
                              ),
                              child: Column(
                                children: [
                                  SizedBox(
                                    height:
                                        MediaQuery.of(context).size.height / 10,
                                  ),
                                  Padding(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 20,
                                    ),
                                    child: Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.spaceBetween,
                                      children: [
                                        Text3("First Name"),
                                        Text3("Last Name"),
                                      ],
                                    ),
                                  ),
                                  SizedBox(
                                    height:
                                        MediaQuery.of(context).size.height / 40,
                                  ),
                                  Padding(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 20,
                                    ),
                                    child: Text4(
                                      "Email",
                                      "image/icon14.png",
                                      const EdgeInsets.symmetric(
                                        horizontal: 12,
                                        vertical: 15,
                                      ),
                                    ),
                                  ),
                                  SizedBox(
                                    height:
                                        MediaQuery.of(context).size.height / 40,
                                  ),
                                  Padding(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 20,
                                    ),
                                    child: Text4(
                                      "Phone Number",
                                      "image/icon15.png",
                                      const EdgeInsets.symmetric(
                                        horizontal: 12,
                                        vertical: 15,
                                      ),
                                    ),
                                  ),
                                  SizedBox(
                                    height:
                                        MediaQuery.of(context).size.height / 40,
                                  ),
                                  Padding(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 20,
                                    ),
                                    child: text5(),
                                  ),
                                  SizedBox(
                                    height:
                                        MediaQuery.of(context).size.height / 20,
                                  ),
                                  Padding(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 20,
                                    ),
                                    child: GestureDetector(
                                      onTap: () {
                                        Navigator.push(
                                          context,
                                          PageTransition(
                                            type: PageTransitionType.fade,
                                            child: User_profile(),
                                          ),
                                        );
                                      },
                                      child: Container(
                                        height:
                                            MediaQuery.of(context).size.height /
                                            17,
                                        decoration: const BoxDecoration(
                                          borderRadius: BorderRadius.all(
                                            Radius.circular(20),
                                          ),
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
                                        child: const Center(
                                          child: Text(
                                            "Save",
                                            style: TextStyle(
                                              fontFamily: 'Gilroy Bold',
                                              color: Color(0xffe2e3e9),

                                              fontSize: 20,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget Text3(name) {
    return Container(
      color: Colors.transparent,
      height: MediaQuery.of(context).size.height / 17,
      width: MediaQuery.of(context).size.width / 2.6,
      child: TextField(
        style: TextStyle(color: Colors.white),
        textAlign: TextAlign.left,
        decoration: InputDecoration(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(30),
            borderSide: const BorderSide(width: 0, style: BorderStyle.none),
          ),
          filled: true,
          hintStyle: const TextStyle(
            fontFamily: 'Gilroy Medium',
            color: Color(0xffe2e3e9),
            fontSize: 12,
          ),
          hintText: name,
          fillColor: const Color(0xff2f3a66),
          prefixIcon: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 13),
            child: Image.asset("image/icon10.png", color: Colors.white),
          ),
        ),
      ),
    );
  }

  Widget Text4(name, img, paddi) {
    return Container(
      color: Colors.transparent,
      height: MediaQuery.of(context).size.height / 17,
      child: TextField(
        style: TextStyle(color: Colors.white),
        textAlign: TextAlign.left,
        decoration: InputDecoration(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(30),
            borderSide: const BorderSide(width: 0, style: BorderStyle.none),
          ),
          filled: true,
          hintStyle: const TextStyle(
            fontFamily: 'Gilroy Medium',
            color: Color(0xffe2e3e9),
            fontSize: 12,
          ),
          hintText: name,
          fillColor: const Color(0xff2f3a66),
          prefixIcon: Padding(
            padding: paddi,
            child: Image.asset(img, color: Colors.white),
          ),
        ),
      ),
    );
  }

  Widget text5() {
    return Container(
      color: Colors.transparent,
      height: MediaQuery.of(context).size.height / 17,
      child: TextField(
        textAlign: TextAlign.left,
        decoration: InputDecoration(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(30),
            borderSide: const BorderSide(width: 0, style: BorderStyle.none),
          ),
          filled: true,
          hintStyle: const TextStyle(
            fontFamily: 'Gilroy Medium',
            color: Color(0xffe2e3e9),
            fontSize: 13,
          ),
          hintText: "Male",
          fillColor: const Color(0xff2f3a66),
          suffixIcon: const Icon(
            Icons.arrow_drop_down,
            color: Color(0xff989bb2),
            size: 25,
          ),
          prefixIcon: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
            child: Image.asset("image/icon16.png", color: Colors.white),
          ),
        ),
      ),
    );
  }
}
