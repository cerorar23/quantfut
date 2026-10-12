import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../../utils/color_notifire.dart';

class Add_bank extends StatefulWidget {
  const Add_bank({Key? key}) : super(key: key);

  @override
  _Add_bankState createState() => _Add_bankState();
}

class _Add_bankState extends State<Add_bank> {
  final int _numPages = 3;
  final PageController _pageController = PageController(initialPage: 0);
  int _currentPage = 0;

  List<Widget> _buildPageIndicator() {
    List<Widget> list = [];
    for (int i = 0; i < _numPages; i++) {
      list.add(i == _currentPage ? _indicator(true) : _indicator(false));
    }
    return list;
  }

  Widget _indicator(bool isActive) {
    return AnimatedContainer(
      duration: const Duration(microseconds: 150),
      margin: const EdgeInsets.symmetric(horizontal: 3.0),
      height: 8.0,
      width: isActive ? 8.0 : 8.0,
      decoration: BoxDecoration(
        color: isActive ? notifire.getwhite : notifire.getgrey,
        borderRadius: const BorderRadius.all(Radius.circular(12)),
      ),
    );
  }

  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      body: AnnotatedRegion<SystemUiOverlayStyle>(
        value: SystemUiOverlayStyle.light,
        child: SingleChildScrollView(
          child: Container(
            height: MediaQuery.of(context).size.height,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                SizedBox(height: MediaQuery.of(context).size.height / 20),
                Row(
                  children: [
                    SizedBox(width: MediaQuery.of(context).size.width / 30),
                    GestureDetector(
                      onTap: () {
                        Navigator.pop(context);
                      },
                      child: Icon(Icons.arrow_back, color: notifire.getwhite),
                    ),
                    SizedBox(width: MediaQuery.of(context).size.width / 3),
                    Text(
                      "Add Payment",
                      style: TextStyle(
                        color: notifire.getwhite,
                        fontFamily: 'Gilroy Medium',
                      ),
                    ),
                  ],
                ),
                SizedBox(height: MediaQuery.of(context).size.height / 50),
                Container(
                  height: MediaQuery.of(context).size.height / 2.5,
                  child: PageView(
                    physics: const ClampingScrollPhysics(),
                    controller: _pageController,
                    onPageChanged: (int page) {
                      setState(() {
                        _currentPage = page;
                      });
                    },
                    children: <Widget>[
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: Image.asset("image/credit-card.png"),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: Image.asset("image/credit-card.png"),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: Image.asset("image/credit-card.png"),
                      ),
                    ],
                  ),
                ),

                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: _buildPageIndicator(),
                ),
                SizedBox(height: MediaQuery.of(context).size.height / 30),
                textf("image/icon_Name Account.png", "Name Account"),
                SizedBox(height: MediaQuery.of(context).size.height / 40),
                textf("image/bank.png", "Bank Name"),
                SizedBox(height: MediaQuery.of(context).size.height / 40),
                textf("image/swift code.png", "Swift Code"),
                SizedBox(height: MediaQuery.of(context).size.height / 40),
                textf("image/account_number.png", "Account Number"),
                SizedBox(height: MediaQuery.of(context).size.height / 20),

                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 30),
                  child: Container(
                    height: MediaQuery.of(context).size.height / 17,
                    width: MediaQuery.of(context).size.width / 1.2,
                    decoration: const BoxDecoration(
                      borderRadius: BorderRadius.all(Radius.circular(20)),
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
                    child: Center(
                      child: Text(
                        "Add Bank",
                        style: TextStyle(
                          fontFamily: 'Gilroy Medium',
                          color: notifire.getwhite,
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),
                    ),
                  ),
                ),
                _currentPage != _numPages
                    ? Expanded(
                        child: Align(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 20.0,
                            ),
                          ),
                        ),
                      )
                    : const Text(''),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget textf(img, name1) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 30),
      child: Container(
        height: MediaQuery.of(context).size.height / 17,
        width: MediaQuery.of(context).size.width / 1.1,
        child: TextField(
          style: TextStyle(color: notifire.getwhite),
          textAlign: TextAlign.left,
          decoration: InputDecoration(
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(30),
              borderSide: const BorderSide(width: 0, style: BorderStyle.none),
            ),
            fillColor: notifire.getlightblue,
            hintStyle: TextStyle(
              fontFamily: 'Gilroy Medium',
              color: notifire.getgrey,
              fontSize: 14,
            ),
            hintText: name1,
            filled: true,
            prefixIcon: Padding(
              padding: const EdgeInsets.all(10.0),
              child: Image.asset(img, color: Color(0xffafb9cf)),
            ),
          ),
        ),
      ),
    );
  }
}
