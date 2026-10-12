import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:page_transition/page_transition.dart';
import 'package:provider/provider.dart';

import 'betting_know.dart';

class Important_step extends StatefulWidget {
  const Important_step({Key? key}) : super(key: key);

  @override
  _Important_stepState createState() => _Important_stepState();
}

class _Important_stepState extends State<Important_step> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return ScreenUtilInit(
      builder: (context, child) => Scaffold(
        backgroundColor: notifire.getprimerycolor,
        body: SingleChildScrollView(
          child: Scrollbar(
            child: Column(
              children: [
                Stack(
                  children: [
                    Container(
                      color: Colors.pink,
                      height: MediaQuery.of(context).size.height / 4,
                      width: MediaQuery.of(context).size.width,
                      child: Image.asset("image/people.png", fit: BoxFit.cover),
                    ),
                    Column(
                      children: [
                        SizedBox(
                          height: MediaQuery.of(context).size.height / 25,
                        ),
                        Row(
                          children: [
                            SizedBox(
                              width: MediaQuery.of(context).size.width / 50,
                            ),
                            GestureDetector(
                              onTap: () {
                                Navigator.pop(context);
                              },
                              child: Row(
                                children: const [
                                  Icon(Icons.arrow_back, color: Colors.white),
                                  Text(
                                    " Back",
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 12,
                                      fontFamily: 'Gilroy Bold',
                                      fontWeight: FontWeight.bold,
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
                Padding(
                  padding: const EdgeInsets.only(left: 10, right: 10),
                  child: Column(
                    children: [
                      Container(
                        color: Colors.transparent,
                        child: Text(
                          "Important Steps for Sports Betting Deals",
                          style: TextStyle(
                            color: Colors.white,
                            fontFamily: 'Gilroy Bold',
                            fontWeight: FontWeight.w500,
                            fontSize: 22.sp,
                          ),
                        ),
                      ),
                      Row(
                        children: [
                          Text(
                            "Nov 28,4:30 pm",
                            style: TextStyle(
                              fontFamily: 'Gilroy Medium',
                              color: const Color(0xff92a5d1),
                              fontSize: 10.sp,
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 30),
                      Text(
                        "Lorem ipsum dolor sit amet. Vel odio esse sit soluta mollitia aut officiis dignissimos sed consequatur tempora. Aut internos officiis quo nostrum enim vel ratione pariatur sit suscipit perferendis. Ea beatae facere eum pariatur tempore ab libero laborum ut enim sapiente est nemo iste eum fugit recusandae ut quasi sint.",
                        style: TextStyle(
                          fontFamily: 'Gilroy Medium',
                          color: Colors.white,
                          fontSize: 10.sp,
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 80),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: Text(
                          "Sit expedita atque est voluptatem natus ut voluptas et accusantium nulla.",
                          style: TextStyle(
                            fontFamily: 'Gilroy Bold',
                            color: Colors.white,
                            fontSize: 14.sp,
                          ),
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 80),
                      Text(
                        "Lorem ipsum dolor sit amet. Vel tempora. Aut internos officiis quo nostrum enim vel ratione pariatur sit suscipit perferendis. Ea beatae facere eum pariatur tempore ab libero laborum ut enim sapiente est nemo iste eum fugit recusandae ut quasi sint.",
                        style: TextStyle(
                          fontFamily: 'Gilroy Medium',
                          color: Colors.white,
                          fontSize: 10.sp,
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 50),
                      Stack(
                        children: [
                          GestureDetector(
                            onTap: () {
                              Navigator.push(
                                context,
                                PageTransition(
                                  type: PageTransitionType.fade,
                                  child: Betting_know(),
                                ),
                              );
                            },
                            child: Container(
                              color: Colors.transparent,
                              height: MediaQuery.of(context).size.height / 4,
                              width: MediaQuery.of(context).size.width,
                              child: Image.asset(
                                "image/i1.jpg",
                                fit: BoxFit.cover,
                              ),
                            ),
                          ),
                          Center(
                            child: Column(
                              children: [
                                SizedBox(
                                  height:
                                      MediaQuery.of(context).size.height / 10,
                                ),
                                Image.asset(
                                  "image/video.png",
                                  height:
                                      MediaQuery.of(context).size.height / 20,
                                  color: const Color(0xffecedf3),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 50),
                      Text(
                        "Lorem ipsum dolor sit ame . Aut internos officiis quo nostrum enim vel ratione pariatur sit suscipit perferendis. Ea beatae facere eum pariatur tempore ab libero laborum ut enim sapiente est nemo iste eum fugit recusandae ut quasi sint.",
                        style: TextStyle(
                          fontFamily: 'Gilroy Medium',
                          color: Colors.white,
                          fontSize: 10.sp,
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 50),
                      Text(
                        "Lorem ipsum dolor sit ame . Aut internos officiis quo nostrum enim vel ratione pariatur sit suscipit perferendis. Ea beatae facere eum pariatur tempore ab libero laborum ut enim sapiente est nemo iste eum fugit recusandae ut quasi sint.",
                        style: TextStyle(
                          fontFamily: 'Gilroy Medium',
                          color: Colors.white,
                          fontSize: 10.sp,
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 50),
                      Text(
                        "Lorem ipsum dolor sit ame . Aut internos officiis quo nostrum enim vel ratione pariatur sit suscipit perferendis. Ea beatae facere eum pariatur tempore ab libero laborum ut enim sapiente est nemo iste eum fugit recusandae ut quasi sint.",
                        style: TextStyle(
                          fontFamily: 'Gilroy Medium',
                          color: Colors.white,
                          fontSize: 10.sp,
                        ),
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 30),
                      Row(
                        children: [
                          Row(
                            children: [
                              Stack(
                                children: [
                                  CircleAvatar(
                                    backgroundColor: Colors.white,
                                    radius:
                                        MediaQuery.of(context).size.height /
                                        100,
                                    child: CircleAvatar(
                                      radius:
                                          MediaQuery.of(context).size.height /
                                          48,
                                      backgroundColor: Colors.white,
                                      backgroundImage: const AssetImage(
                                        "image/man.png",
                                      ),
                                    ),
                                  ),
                                  Row(
                                    children: [
                                      SizedBox(
                                        width:
                                            MediaQuery.of(context).size.width /
                                            40,
                                      ),
                                      Stack(
                                        children: [
                                          CircleAvatar(
                                            backgroundColor: Colors.white,
                                            radius:
                                                MediaQuery.of(context)
                                                    .size
                                                    .height /
                                                100,
                                            child: CircleAvatar(
                                              radius:
                                                  MediaQuery.of(context)
                                                      .size
                                                      .height /
                                                  48,
                                              backgroundColor: Colors.white,
                                              backgroundImage: const AssetImage(
                                                "image/man.png",
                                              ),
                                            ),
                                          ),
                                          Row(
                                            children: [
                                              SizedBox(
                                                width:
                                                    MediaQuery.of(context)
                                                        .size
                                                        .width /
                                                    40,
                                              ),
                                              Stack(
                                                children: [
                                                  CircleAvatar(
                                                    backgroundColor:
                                                        Colors.white,
                                                    radius:
                                                        MediaQuery.of(context)
                                                            .size
                                                            .height /
                                                        100,
                                                    child: CircleAvatar(
                                                      radius:
                                                          MediaQuery.of(context)
                                                              .size
                                                              .height /
                                                          48,
                                                      backgroundColor:
                                                          Colors.white,
                                                      backgroundImage:
                                                          const AssetImage(
                                                            "image/man.png",
                                                          ),
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
                            ],
                          ),
                          Text(
                            " + 209 Likes",
                            style: TextStyle(
                              color: const Color(0xff8698c6),
                              fontFamily: 'Gilroy Medium',
                              fontSize: 8.sp,
                            ),
                          ),
                          Spacer(),
                          Icon(
                            Icons.message_outlined,
                            size: 11.sp,
                            color: const Color(0xff8698c6),
                          ),
                          Text(
                            " 73 Comments",
                            style: TextStyle(
                              color: const Color(0xff8698c6),
                              fontFamily: 'Gilroy Medium',
                              fontSize: 8.sp,
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: MediaQuery.of(context).size.height / 20),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
