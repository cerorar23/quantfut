import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Wallet_empty extends StatefulWidget {
  const Wallet_empty({Key? key}) : super(key: key);

  @override
  _Wallet_emptyState createState() => _Wallet_emptyState();
}

class _Wallet_emptyState extends State<Wallet_empty> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      body: Column(
        children: [
          SizedBox(height: MediaQuery.of(context).size.height / 6),
          Container(
            height: MediaQuery.of(context).size.height / 3,
            decoration: BoxDecoration(
              color: notifire.getmediumblue,
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
          SizedBox(height: MediaQuery.of(context).size.height / 8),
          const Text(
            "Your wallet is empty",
            style: TextStyle(
              color: Color(0xfff6f6f5),
              fontSize: 30,
              fontFamily: 'Gilroy Bold',
            ),
          ),
          SizedBox(height: MediaQuery.of(context).size.height / 70),
          const Text(
            "Look like there are no credits in your",
            style: TextStyle(
              fontFamily: 'Gilroy Medium',
              color: Color(0xffe6eef7),
            ),
          ),
          const Text(
            "wallet at the moment",
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
