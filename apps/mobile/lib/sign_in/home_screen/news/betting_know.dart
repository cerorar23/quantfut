import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:provider/provider.dart';

class Betting_know extends StatefulWidget {
  const Betting_know({Key? key}) : super(key: key);

  @override
  _Betting_knowState createState() => _Betting_knowState();
}

class _Betting_knowState extends State<Betting_know> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return ScreenUtilInit(
      builder: (context, child) => Scaffold(
        backgroundColor: notifire.getprimerycolor,
        body: SingleChildScrollView(
          child: Column(
            children: [
              SizedBox(height: MediaQuery.of(context).size.height / 25),
              Row(
                children: [
                  SizedBox(width: MediaQuery.of(context).size.width / 50),
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
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 50),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Container(
                  color: Colors.transparent,
                  child: Text(
                    "Online Sports Betting Tips You Need to Know",
                    style: TextStyle(
                      color: Colors.white,
                      fontFamily: 'Gilroy Bold',
                      fontSize: 22.sp,
                    ),
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 50),
              Stack(
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: ClipRRect(
                      borderRadius: const BorderRadius.all(Radius.circular(15)),
                      child: Container(
                        color: Colors.transparent,
                        height: MediaQuery.of(context).size.height / 4,
                        width: MediaQuery.of(context).size.width,
                        child: Image.asset("image/i2.jpg", fit: BoxFit.cover),
                      ),
                    ),
                  ),
                  Center(
                    child: Column(
                      children: [
                        SizedBox(
                          height: MediaQuery.of(context).size.height / 10,
                        ),
                        Image.asset(
                          "image/video.png",
                          height: MediaQuery.of(context).size.height / 20,
                          color: const Color(0xffecedf3),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Text(
                  "Lorem ipsum dolor sit amet. Vel odio esse sit soluta mollitia aut officiis dignissimos sed consequatur tempora. Aut internos officiis quo nostrum enim vel ratione pariatur sit suscipit perferendis. Ea beatae facere eum pariatur tempore ab libero laborum ut enim sapiente est nemo iste eum fugit recusandae ut quasi sint.",
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 10.sp,
                    fontFamily: 'Gilroy Medium',
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 80),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40),
                child: Text(
                  "Sit expedita atque est voluptatem natus ut voluptas et accusantium nulla.",
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14.sp,
                    fontFamily: 'Gilroy Bold',
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 80),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Text(
                  "Lorem ipsum dolor sit amet. Vel tempora. Aut internos officiis quo nostrum enim vel ratione pariatur sit suscipit perferendis. Ea beatae facere eum pariatur tempore ab libero laborum ut enim sapiente est nemo iste eum fugit recusandae ut quasi sint.",
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 10.sp,
                    fontFamily: 'Gilroy Medium',
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 50),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    imgs("image/i3.png"),
                    imgs("image/i4.png"),
                    imgs("image/i5.jpg"),
                    imgs("image/i6.jpg"),
                    imgs("image/i7.png"),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 50),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Text(
                  "Lorem ipsum dolor sit ame . Aut internos officiis quo nostrum enim vel ratione pariatur sit suscipit perferendis. Ea beatae facere eum pariatur tempore ab libero laborum ut enim sapiente est nemo iste eum fugit recusandae ut quasi sint.",
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 10.sp,
                    fontFamily: 'Gilroy Medium',
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 50),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Text(
                  "Lorem ipsum dolor sit ame . Aut internos officiis quo nostrum enim vel ratione pariatur sit suscipit perferendis. Ea beatae facere eum pariatur tempore ab libero laborum ut enim sapiente est nemo iste eum fugit recusandae ut quasi sint.",
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 10.sp,
                    fontFamily: 'Gilroy Medium',
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 50),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Text(
                  "Lorem ipsum dolor sit ame . Aut internos officiis quo nostrum enim vel ratione pariatur sit suscipit perferendis. Ea beatae facere eum pariatur tempore ab libero laborum ut enim sapiente est nemo iste eum fugit recusandae ut quasi sint.",
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 10.sp,
                    fontFamily: 'Gilroy Medium',
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: [
                    Row(
                      children: [
                        Stack(
                          children: [
                            CircleAvatar(
                              backgroundColor: Colors.white,
                              radius: MediaQuery.of(context).size.height / 100,
                              child: CircleAvatar(
                                radius: MediaQuery.of(context).size.height / 48,
                                backgroundColor: Colors.white,
                                backgroundImage: const AssetImage(
                                  "image/man.png",
                                ),
                              ),
                            ),
                            Row(
                              children: [
                                SizedBox(
                                  width: MediaQuery.of(context).size.width / 40,
                                ),
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
                                              MediaQuery.of(context)
                                                  .size
                                                  .width /
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
                        fontSize: 8.sp,
                        fontFamily: 'Gilroy Medium',
                      ),
                    ),
                    const Spacer(),
                    Icon(
                      Icons.message_outlined,
                      size: 11.sp,
                      color: const Color(0xff8698c6),
                    ),
                    Text(
                      " 73 Comments",
                      style: TextStyle(
                        color: const Color(0xff8698c6),
                        fontSize: 8.sp,
                        fontFamily: 'Gilroy Medium',
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: MediaQuery.of(context).size.height / 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget imgs(img) {
    return Row(
      children: [
        Container(
          color: Colors.transparent,
          height: MediaQuery.of(context).size.height / 9,
          width: MediaQuery.of(context).size.width / 3,
          child: Image.asset(img, fit: BoxFit.cover),
        ),
        SizedBox(width: MediaQuery.of(context).size.width / 50),
      ],
    );
  }
}
