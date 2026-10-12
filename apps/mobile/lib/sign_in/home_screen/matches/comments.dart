import 'package:gobet/utils/color_notifire.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class Comments extends StatefulWidget {
  const Comments({Key? key}) : super(key: key);

  @override
  _CommentsState createState() => _CommentsState();
}

class _CommentsState extends State<Comments> {
  late ColorNotifire notifire;
  @override
  Widget build(BuildContext context) {
    notifire = Provider.of<ColorNotifire>(context, listen: true);
    return Scaffold(
      backgroundColor: notifire.getprimerycolor,
      appBar: AppBar(
        title: const Text("Comments", style: TextStyle(fontSize: 15)),
        backgroundColor: Color(0xff181c35),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            children: [
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Comment("Shane Jimenez", const AssetImage("image/man.png")),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Comment("Elbert Ruiz", const AssetImage("image/man.png")),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Comment("Dianne George", const AssetImage("image/man.png")),
              SizedBox(height: MediaQuery.of(context).size.height / 40),
              Comment("Calvin Rodgers", const AssetImage("image/man.png")),
              SizedBox(height: MediaQuery.of(context).size.height / 30),
            ],
          ),
        ),
      ),
    );
  }

  Widget Comment(name, image) {
    return Container(
      height: MediaQuery.of(context).size.height / 4.7,
      decoration: const BoxDecoration(
        borderRadius: BorderRadius.all(Radius.circular(15)),
        color: Color(0xff252a4a),
      ),
      child: Column(
        children: [
          SizedBox(height: MediaQuery.of(context).size.height / 60),
          Row(
            children: [
              SizedBox(width: MediaQuery.of(context).size.width / 20),
              Image.asset(
                "image/profile.png",
                height: MediaQuery.of(context).size.height / 10,
              ),
              SizedBox(width: MediaQuery.of(context).size.width / 20),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: const TextStyle(
                      color: Color(0xfffdfbfd),
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 100),
                  const Text(
                    "27 mins ago",
                    style: TextStyle(
                      color: Color(0xff5a6eac),
                      fontSize: 11,
                      fontFamily: 'Gilroy Bold',
                    ),
                  ),
                  SizedBox(height: MediaQuery.of(context).size.height / 90),
                  const Text(
                    "Quisque condimentum lobortis",
                    style: TextStyle(
                      fontFamily: 'Gilroy Medium',
                      color: Color(0xff8b9cce),
                      fontSize: 12,
                    ),
                  ),
                  const Text(
                    "ullamcorper. Aenean ac elit luctus.",
                    style: TextStyle(
                      fontFamily: 'Gilroy Medium',
                      color: Color(0xff8b9cce),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ],
          ),
          SizedBox(height: MediaQuery.of(context).size.height / 100),
          const Divider(thickness: 0.5, color: Color(0xff8b9cce)),
          SizedBox(height: MediaQuery.of(context).size.height / 110),
          Padding(
            padding: const EdgeInsets.only(right: 20),
            child: Row(
              children: [
                const Spacer(),
                const Icon(
                  Icons.message_outlined,
                  color: Color(0xff98a6d0),
                  size: 17,
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 100),
                const Text(
                  "10",
                  style: TextStyle(
                    color: Color(0xff98a6d0),
                    fontSize: 18,
                    fontFamily: 'Gilroy Bold',
                  ),
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 30),
                const Icon(
                  Icons.favorite_border,
                  color: Color(0xff98a6d0),
                  size: 17,
                ),
                SizedBox(width: MediaQuery.of(context).size.width / 100),
                const Text(
                  "10",
                  style: TextStyle(
                    color: Color(0xff98a6d0),
                    fontSize: 18,
                    fontFamily: 'Gilroy Bold',
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
