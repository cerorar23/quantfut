import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:in_app_purchase_android/in_app_purchase_android.dart';

import '../core/meta_events.dart';
import 'live_api.dart';

enum StoreState {
  idle,
  loading,
  unavailable,
  verifying,
  pending,
  granted,
  failed,
  manage,
}

String? storeProductId(JsonMap plan, {required bool ios}) =>
    (ios ? plan['apple_product_id'] : plan['play_product_id']) as String?;

/// En Play cada plan base de una suscripción llega como un ProductDetails propio.
String? basePlanOf(ProductDetails p) {
  if (p is! GooglePlayProductDetails) return null;
  final i = p.subscriptionIndex;
  final offers = p.productDetails.subscriptionOfferDetails;
  if (i == null || offers == null) return null;
  return offers[i].offerId == null ? offers[i].basePlanId : null;
}

Uri manageSubscriptionsUri({required bool ios}) => ios
    ? Uri.parse('https://apps.apple.com/account/subscriptions')
    : Uri.parse(
        'https://play.google.com/store/account/subscriptions?package=com.saptain.quantfut',
      );

abstract class StoreBackend {
  Stream<List<PurchaseDetails>> get purchases;
  Future<bool> available();
  Future<List<ProductDetails>> products(Set<String> ids);
  Future<bool> buy(ProductDetails product, String accountToken);
  Future<void> complete(PurchaseDetails purchase);
  Future<void> restore(String accountToken);
}

class PluginStore implements StoreBackend {
  InAppPurchase get _iap => InAppPurchase.instance;
  @override
  Stream<List<PurchaseDetails>> get purchases => _iap.purchaseStream;
  @override
  Future<bool> available() => _iap.isAvailable();
  @override
  Future<List<ProductDetails>> products(Set<String> ids) async =>
      (await _iap.queryProductDetails(ids)).productDetails;
  @override
  Future<bool> buy(ProductDetails product, String accountToken) =>
      _iap.buyNonConsumable(
        // applicationUserName → obfuscatedAccountId (Play) / appAccountToken (StoreKit 2).
        purchaseParam: product is GooglePlayProductDetails
            ? GooglePlayPurchaseParam(
                productDetails: product,
                applicationUserName: accountToken,
              )
            : PurchaseParam(
                productDetails: product,
                applicationUserName: accountToken,
              ),
      );
  @override
  Future<void> complete(PurchaseDetails purchase) =>
      _iap.completePurchase(purchase);
  @override
  Future<void> restore(String accountToken) =>
      _iap.restorePurchases(applicationUserName: accountToken);
}

/// El acceso lo concede el servidor tras verificar con la tienda; la app solo transporta
/// el token/JWS y completa la compra cuando el servidor contesta.
class StoreController extends ChangeNotifier {
  StoreController(this.api, {StoreBackend? backend, bool? ios})
    : backend = backend ?? PluginStore(),
      ios = ios ?? Platform.isIOS;
  final QuantFutApi api;
  final StoreBackend backend;
  final bool ios;
  StoreState state = StoreState.idle;
  String? error;
  final Map<String, ProductDetails> byPlan = {};
  StreamSubscription<List<PurchaseDetails>>? _sub;

  String get _store => ios ? 'app_store' : 'google_play';
  String? get _token => api.account?['store_account_token'] as String?;

  void _set(StoreState value, [String? message]) {
    state = value;
    error = message;
    notifyListeners();
  }

  /// Desde el arranque: la tienda re-entrega aquí compras sin completar.
  void listen() => _sub ??= backend.purchases.listen(_onPurchases);

  Future<void> load(List<JsonMap> plans) async {
    listen();
    _set(StoreState.loading);
    try {
      if (!await backend.available()) return _set(StoreState.unavailable);
      final ids = plans
          .map((p) => storeProductId(p, ios: ios))
          .whereType<String>()
          .toSet();
      final found = await backend.products(ids);
      byPlan.clear();
      for (final plan in plans) {
        final id = storeProductId(plan, ios: ios);
        final match = found.where(
          (p) =>
              p.id == id &&
              (ios || basePlanOf(p) == plan['play_base_plan_id']),
        );
        if (match.isNotEmpty) byPlan[plan['plan_code'] as String] = match.first;
      }
      _set(byPlan.isEmpty ? StoreState.unavailable : StoreState.idle);
    } catch (_) {
      _set(StoreState.unavailable);
    }
  }

  Future<void> buy(String planCode) async {
    if (api.plus) return _set(StoreState.manage);
    final product = byPlan[planCode], token = _token;
    if (product == null || token == null) return _set(StoreState.unavailable);
    await MetaEvents.current?.initiateCheckout(
      planCode,
      product.rawPrice,
      product.currencyCode,
    );
    try {
      await backend.buy(product, token);
    } catch (_) {
      _set(StoreState.failed);
    }
  }

  Future<void> restore() async {
    final token = _token;
    if (token == null) return _set(StoreState.unavailable);
    _set(StoreState.verifying);
    await backend.restore(token);
  }

  Future<void> _onPurchases(List<PurchaseDetails> list) async {
    for (final p in list) {
      switch (p.status) {
        case PurchaseStatus.pending:
          _set(StoreState.pending);
        case PurchaseStatus.error:
        case PurchaseStatus.canceled:
          if (p.pendingCompletePurchase) await backend.complete(p);
          _set(
            p.status == PurchaseStatus.error
                ? StoreState.failed
                : StoreState.idle,
          );
        case PurchaseStatus.purchased:
        case PurchaseStatus.restored:
          _set(StoreState.verifying);
          try {
            final r = await api.verifyPurchase(
              store: _store,
              productId: p.productID,
              token: p.verificationData.serverVerificationData,
            );
            // «sin_acceso» (caducada o reembolsada) también se completa: no hay nada que dar.
            if (p.pendingCompletePurchase) await backend.complete(p);
            await api.updateAccount();
            _set(
              r['estado'] == 'concedido'
                  ? StoreState.granted
                  : StoreState.idle,
            );
          } on ApiFailure catch (e) {
            // Sin completar: Play/App Store la re-entregan y se vuelve a verificar.
            _set(StoreState.failed, e.message);
          }
      }
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
