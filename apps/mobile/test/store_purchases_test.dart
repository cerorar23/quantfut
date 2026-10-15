import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/store_purchases.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

class FakeApi extends QuantFutApi {
  FakeApi({this.plusNow = false, this.answer = 'concedido'})
    : super(base: Uri.parse('https://x.invalid'));
  final bool plusNow;
  final String answer;
  final verified = <String>[];
  @override
  bool get plus => plusNow;
  @override
  bool get signedIn => true;
  @override
  JsonMap? get account => {
    'store_account_token': '0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c',
  };
  @override
  Future<JsonMap> verifyPurchase({
    required String store,
    required String productId,
    required String token,
  }) async {
    verified.add('$store:$productId:$token');
    if (answer == 'error') {
      throw const ApiFailure('La tienda no está disponible', 503);
    }
    return {'estado': answer, 'plus': answer == 'concedido'};
  }

  @override
  Future<void> updateAccount() async {}
}

class FakeBackend implements StoreBackend {
  final controller = StreamController<List<PurchaseDetails>>.broadcast();
  final bought = <String>[];
  final completed = <String>[];
  @override
  Stream<List<PurchaseDetails>> get purchases => controller.stream;
  @override
  Future<bool> available() async => true;
  @override
  Future<List<ProductDetails>> products(Set<String> ids) async => [
    ProductDetails(
      id: 'quantfut_plus_1m',
      title: 'Plus',
      description: '',
      price: r'$4.99',
      rawPrice: 4.99,
      currencyCode: 'USD',
    ),
  ];
  @override
  Future<bool> buy(ProductDetails product, String accountToken) async {
    bought.add('${product.id}:$accountToken');
    return true;
  }

  @override
  Future<void> complete(PurchaseDetails purchase) async =>
      completed.add(purchase.productID);
  @override
  Future<void> restore(String accountToken) async {}
}

PurchaseDetails _purchase(PurchaseStatus status) => PurchaseDetails(
  productID: 'quantfut_plus_1m',
  verificationData: PurchaseVerificationData(
    localVerificationData: '',
    serverVerificationData: 'jws-123',
    source: 'app_store',
  ),
  transactionDate: '0',
  status: status,
)..pendingCompletePurchase = true;

const plans = <JsonMap>[
  {
    'plan_code': 'plus_1m',
    'apple_product_id': 'quantfut_plus_1m',
    'play_product_id': 'quantfut_plus',
    'play_base_plan_id': 'plus-1m',
  },
];

// La verificación encadena varios `await`: un retardo real (no un solo microtask) deja
// terminar el manejador del stream antes de comprobar.
Future<void> _flush() =>
    Future<void>.delayed(const Duration(milliseconds: 10));

void main() {
  test('Comprar pasa el token de cuenta a la tienda', () async {
    final backend = FakeBackend();
    final store = StoreController(FakeApi(), backend: backend, ios: true)
      ..listen();
    await store.load(plans);
    await store.buy('plus_1m');
    expect(backend.bought, [
      'quantfut_plus_1m:0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c',
    ]);
  });

  test('Solo se completa la compra cuando el servidor concede', () async {
    final backend = FakeBackend();
    final api = FakeApi();
    final store = StoreController(api, backend: backend, ios: true)..listen();
    backend.controller.add([_purchase(PurchaseStatus.purchased)]);
    await _flush();
    await _flush();
    expect(api.verified, ['app_store:quantfut_plus_1m:jws-123']);
    expect(backend.completed, ['quantfut_plus_1m']);
    expect(store.state, StoreState.granted);
  });

  test(
    'Si el servidor falla no se completa: la tienda la re-entrega después',
    () async {
      final backend = FakeBackend();
      final store =
          StoreController(FakeApi(answer: 'error'), backend: backend, ios: true)
            ..listen();
      backend.controller.add([_purchase(PurchaseStatus.purchased)]);
      await _flush();
      await _flush();
      expect(backend.completed, isEmpty);
      expect(store.state, StoreState.failed);
    },
  );

  test('Compra pendiente muestra pendiente y no verifica', () async {
    final backend = FakeBackend();
    final api = FakeApi();
    final store = StoreController(api, backend: backend, ios: true)..listen();
    backend.controller.add([_purchase(PurchaseStatus.pending)]);
    await _flush();
    expect(store.state, StoreState.pending);
    expect(api.verified, isEmpty);
  });

  test(
    'Con Plus vigente no se lanza otra compra: se gestiona en la tienda',
    () async {
      final backend = FakeBackend();
      final store =
          StoreController(FakeApi(plusNow: true), backend: backend, ios: true)
            ..listen();
      await store.load(plans);
      await store.buy('plus_1m');
      expect(backend.bought, isEmpty);
      expect(store.state, StoreState.manage);
    },
  );

  test('Enlace de gestión según la tienda', () {
    expect(
      manageSubscriptionsUri(ios: false).toString(),
      'https://play.google.com/store/account/subscriptions?package=com.saptain.quantfut',
    );
    expect(
      manageSubscriptionsUri(ios: true).toString(),
      'https://apps.apple.com/account/subscriptions',
    );
  });
}
