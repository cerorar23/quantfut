-- ============================================================================
-- 051 - Clubes del historial de las ligas "solo sharp" que no existen en la
-- base (2026-10-11). Segundo ensayo en seco tras db/050: 91 nombres,
-- 86 "nuevos" (nadie se les parece) y 5 que el ensayo marcó dudosos
-- solo porque se parecen a clubes que creó la propia 050 (Latina/Catania,
-- Balikesirspor/Ad. Demirspor, Bodrumspor/Erzurumspor FK,
-- Pendikspor/Denizlispor, Oster/IFK Goteborg): son clubes distintos.
--
-- Se crean AQUÍ y no durante la carga para que la carga sea determinista:
-- cada club que crea el cargador entra en el conjunto contra el que se
-- comparan los siguientes nombres, y podía convertir en dudoso a mitad de
-- carga un nombre que el ensayo dio por nuevo. Con esto la carga solo
-- engancha nombres que ya existen. Ninguno juega hoy en el catálogo (su
-- última temporada es <= 2025/26).
-- ============================================================================
BEGIN;

CREATE TEMP TABLE nuevos (lg text, nombre text) ON COMMIT DROP;
INSERT INTO nuevos VALUES
    ('gb.championship', 'Blackpool'),
    ('gb.championship', 'Milton Keynes Dons'),
    ('gb.championship', 'Peterboro'),
    ('gb.championship', 'Reading'),
    ('gb.championship', 'Wigan'),
    ('gb.championship', 'Wycombe'),
    ('es.laliga2', 'Amorebieta'),
    ('es.laliga2', 'Cartagena'),
    ('es.laliga2', 'Extremadura UD'),
    ('es.laliga2', 'Ferrol'),
    ('es.laliga2', 'Fuenlabrada'),
    ('es.laliga2', 'Gimnastic'),
    ('es.laliga2', 'Llagostera'),
    ('es.laliga2', 'Mirandes'),
    ('es.laliga2', 'Ponferradina'),
    ('es.laliga2', 'Rayo Majadahonda'),
    ('es.laliga2', 'Recreativo'),
    ('es.laliga2', 'Reus Deportiu'),
    ('es.laliga2', 'UCAM Murcia'),
    ('es.laliga2', 'Zaragoza'),
    ('de.bundesliga2', 'Aalen'),
    ('de.bundesliga2', 'Erzgebirge Aue'),
    ('de.bundesliga2', 'Hansa Rostock'),
    ('de.bundesliga2', 'Munich 1860'),
    ('de.bundesliga2', 'Preußen Münster'),
    ('de.bundesliga2', 'Sandhausen'),
    ('de.bundesliga2', 'Ulm'),
    ('de.bundesliga2', 'Wehen'),
    ('de.bundesliga2', 'Wurzburger Kickers'),
    ('it.serie_b', 'Cittadella'),
    ('it.serie_b', 'FeralpiSalo'),
    ('it.serie_b', 'Foggia'),
    ('it.serie_b', 'Pordenone'),
    ('it.serie_b', 'Pro Vercelli'),
    ('it.serie_b', 'Reggiana'),
    ('it.serie_b', 'Reggina'),
    ('it.serie_b', 'Trapani'),
    ('it.serie_b', 'Latina'),
    ('fr.ligue_2', 'Beziers'),
    ('fr.ligue_2', 'Bourg Peronnas'),
    ('fr.ligue_2', 'Chambly'),
    ('fr.ligue_2', 'Chateauroux'),
    ('fr.ligue_2', 'Concarneau'),
    ('fr.ligue_2', 'Creteil'),
    ('fr.ligue_2', 'Martigues'),
    ('fr.ligue_2', 'Niort'),
    ('fr.ligue_2', 'Quevilly Rouen'),
    ('tr.super_lig', 'Akhisar Belediyespor'),
    ('tr.super_lig', 'Ankaragucu'),
    ('tr.super_lig', 'Karagumruk'),
    ('tr.super_lig', 'Mersin Idman Yurdu'),
    ('tr.super_lig', 'Balikesirspor'),
    ('tr.super_lig', 'Bodrumspor'),
    ('tr.super_lig', 'Pendikspor'),
    ('no.eliteserien', 'Jerv'),
    ('no.eliteserien', 'Kongsvinger'),
    ('no.eliteserien', 'Mjondalen'),
    ('no.eliteserien', 'Moss'),
    ('no.eliteserien', 'Odd'),
    ('no.eliteserien', 'Ranheim'),
    ('no.eliteserien', 'Sandnes'),
    ('no.eliteserien', 'Sogndal'),
    ('no.eliteserien', 'Stabaek'),
    ('se.allsvenskan', 'AFC Eskilstuna'),
    ('se.allsvenskan', 'Atvidabergs'),
    ('se.allsvenskan', 'Brage'),
    ('se.allsvenskan', 'Dalkurd'),
    ('se.allsvenskan', 'Falkenbergs'),
    ('se.allsvenskan', 'Gefle'),
    ('se.allsvenskan', 'Jonkopings'),
    ('se.allsvenskan', 'Landskrona'),
    ('se.allsvenskan', 'Ljungskile'),
    ('se.allsvenskan', 'Norrkoping'),
    ('se.allsvenskan', 'Orebro'),
    ('se.allsvenskan', 'Ostersunds'),
    ('se.allsvenskan', 'Sundsvall'),
    ('se.allsvenskan', 'Varberg'),
    ('se.allsvenskan', 'Varnamo'),
    ('se.allsvenskan', 'Oster'),
    ('dk.superliga', 'Esbjerg'),
    ('dk.superliga', 'Fredericia'),
    ('dk.superliga', 'Helsingor'),
    ('dk.superliga', 'Hobro'),
    ('dk.superliga', 'Hvidovre IF'),
    ('dk.superliga', 'Vejle'),
    ('dk.superliga', 'Vendsyssel'),
    ('ch.super_league', 'Aarau'),
    ('ch.super_league', 'Schaffhausen'),
    ('ch.super_league', 'Winterthur'),
    ('ch.super_league', 'Xamax'),
    ('ch.super_league', 'Yverdon');

INSERT INTO teams (league_id, canonical_name)
SELECT lg, nombre FROM nuevos
ON CONFLICT (league_id, canonical_name) DO NOTHING;

INSERT INTO team_aliases (alias, source, team_id)
SELECT n.nombre, 'football_data', t.team_id
FROM nuevos n JOIN teams t ON t.league_id = n.lg AND t.canonical_name = n.nombre
ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id;

DO $$ BEGIN
  IF (SELECT count(*) FROM nuevos n JOIN team_aliases a
        ON a.alias = n.nombre AND a.source = 'football_data') <> 91 THEN
    RAISE EXCEPTION 'db/051: no se crearon los 91 clubes';
  END IF;
END $$;

COMMIT;
