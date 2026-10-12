import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Chat_history extends StatefulWidget {
  const Chat_history({Key? key}) : super(key: key);

  @override
  _Chat_historyState createState() => _Chat_historyState();
}

class _Chat_historyState extends State<Chat_history> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      body: SingleChildScrollView(
        child: Column(
          children: [
            SizedBox(height: MediaQuery.of(context).size.height / 20),
            Row(
              children: [
                SizedBox(width: MediaQuery.of(context).size.width / 40),
                GestureDetector(
                  onTap: () {
                    Navigator.pop(context);
                  },
                  child: Icon(Icons.arrow_back, color: Colors.white),
                ),
              ],
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 7),
            Container(
              height: MediaQuery.of(context).size.height / 3,
              decoration: BoxDecoration(
                color: notifire.getlightblue,
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Image.asset(
                  "image/chat.png",
                  height: MediaQuery.of(context).size.height / 6,
                  color: const Color(0xff8c9acb),
                ),
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 8),
            const Text(
              "No Chat History",
              style: TextStyle(
                color: Color(0xfff6f6f5),
                fontSize: 30,
                fontFamily: 'Gilroy Bold',
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 70),
            const Text(
              "No message in your inbox,yet ! start",
              style: TextStyle(
                fontFamily: 'Gilroy Medium',
                color: Color(0xffe6eef7),
              ),
            ),
            const Text(
              "chatting with people around you.",
              style: TextStyle(
                fontFamily: 'Gilroy Medium',
                color: Color(0xffe6eef7),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
