import 'package:flutter/material.dart';

import 'live_api.dart';
import 'qf_theme.dart';
import 'sport_images.dart';

/// Modelo de un jugador en la pizarra táctica (`QfPitch`).
class PitchPlayer {
  const PitchPlayer({
    required this.name,
    required this.number,
    this.position,
    this.photoUrl,
    required this.x,
    required this.y,
  });

  final String name;
  final int number;
  final String? position;
  final String? photoUrl;
  final double x; // Porcentaje horizontal 0..100
  final double y; // Porcentaje vertical 0..100 (GK abajo ≈ 89, delanteros arriba ≈ 13)

  factory PitchPlayer.fromJson(
    JsonMap json, {
    required double x,
    required double y,
  }) {
    return PitchPlayer(
      name: '${json['nombre'] ?? ''}',
      number: (json['numero'] as num?)?.toInt() ?? 0,
      position: json['pos'] != null ? '${json['pos']}' : (json['posicion'] != null ? '${json['posicion']}' : null),
      photoUrl: json['foto'] != null ? '${json['foto']}' : null,
      x: x,
      y: y,
    );
  }

  static String initials(String name) {
    final parts = name.split(RegExp(r'[\s.]+')).where((p) => p.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) return parts.first.characters.first.toUpperCase();
    return '${parts.first.characters.first}${parts.last.characters.first}'.toUpperCase();
  }

  /// Distribuye los jugadores de `titulares` en las líneas de la formación dada.
  /// Formato: "4-3-1-2", "4-3-3", "4-4-2", "3-5-2", "4-2-3-1", etc.
  /// La primera línea siempre es el portero (1). Las líneas van de abajo hacia arriba.
  static List<PitchPlayer> layoutPlayers({
    required String formation,
    required List<JsonMap> titulares,
  }) {
    if (titulares.isEmpty) return const [];

    final rawParts = formation
        .split('-')
        .map((s) => int.tryParse(s.trim()))
        .whereType<int>()
        .toList();
    final parts = rawParts.isEmpty ? const [4, 4, 2] : rawParts;
    final lines = [1, ...parts]; // Portero + defensas + medios...
    final lineCount = lines.length;

    var idx = 0;
    final players = <PitchPlayer>[];

    for (var li = 0; li < lineCount && idx < titulares.length; li++) {
      final countInLine = lines[li];
      final y = lineCount <= 1
          ? 50.0
          : 89.0 - li * (76.0 / (lineCount - 1));

      for (var i = 0; i < countInLine && idx < titulares.length; i++) {
        final x = (i + 1.0) / (countInLine + 1.0) * 100.0;
        players.add(PitchPlayer.fromJson(titulares[idx], x: x, y: y));
        idx++;
      }
    }

    // Si sobran titulares sin colocar por formación incompleta, los colocamos arriba
    while (idx < titulares.length) {
      final x = (players.length % 5 + 1.0) / 6.0 * 100.0;
      players.add(PitchPlayer.fromJson(titulares[idx], x: x, y: 13.0));
      idx++;
    }

    return players;
  }
}

/// Campo de fútbol CyberCore 400 dp con el once inicial dispuesto tácticamente.
class QfPitch extends StatelessWidget {
  const QfPitch({
    super.key,
    required this.formation,
    required this.titulares,
    this.api,
  });

  final String formation;
  final List<JsonMap> titulares;
  final QuantFutApi? api;

