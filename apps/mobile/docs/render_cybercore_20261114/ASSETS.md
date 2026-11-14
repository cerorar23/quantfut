# Imágenes del render

El render usa `/_blob/<id>` (almacén privado del lienzo de Claude). Esta tabla traduce cada id al archivo de esta carpeta y a su origen real.
En la app NO se empaquetan: se piden al servidor (`/web/escudos/{id}.png`, `/web/imagenes/...`) con iniciales como respaldo.

| id en el render | archivo | origen real |
|---|---|---|
| `9da85345e94e5f91f11240ac38d5c58d` | `assets/escudo_6771_mallorca.png` | /web/escudos/6771.png (API-Football; servido por la API) |
| `afab1ff9f1c954d5ecc8200c3dcf500d` | `assets/escudo_2982_cordoba.png` | /web/escudos/2982.png (API-Football; servido por la API) |
| `06563c762f34a50e9e5dcaefa09be9de` | `assets/escudo_2970_athletic.png` | /web/escudos/2970.png (API-Football; servido por la API) |
| `b254821b70ff6a347e9dba18d8ccb717` | `assets/escudo_2966_espanyol.png` | /web/escudos/2966.png (API-Football; servido por la API) |
| `9a20bf15cbc68ac56b042100f44f532b` | `assets/escudo_39925_cruzeiro.png` | /web/escudos/39925.png (API-Football; servido por la API) |
| `b4d035f162742dc4744fb6ea4736ba93` | `assets/escudo_39929_palmeiras.png` | /web/escudos/39929.png (API-Football; servido por la API) |
| `b6f3599a4863f2d04df62ca2925478fe` | `assets/escudo_39930_flamengo.png` | /web/escudos/39930.png (API-Football; servido por la API) |
| `1eb70b09ff1dfebea1ee8d685df7af07` | `assets/escudo_39922_atletico_pr.png` | /web/escudos/39922.png (API-Football; servido por la API) |
| `05547c47e6be17a6d8e0672608fda793` | `assets/escudo_7529_cadiz.png` | /web/escudos/7529.png (API-Football; servido por la API) |
| `26ab7ff29aa1917e2b41d56db0830fab` | `assets/escudo_4502_leganes.png` | /web/escudos/4502.png (API-Football; servido por la API) |
| `e9fb4f6ca6e38fc82a80d85533a963e7` | `assets/escudo_2977_eibar.png` | /web/escudos/2977.png (API-Football; servido por la API) |
| `9fa7b50fe217dfaf23c58d2a60265371` | `assets/escudo_3728_las_palmas.png` | /web/escudos/3728.png (API-Football; servido por la API) |
| `85a49bb7d75e433efd1368a459cc7158` | `assets/escudo_5251_girona.png` | /web/escudos/5251.png (API-Football; servido por la API) |
| `61a80cb9265bade28041dc8879ebfdb9` | `assets/escudo_84894_ceuta.png` | /web/escudos/84894.png (API-Football; servido por la API) |
| `53d8656e546fb8efb8fcdd5acf7f01d0` | `assets/escudo_84898_celta_b.png` | /web/escudos/84898.png (API-Football; servido por la API) |
| `8a3da2674305bc5cb6316bb1f821779c` | `assets/escudo_84899_eldense.png` | /web/escudos/84899.png (API-Football; servido por la API) |
| `d0ebf60165f16fb39cb0ca3702b41c79` | `assets/escudo_2967_granada.png` | /web/escudos/2967.png (API-Football; servido por la API) |
| `da6f2c877d18ba35a8d4350664c395f9` | `assets/escudo_6008_valladolid.png` | /web/escudos/6008.png (API-Football; servido por la API) |
| `cf44a5a61913d439a6928335e67150eb` | `assets/logo_nba_NYK.png` | frontend/imagenes/nba/NYK.png (TheSportsDB) |
| `10fda615cda9a0af6884ca922825e90b` | `assets/logo_nba_MIA.png` | frontend/imagenes/nba/MIA.png (TheSportsDB) |
| `e9b400da9580608c75ff00a2c1dc11c5` | `assets/logo_nba_BOS.png` | frontend/imagenes/nba/BOS.png (TheSportsDB) |
| `aea89ff3989ccce3b75d8343a05a3743` | `assets/logo_nba_MIL.png` | frontend/imagenes/nba/MIL.png (TheSportsDB) |
| `5ff7399de00cdcd9892baa828ce590c6` | `assets/logo_nba_DEN.png` | frontend/imagenes/nba/DEN.png (TheSportsDB) |
| `a6246951c4ae5f8463fa3dced06e1c4e` | `assets/logo_nba_PHX.png` | frontend/imagenes/nba/PHX.png (TheSportsDB) |
| `bfd80f71d11b27f23208aba8ff962867` | `assets/logo_nba_DET.png` | frontend/imagenes/nba/DET.png (TheSportsDB) |
| `ee10ef692188fd86766c8bf80836b37f` | `assets/nba_jugador_1628973_brunson.png` | /web/imagenes/jugadores/nba/1628973.png (cdn.nba.com headshots) |
| `10cf38659154112f7b81a1dd0b4c3d8b` | `assets/nba_jugador_1629639_herro.png` | /web/imagenes/jugadores/nba/1629639.png (cdn.nba.com headshots) |
| `1aa5591b0d28d45302cd1f125d1712fe` | `assets/nba_jugador_1626157_towns.png` | /web/imagenes/jugadores/nba/1626157.png (cdn.nba.com headshots) |
| `e1fe13dda9032357d0d9f123c2a5138d` | `assets/nba_jugador_1628389_adebayo.png` | /web/imagenes/jugadores/nba/1628389.png (cdn.nba.com headshots) |
| `fc3dff5676a4ff417341754d6b94a621` | `assets/nba_jugador_1630595_cunningham.png` | /web/imagenes/jugadores/nba/1630595.png (cdn.nba.com headshots) |
| `7c86d15fdc0d605dc4b566f88e922312` | `assets/nba_jugador_1631105_duren.png` | /web/imagenes/jugadores/nba/1631105.png (cdn.nba.com headshots) |
| `05914e7f26589ee70f2b602e55ca070a` | `assets/futbol_jugador_179139_roman.png` | /web/imagenes/jugadores/futbol/179139.png (API-Football) |
| `68d9fad67201d079b20526c177e7e444` | `assets/futbol_jugador_26302_maffeo.png` | /web/imagenes/jugadores/futbol/26302.png (API-Football) |
| `db64ae22b0af1995b83cd874f849a26f` | `assets/futbol_jugador_46738_valjent.png` | /web/imagenes/jugadores/futbol/46738.png (API-Football) |
| `105d7afd90042b6b2fe28624bbcd33af` | `assets/futbol_jugador_414_mascarell.png` | /web/imagenes/jugadores/futbol/414.png (API-Football) |
| `c9ff947eaacd0aa61d8aa1fbe20a2dfe` | `assets/futbol_jugador_920_lato.png` | /web/imagenes/jugadores/futbol/920.png (API-Football) |
| `3271fade0842934ebd5230f4b9358be1` | `assets/futbol_jugador_190485_samu_costa.png` | /web/imagenes/jugadores/futbol/190485.png (API-Football) |
| `a72af6d834150a73cbaceab413d2e620` | `assets/futbol_jugador_47336_darder.png` | /web/imagenes/jugadores/futbol/47336.png (API-Football) |
| `b927dcbff529a08db62c04aea9126d84` | `assets/futbol_jugador_1701_morlanes.png` | /web/imagenes/jugadores/futbol/1701.png (API-Football) |
| `de8e75b7bdaa7ffd2848d331b87a586b` | `assets/futbol_jugador_285909_torre.png` | /web/imagenes/jugadores/futbol/285909.png (API-Football) |
| `3485c14b3606948f207b10b080998d11` | `assets/futbol_jugador_25375_asano.png` | /web/imagenes/jugadores/futbol/25375.png (API-Football) |
| `f4d6d5fed2cda059e2a0e2a46c2a2da8` | `assets/futbol_jugador_50048_muriqi.png` | /web/imagenes/jugadores/futbol/50048.png (API-Football) |
| `c1cdfced4be0b368a59a4a6b87f01ce5` | `assets/tenis_fritz.webp` | SofaScore, carpeta local SOFASCORE/data/images/tenistas (150x150 RGBA, retrato circular) |
| `34c6447ff06248aad6c47ec3e792fe40` | `assets/tenis_tirante.webp` | SofaScore, carpeta local SOFASCORE/data/images/tenistas (150x150 RGBA, retrato circular) |
| `93372743515ef3f3b1a897cc2669b845` | `assets/tenis_alcaraz.webp` | SofaScore, carpeta local SOFASCORE/data/images/tenistas (150x150 RGBA, retrato circular) |
| `4e1d40a719ca20a5cf7c8a7c3cbc8642` | `assets/tenis_zverev.webp` | SofaScore, carpeta local SOFASCORE/data/images/tenistas (150x150 RGBA, retrato circular) |
| `ea610f40c3f67b0aee7039a50569ca00` | `assets/tenis_de_minaur.webp` | SofaScore, carpeta local SOFASCORE/data/images/tenistas (150x150 RGBA, retrato circular) |
| `d104815e8f420fcb473e17de55e13826` | `assets/tenis_paolini.webp` | SofaScore, carpeta local SOFASCORE/data/images/tenistas (150x150 RGBA, retrato circular) |
| `1d05682d3921573084dbdb00f1eb5314` | `assets/tenis_rybakina.webp` | SofaScore, carpeta local SOFASCORE/data/images/tenistas (150x150 RGBA, retrato circular) |

Obsoletas (fotos de Wikimedia, reemplazadas por las de SofaScore y ya no usadas): `f4ecc18e…` Alcaraz, `1e020faa…` Zverev, `c85fffeb…` Fritz, `49a99b37…` Tirante, `7f75f74f…` De Minaur, `c8ecef06…` Paolini, `0bd4f855…` Rybakina.
