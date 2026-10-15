import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/firebase_services.dart';

void main() {
  test('Quien nunca eligió queda con el seguimiento activo', () {
    expect(consentDefault(null), isTrue);
  });
  test('Una negativa explícita guardada se conserva', () {
    expect(consentDefault(false), isFalse);
  });
  test('Una aceptación guardada se conserva', () {
    expect(consentDefault(true), isTrue);
  });
}
