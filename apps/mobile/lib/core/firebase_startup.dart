import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';

import '../firebase_options.dart';
import '../l10n/app_locale.dart';
import 'firebase_services.dart';
import 'meta_events.dart';

const firebaseEnabled = bool.fromEnvironment(
  'QF_FIREBASE_ENABLED',
  defaultValue: true,
);

Future<void> initializeFirebase() async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  await FirebaseServices.initialize();
  MetaEvents.current ??= MetaEvents(FacebookSink());
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
        locale: AppLocale.instance.locale,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
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
                          Builder(
                            builder: (context) => Text(
                              context.l10n.startupFailed,
                              textAlign: TextAlign.center,
                            ),
                          ),
                          const SizedBox(height: 16),
                          FilledButton(
                            onPressed: () => setState(() {
                              _initialization = Future.sync(widget.initialize);
                            }),
                            child: Builder(
                              builder: (context) =>
                                  Text(context.l10n.commonRetry),
                            ),
                          ),
                        ],
                      )
                    : Builder(
                        builder: (context) => CircularProgressIndicator(
                          semanticsLabel: context.l10n.startupLoading,
                        ),
                      ),
              ),
            ),
          ),
        ),
      );
    },
  );
}
