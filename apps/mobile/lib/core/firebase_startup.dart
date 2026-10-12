import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';

import '../firebase_options.dart';
import 'firebase_services.dart';

const firebaseEnabled = bool.fromEnvironment(
  'QF_FIREBASE_ENABLED',
  defaultValue: true,
);

Future<void> initializeFirebase() async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  await FirebaseServices.initialize();
}

/// Does not mount the account/content app until Firebase has initialized.
class FirebaseStartup extends StatefulWidget {
  const FirebaseStartup({
    super.key,
    required this.child,
    this.initialize = initializeFirebase,
  });

  final Widget child;
  final Future<void> Function() initialize;

  @override
  State<FirebaseStartup> createState() => _FirebaseStartupState();
}

class _FirebaseStartupState extends State<FirebaseStartup> {
  late Future<void> _initialization;

  @override
  void initState() {
    super.initState();
    _initialization = Future.sync(widget.initialize);
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<void>(
    future: _initialization,
    builder: (context, snapshot) {
      if (snapshot.connectionState == ConnectionState.done &&
          !snapshot.hasError) {
        return widget.child;
      }
      return MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: ThemeData.dark(),
        home: Scaffold(
          body: SafeArea(
            child: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child:
                    snapshot.connectionState == ConnectionState.done &&
                        snapshot.hasError
                    ? Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Text(
                            'No pudimos iniciar QuantFut. Inténtalo de nuevo.',
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 16),
                          FilledButton(
                            onPressed: () => setState(() {
                              _initialization = Future.sync(widget.initialize);
                            }),
                            child: const Text('Reintentar'),
                          ),
                        ],
                      )
                    : const CircularProgressIndicator(
                        semanticsLabel: 'Iniciando QuantFut',
                      ),
              ),
            ),
          ),
        ),
      );
    },
  );
}
