import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Participated extends StatefulWidget {
  const Participated({Key? key}) : super(key: key);

  @override
  _ParticipatedState createState() => _ParticipatedState();
}

class _ParticipatedState extends State<Participated> {
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
          "Participated",
          style: TextStyle(
            color: notifire.getwhite,
            fontFamily: 'Gilroy Medium',
            fontSize: 18,
          ),
        ),
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            children: [
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Users("Shane Jimenez", "\$99.00"),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Users("Hazel Meyer", "\$90.00"),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Users("Adam Horton", "\$86.00"),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Users("Wade Ramos", "\$12.00"),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Users("Neil Coleman", "\$32.00"),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Users("Kay Gibson", "\$39.00"),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Users("Ollie Adams", "\$99.00"),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
            ],
          ),
        ),
      ),
    );
  }

  Widget Users(name1, name2) {
    return Container(
      height: MediaQuery.of(context).size.height / 8,
      decoration: const BoxDecoration(
        color: Color(0xff252a4a),
        borderRadius: BorderRadius.all(Radius.circular(15)),
      ),
      child: Column(
        children: [
          SizedBox(height: MediaQuery.of(context).size.height / 50),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Row(
              children: [
                Image.asset(
                  "image/profile.png",
                  height: MediaQuery.of(context).size.height / 12,
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 40),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name1,
                      style: const TextStyle(
                        color: Color(0xfff7f8f9),
                        fontWeight: FontWeight.w700,
                        fontSize: 17,
                      ),
                    ),
                    SizedBox(height: MediaQuery.of(context).size.height / 200),
                    const Text(
                      "27 mins ago",
                      style: TextStyle(
                        color: Color(0xff5465a0),
                        fontSize: 12,
                        fontFamily: 'Gilroy Bold',
                      ),
                    ),
                  ],
                ),
                Spacer(),
                Column(
                  children: [
                    Text(
                      name2,
                      style: const TextStyle(
                        color: Color(0xff7a69fa),
                        fontSize: 21,
                        fontFamily: 'Gilroy Bold',
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
