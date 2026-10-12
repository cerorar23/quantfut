import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/firebase_access.dart';
import 'package:gobet/core/firebase_services.dart';
import 'package:gobet/product/live_api.dart';

void main() {
  test('Incoming notifications only open an internal match identifier', () {
    expect(notificationMatchId({'route':'match','match_id':'match-123'}), 'match-123');
    expect(notificationMatchId({'route':'match','match_id':'https://outside.example'}), isNull);
    expect(notificationMatchId({'route':'vip','match_id':'123'}), isNull);
    expect(notificationMatchId({'route':'match','match_id':'../private'}), isNull);
  });
  test('Consent documents require HTTPS and the published legal paths', () {
    expect(legalUrl('https://pronosticosdeportivos.pro/legal/terminos'), isNotNull);
    expect(legalUrl('http://pronosticosdeportivos.pro/legal/terminos'), isNull);
    expect(legalUrl('https://untrusted.example/legal/terminos'), isNull);
    expect(legalUrl('https://pronosticosdeportivos.pro/control'), isNull);
  });
  test('Performance names never include account or match identifiers', () {
    expect(apiTraceName('/mobile/v1/matches/private-id'), 'qf_load_match');
    expect(apiTraceName('/app/v1/firebase/devices'), 'qf_firebase_request');
  });
}
