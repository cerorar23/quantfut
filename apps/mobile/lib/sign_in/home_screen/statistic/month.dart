import 'package:fl_chart/fl_chart.dart';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../utils/color_notifire.dart';

class Month extends StatefulWidget {
  const Month({Key? key}) : super(key: key);

  @override
  _MonthState createState() => _MonthState();
}

class _MonthState extends State<Month> {
  List<Color> gradientColors = [
    const Color(0xffa75cc0),
    const Color(0xff6a438b),
    const Color(0xff4b3976),
    const Color(0xff5f4eae),
    const Color(0xff7056c4),
  ];

  bool showAvg = false;
  final int _numPages = 2;
  final PageController _pageController = PageController(initialPage: 0);

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  int _currentPage = 0;
  int touchedIndex = -1;

  List<PieChartSectionData> showingSections({required int i}) {
    var currentWidth = MediaQuery.of(context).size.width;
    var extraScreenGrid = currentWidth > 1536;
    var largeScreenGrid = currentWidth > 1366;
    var smallScreenGrid = currentWidth > 1201;
    var extraSmallScreenGrid = currentWidth > 1025;
    var tabScreenGrid = currentWidth > 769;
    var mobileScreenGrid = currentWidth > 481;

    return List.generate(7, (i) {
      final isTouched = i == touchedIndex;
      final fontSize = isTouched ? 25.0 : 16.0;
      final radius = isTouched
          ? extraScreenGrid
                ? 145.0
                : largeScreenGrid
                ? 120.0
                : smallScreenGrid
                ? 200.0
                : extraSmallScreenGrid
                ? 165.0
                : tabScreenGrid
                ? 175.0
                : mobileScreenGrid
                ? 95.0
                : 85.0
          : extraScreenGrid
          ? 140.0
          : largeScreenGrid
          ? 115.0
          : smallScreenGrid
          ? 195.0
          : extraSmallScreenGrid
          ? 160.0
          : tabScreenGrid
          ? 170.0
          : mobileScreenGrid
          ? 90.0
          : 80.0;
      switch (i) {
        case 0:
          return PieChartSectionData(
            color: Colors.blue,
            value: 40,
            title: '40%',
            radius: radius,
            titleStyle: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.bold,
              color: const Color(0xffffffff),
            ),
          );
        case 1:
          return PieChartSectionData(
            color: Colors.red,
            value: 30,
            title: '30%',
            radius: radius,
            titleStyle: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.bold,
              color: const Color(0xffffffff),
            ),
          );
        case 2:
          return PieChartSectionData(
            color: Colors.indigo,
            value: 15,
            title: '15%',
            radius: radius,
            titleStyle: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.bold,
              color: const Color(0xffffffff),
            ),
          );
        case 3:
          return PieChartSectionData(
            color: Colors.blueGrey,
            value: 19,
            title: '15%',
            radius: radius,
            titleStyle: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.bold,
              color: const Color(0xffffffff),
            ),
          );
        case 4:
          return PieChartSectionData(
            color: Colors.brown,
            value: 05,
            title: '15%',
            radius: radius,
            titleStyle: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.bold,
              color: const Color(0xffffffff),
            ),
          );
        case 5:
          return PieChartSectionData(
            color: Colors.orange,
            value: 15,
            title: '15%',
            radius: radius,
            titleStyle: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.bold,
              color: const Color(0xffffffff),
            ),
          );
        case 6:
          return PieChartSectionData(
            color: Colors.purple,
            value: 15,
            title: '15%',
            radius: radius,
            titleStyle: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.bold,
              color: const Color(0xffffffff),
            ),
          );

        default:
          throw Error();
      }
    });
  }

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
      height: MediaQuery.of(context).size.height / 10,
      width: isActive ? 0 : 0,
      decoration: BoxDecoration(
        color: isActive ? const Color(0xff22c0ff) : const Color(0xff474e84),
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
      body: Column(
        children: [
          SizedBox(height: MediaQuery.of(context).size.height / 20),
          Container(
            color: Colors.transparent,
            height: MediaQuery.of(context).size.height / 3.3,
            child: PageView(
              physics: const ClampingScrollPhysics(),
              controller: _pageController,
              onPageChanged: (int page) {
                setState(() {
                  _currentPage = page;
                });
              },
              children: <Widget>[
                Container(
                  color: Colors.transparent,
                  width: MediaQuery.of(context).size.width,
                  height: MediaQuery.of(context).size.height / 3,
                  child: Row(
                    children: <Widget>[
                      Expanded(
                        flex: 3,
                        child: PieChart(
                          PieChartData(
                            pieTouchData: PieTouchData(),
                            borderData: FlBorderData(show: false),
                            sectionsSpace: 01,
                            centerSpaceRadius: 20,
                            sections: showingSections(i: 1),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                InkWell(
                  onHover: (value) {
                    setState(() {
                      touchedIndex = -1;
                    });
                  },
                  hoverColor: Colors.white,
                  onTap: () {},
                  child: Container(
                    color: Colors.transparent,
                    child: LineChart(mainData()),
                  ),
                ),
              ],
            ),
          ),
          SizedBox(height: MediaQuery.of(context).size.height / 60),
          Center(
            child: Row(
              children: [
                SizedBox(width: MediaQuery.of(context).size.width / 5),
                Container(
                  height: MediaQuery.of(context).size.height / 23,
                  width: MediaQuery.of(context).size.width / 4,
                  decoration: BoxDecoration(
                    border: Border.all(color: const Color(0xff8f94b0)),
                    borderRadius: const BorderRadius.all(Radius.circular(20)),
                  ),
                  child: const Center(
                    child: Text(
                      "Liner",
                      style: TextStyle(
                        fontFamily: 'Gilroy Bold',
                        color: Color(0xffe2e3e9),
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 30),
                Container(
                  height: MediaQuery.of(context).size.height / 23,
                  width: MediaQuery.of(context).size.width / 4,
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
                      "Radial",
                      style: TextStyle(
                        fontFamily: 'Gilroy Bold',
                        color: Color(0xffe2e3e9),
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          SizedBox(height: MediaQuery.of(context).size.height / 40),
          Row(
            children: [
              SizedBox(width: MediaQuery.of(context).size.width / 5),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "0,2\$",
                    style: TextStyle(
                      fontFamily: 'Gilroy Bold',
                      color: Colors.white,
                      fontSize: 30,
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                  const Text(
                    "Average /hour",
                    style: TextStyle(
                      fontFamily: 'Gilroy Medium',
                      color: Color(0xffa7bef5),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
              SizedBox(width: MediaQuery.of(context).size.width / 10),
              Container(
                width: MediaQuery.of(context).size.width / 500,
                height: MediaQuery.of(context).size.height / 10,
                color: Colors.white,
              ),
              SizedBox(width: MediaQuery.of(context).size.width / 10),
              Column(
                children: [
                  const Text(
                    "4,8\$",
                    style: TextStyle(
                      fontFamily: 'Gilroy Bold',
                      color: Colors.white,
                      fontSize: 30,
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                  const Text(
                    "Total /day",
                    style: TextStyle(
                      fontFamily: 'Gilroy Medium',
                      color: Color(0xffa7bef5),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ],
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: _buildPageIndicator(),
          ),
          _currentPage != _numPages
              ? const Expanded(
                  child: Align(
                    child: Padding(
                      padding: EdgeInsets.symmetric(horizontal: 20.0),
                    ),
                  ),
                )
              : const Text(''),
        ],
      ),
    );
  }

  LineChartData mainData() {
    return LineChartData(
      gridData: FlGridData(
        show: true,
        drawVerticalLine: true,
        getDrawingHorizontalLine: (value) {
          return FlLine(strokeWidth: 1, color: Color(0xff4f5880));
        },
        getDrawingVerticalLine: (value) {
          return FlLine(strokeWidth: 0);
        },
      ),
      titlesData: FlTitlesData(
        show: true,
        // bottomTitles: SideTitles(
        //   showTitles: true,
        //   reservedSize: 22,
        //   // getTextStyles: (value) =>  TextStyle(
        //   //     color: Colors.black45, fontWeight: FontWeight.bold, fontSize: 16),
        //   getTitles: (value) {
        //     switch (value.toInt()) {
        //       case 0:
        //         return 'Jan';
        //       case 1:
        //         return 'Fab';
        //       case 2:
        //         return 'Mar';
        //       case 3:
        //         return 'Apr';
        //       case 4:
        //         return 'May';
        //       case 5:
        //         return 'Jun';
        //       case 6:
        //         return 'Jul';
        //       case 7:
        //         return 'Aug';
        //       case 8:
        //         return 'Sep';
        //       case 9:
        //         return 'Oct';
        //     }
        //     return '';
        //   },
        //   margin: 10,
        // ),
      ),
      borderData: FlBorderData(
        show: true,
        border: Border.all(color: const Color(0xff37434d), width: 0),
      ),
      minX: 0,
      maxX: 10,
      minY: 0,
      maxY: 5,
      lineBarsData: [
        LineChartBarData(
          spots: [
            FlSpot(0, 2.5),
            FlSpot(1, 2),
            FlSpot(2, 4),
            FlSpot(3, 3.1),
            FlSpot(4, 4),
            FlSpot(5, 2),
            FlSpot(6, 4),
            FlSpot(7, 3.1),
            FlSpot(8, 2),
            FlSpot(9, 1.5),
            FlSpot(10, 3),
          ],
          isCurved: true,
          barWidth: 2,
          isStrokeCapRound: true,
          dotData: FlDotData(show: false),
          belowBarData: BarAreaData(show: true),
        ),
      ],
    );
  }
}
