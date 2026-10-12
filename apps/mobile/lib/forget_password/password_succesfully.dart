import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'profile/profile.dart';

class Password_success extends StatefulWidget {
  const Password_success({Key? key}) : super(key: key);

  @override
  _Password_successState createState() => _Password_successState();
}

class _Password_successState extends State<Password_success> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      body: SingleChildScrollView(
        child: Column(
          children: [
            SizedBox(height: MediaQuery.of(context).size.height / 7),
            Center(
              child: Image.asset(
                "image/img1.png",
                height: MediaQuery.of(context).size.height / 7,
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 20),
            const Text(
              "Password reset successful",
              style: TextStyle(
                color: Color(0xffe0e1e4),
                fontSize: 25,
                fontFamily: 'Gilroy Bold',
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 50),
            const Text(
              "Recent Password reset has been",
              style: TextStyle(
                color: Color(0xffe0e1e4),
                fontFamily: 'Gilroy Medium',
              ),
            ),
            const Text(
              "done successfully",
              style: TextStyle(
                fontFamily: 'Gilroy Medium',
                color: Color(0xffe0e1e4),
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 2.5),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 30),
              child: GestureDetector(
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) {
                        return const Profile();
                      },
                    ),
                  );
                },
                child: Container(
                  height: MediaQuery.of(context).size.height / 17,
                  decoration: const BoxDecoration(
                    borderRadius: BorderRadius.all(Radius.circular(20)),
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
                  ),
                  child: const Center(
                    child: Text(
                      "Continue to Account",
                      style: TextStyle(
                        color: Color(0xffe2e3e9),
                        fontFamily: 'Gilroy Bold',
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
    );
  }
}
