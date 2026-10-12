import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Message extends StatefulWidget {
  const Message({Key? key}) : super(key: key);

  @override
  _MessageState createState() => _MessageState();
}

class _MessageState extends State<Message> {
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
          "Message",
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
            Container(
              color: Colors.transparent,
              height: MediaQuery.of(context).size.height / 1.35,
              child: SingleChildScrollView(
                child: Column(
                  children: [
                    SizedBox(height: MediaQuery.of(context).size.height / 50),
                    const Text(
                      "Today at 7:20 PM",
                      style: TextStyle(
                        fontFamily: 'Gilroy Medium',
                        color: Color(0xff8da0cf),
                        fontSize: 12,
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 20),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: Chat(),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 50),
                    Padding(
                      padding: const EdgeInsets.only(right: 20),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          Container(
                            height: MediaQuery.of(context).size.height / 20,
                            width: MediaQuery.of(context).size.width / 3,
                            decoration: const BoxDecoration(
                              gradient: LinearGradient(
                                begin: Alignment.centerLeft,
                                end: Alignment.centerRight,
                                colors: [
                                  Color(0xff3030b2),
                                  Color(0xff322e9e),
                                  Color(0xff4b32b4),
                                  Color(0xff5233b4),
                                  Color(0xff492f9a),
                                ],
                              ),
                              borderRadius: BorderRadius.only(
                                topRight: Radius.circular(15),
                                bottomLeft: Radius.circular(15),
                              ),
                            ),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  SizedBox(
                                    height:
                                        MediaQuery.of(context).size.height / 80,
                                  ),
                                  const Text(
                                    "Nulla sit amet",
                                    style: TextStyle(
                                      fontFamily: 'Gilroy Medium',
                                      fontSize: 12,
                                      color: Color(0xff899bc5),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 50),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: Chat(),
                    ),
                  ],
                ),
              ),
            ),
            // SizedBox(
            //   height: MediaQuery.of(context).size.height / 80,
            // ),
            Padding(
              padding: const EdgeInsets.only(left: 20),
              child: Row(
                children: [
                  Container(
                    color: Colors.transparent,
                    height: MediaQuery.of(context).size.height / 17,
                    width: MediaQuery.of(context).size.width / 1.3,
                    child: TextField(
                      textAlign: TextAlign.left,
                      style: TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(30),
                          borderSide: const BorderSide(
                            width: 0,
                            style: BorderStyle.none,
                          ),
                        ),
                        filled: true,
                        fillColor: const Color(0xff181c35),
                      ),
                    ),
                  ),
                  SizedBox(width: MediaQuery.of(context).size.width / 30),
                  const Icon(Icons.send, color: Color(0xff5233b4)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget Chat() {
    return Row(
      children: [
        Image.asset(
          "image/profile.png",
          height: MediaQuery.of(context).size.height / 15,
        ),
        SizedBox(width: MediaQuery.of(context).size.width / 40),
        Container(
          height: MediaQuery.of(context).size.height / 15,
          width: MediaQuery.of(context).size.width / 2.3,
          decoration: const BoxDecoration(
            color: Color(0xff181c35),
            borderRadius: BorderRadius.only(
              topRight: Radius.circular(15),
              bottomLeft: Radius.circular(15),
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(height: MediaQuery.of(context).size.height / 100),
                const Text(
                  "Nulla sit amet faucibus ex,",
                  style: TextStyle(
                    fontFamily: 'Gilroy Medium',
                    fontSize: 12,
                    color: Color(0xff899bc5),
                  ),
                ),
                const Text(
                  "ut laoreet erat.",
                  style: TextStyle(
                    fontFamily: 'Gilroy Medium',
                    fontSize: 12,
                    color: Color(0xff899bc5),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