  @override
  Widget build(BuildContext context) {
    final players = PitchPlayer.layoutPlayers(
      formation: formation,
      titulares: titulares,
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        const height = 400.0;

        return Container(
          key: const ValueKey('qf-pitch'),
          height: height,
          decoration: BoxDecoration(
            border: Border.all(color: const Color(0x5905ffa1)), // rgba(5,255,161,.35)
            gradient: const LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Color(0xff0a1d16), Color(0xff08140f)],
            ),
          ),
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              // Línea de medio campo
              Positioned(
                left: 0,
                right: 0,
                top: height / 2,
                child: Container(
                  height: 1,
                  color: const Color(0x4005ffa1), // rgba(5,255,161,.25)
                ),
              ),

              // Círculo central (84 dp de diámetro)
              Positioned(
                left: (width - 84) / 2,
                top: (height - 84) / 2,
                width: 84,
                height: 84,
                child: Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: const Color(0x4005ffa1)),
                  ),
                ),
              ),

              // Área de penalti superior (70 dp de alto, 24% a cada lado)
              Positioned(
                left: width * 0.24,
                right: width * 0.24,
                top: 0,
                height: 70,
                child: Container(
                  decoration: const BoxDecoration(
                    border: Border(
                      left: BorderSide(color: Color(0x4005ffa1)),
                      right: BorderSide(color: Color(0x4005ffa1)),
                      bottom: BorderSide(color: Color(0x4005ffa1)),
                    ),
                  ),
                ),
              ),

              // Área de penalti inferior (70 dp de alto, 24% a cada lado)
              Positioned(
                left: width * 0.24,
                right: width * 0.24,
                bottom: 0,
                height: 70,
                child: Container(
                  decoration: const BoxDecoration(
                    border: Border(
                      left: BorderSide(color: Color(0x4005ffa1)),
                      right: BorderSide(color: Color(0x4005ffa1)),
                      top: BorderSide(color: Color(0x4005ffa1)),
                    ),
                  ),
                ),
              ),

              // Jugadores
              for (final p in players)
                Positioned(
                  left: (p.x / 100.0) * width - 32,
                  top: (p.y / 100.0) * height - 26,
                  width: 64,
                  child: _PitchPlayerWidget(player: p, api: api),
                ),
            ],
          ),
        );
      },
    );
  }
}

class _PitchPlayerWidget extends StatelessWidget {
  const _PitchPlayerWidget({required this.player, this.api});

  final PitchPlayer player;
  final QuantFutApi? api;

  @override
  Widget build(BuildContext context) {
    final photo = player.photoUrl;
    final resolvedPhoto = api != null ? serverImageUrl(api!, photo) : photo;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Stack(
          clipBehavior: Clip.none,
          children: [
            // Avatar redondo 42 dp con borde cian de 2 dp
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: QfColors.cyan, width: 2),
                color: const Color(0xff12141d),
              ),
              child: ClipOval(
                child: resolvedPhoto != null && resolvedPhoto.isNotEmpty
                    ? Image.network(
                        resolvedPhoto,
                        fit: BoxFit.cover,
                        alignment: const Alignment(0, -0.76), // 12% desde arriba
                        errorBuilder: (_, error, stackTrace) => _FallbackInitials(name: player.name),
                      )
                    : _FallbackInitials(name: player.name),
              ),
            ),

            // Dorsal en la esquina inferior derecha
            Positioned(
              right: -6,
              bottom: -4,
              child: Container(
                constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
                padding: const EdgeInsets.symmetric(horizontal: 3),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: const Color(0xff07080c),
                  border: Border.all(color: QfColors.cyan, width: 1),
                ),
                child: Text(
                  '${player.number}',
                  style: const TextStyle(
                    color: QfColors.cyan,
                    fontFamily: 'JetBrains Mono',
                    fontWeight: FontWeight.bold,
                    fontSize: 10,
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 3),
        // Apellido / nombre con sombra de 3px
        Text(
          player.name,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          textAlign: TextAlign.center,
          style: const TextStyle(
            color: Color(0xfff0f1f5),
            fontFamily: 'JetBrains Mono',
            fontWeight: FontWeight.bold,
            fontSize: 10,
            shadows: [
              Shadow(
                color: Colors.black,
                blurRadius: 3,
                offset: Offset(0, 1),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _FallbackInitials extends StatelessWidget {
  const _FallbackInitials({required this.name});

  final String name;

  @override
  Widget build(BuildContext context) {
    return Container(
      alignment: Alignment.center,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xff1f2230), Color(0xff12141d)],
        ),
      ),
      child: Text(
        PitchPlayer.initials(name),
        style: const TextStyle(
          color: QfColors.cyan,
          fontFamily: 'JetBrains Mono',
          fontWeight: FontWeight.bold,
          fontSize: 12,
        ),
      ),
    );
  }
}
