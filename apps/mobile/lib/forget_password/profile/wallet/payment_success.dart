import 'package:gobet/sign_in/home_screen/matches/matches.dart';
import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Payment_success extends StatefulWidget {
  const Payment_success({Key? key}) : super(key: key);

  @override
  _Payment_successState createState() => _Payment_successState();
}

class _Payment_successState extends State<Payment_success> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      body: SingleChildScrollView(
        child: Column(
          children: [
            SizedBox(height: MediaQuery.of(context).size.height / 9),
            Text(
              "Your payment Method has",
              style: const TextStyle(
                color: Color(0xfff6f6f5),
                fontFamily: 'Gilroy Bold',
              ),
            ),
            const Text(
              "been successfully added",
              style: TextStyle(
                color: Color(0xfff6f6f5),
                fontFamily: 'Gilroy Bold',
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 9),
            Container(
              height: MediaQuery.of(context).size.height / 4,
              decoration: BoxDecoration(
                color: notifire.getlightblue,
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Image.asset(
                  "image/wallet.png",
                  height: MediaQuery.of(context).size.height / 6,
                  color: Color(0xff8c9acb),
                ),
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 4),

            const Text(
              "Now you save a lot of time by adding",
              style: TextStyle(
                fontFamily: 'Gilroy Medium',
                color: Color(0xffe6eef7),
              ),
            ),
            const Text(
              "transactions automatically",
              style: TextStyle(
                fontFamily: 'Gilroy Medium',
                color: Color(0xffe6eef7),
              ),
            ),
            SizedBox(height: MediaQuery.of(context).size.height / 20),
            GestureDetector(
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) {
                      return Matches();
                    },
                  ),
                );
              },
              child: Container(
                height: MediaQuery.of(context).size.height / 23,
                width: MediaQuery.of(context).size.width / 1.7,
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
                    "Return to Home",
                    style: TextStyle(
                      color: Color(0xffe2e3e9),
                      fontFamily: 'Gilroy Bold',
                      fontSize: 12,
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
