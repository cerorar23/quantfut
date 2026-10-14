"""Purga excepcional autorizada por el titular: Chile y Brasil B exclusivamente.

Respalda COPY binario, prueba reversión y repetición, elimina grupos afectados
completos y restablece cada trigger antes de confirmar. No toca archivos sellados.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re

from psycopg import Rollback, sql
from qf.db import conn

IDS = ['cl.primera', 'br.serie_b']
ROOTS = {
    'leagues': "{a}.league_id IN ('cl.primera','br.serie_b')",
    'teams': "{a}.league_id IN ('cl.primera','br.serie_b')",
    'matches': "{a}.league_id IN ('cl.primera','br.serie_b')",
    'parley_tickets': "EXISTS(SELECT 1 FROM parley_patas z JOIN matches m USING(match_id) WHERE z.ticket_id={a}.ticket_id AND m.league_id IN ('cl.primera','br.serie_b'))",
    'escalera_retos': "EXISTS(SELECT 1 FROM escalera_pasos z JOIN matches m USING(match_id) WHERE z.reto_id={a}.reto_id AND m.league_id IN ('cl.primera','br.serie_b'))",
}


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str), encoding='utf-8')


def graph(c):
    return c.execute("""SELECT conrelid::regclass::text AS child,
        confrelid::regclass::text AS parent,
        array(SELECT attname FROM unnest(conkey) WITH ORDINALITY k(attnum,n)
          JOIN pg_attribute a ON a.attrelid=conrelid AND a.attnum=k.attnum ORDER BY n) AS child_cols,
        array(SELECT attname FROM unnest(confkey) WITH ORDINALITY k(attnum,n)
          JOIN pg_attribute a ON a.attrelid=confrelid AND a.attnum=k.attnum ORDER BY n) AS parent_cols
        FROM pg_constraint WHERE contype='f' AND connamespace='public'::regnamespace""").fetchall()


def table_order(fks):
    included = set(ROOTS)
    while True:
        more = {f['child'] for f in fks if f['parent'] in included} - included
        if not more:
            break
        included.update(more)
    remaining = included.copy()
    order = []
    while remaining:
        ready = sorted(t for t in remaining if not any(
            f['child'] == t and f['parent'] in remaining for f in fks))
        if not ready:
            raise ValueError('foreign_key_cycle_requires_review')
        order.extend(ready)
        remaining.difference_update(ready)
    return order


def selector(table, alias, fks, included, depth=0):
    if table in ROOTS:
        return sql.SQL(ROOTS[table]).format(a=sql.Identifier(alias))
    pieces = []
    for f in fks:
        if f['child'] != table or f['parent'] not in included:
            continue
        parent_alias = 'p' + str(depth)
        equality = sql.SQL(' AND ').join(sql.SQL('{}.{}={}.{}').format(
            sql.Identifier(alias), sql.Identifier(child),
            sql.Identifier(parent_alias), sql.Identifier(parent))
            for child, parent in zip(f['child_cols'], f['parent_cols']))
        pieces.append(sql.SQL('EXISTS(SELECT 1 FROM {} {} WHERE {} AND ({}))').format(
            sql.Identifier(f['parent']), sql.Identifier(parent_alias), equality,
            selector(f['parent'], parent_alias, fks, included, depth + 1)))
    assert pieces, table
    return sql.SQL(' OR ').join(pieces)


def triggers(c):
    return c.execute("""SELECT tgrelid::regclass::text AS table_name,tgname,
        tgenabled::text AS tgenabled,pg_get_triggerdef(oid) AS definition FROM pg_trigger
        WHERE NOT tgisinternal ORDER BY table_name,tgname""").fetchall()


def fingerprint(c, table, condition=sql.SQL('TRUE')):
    return c.execute(sql.SQL("""SELECT count(*) AS n,
        coalesce(sum(hashtextextended(t::text,0)::numeric),0)::text AS digest
        FROM {} t WHERE {}""").format(sql.Identifier(table), condition)).fetchone()


def delete_selected(c, order, protections):
    disabled = []
    for t in protections:
        n = c.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(
            sql.Identifier('retire_keys_' + t['table_name']))).fetchone()['n']
        if not n:
            continue
        assert t['tgenabled'] == 'O', t
        c.execute(sql.SQL('ALTER TABLE {} DISABLE TRIGGER {}').format(
            sql.Identifier(t['table_name']), sql.Identifier(t['tgname'])))
        disabled.append(t)
    counts = {}
    for table in reversed(order):
        counts[table] = c.execute(sql.SQL('DELETE FROM {} t USING {} k WHERE t.ctid::text=k.rid').format(
            sql.Identifier(table), sql.Identifier('retire_keys_' + table))).rowcount
    for t in disabled:
        c.execute(sql.SQL('ALTER TABLE {} ENABLE TRIGGER {}').format(
            sql.Identifier(t['table_name']), sql.Identifier(t['tgname'])))
    return counts


def run(output, migration):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    schema = Path(migration).read_text(encoding='utf-8-sig')
    schema = re.sub(r'(?m)^\s*(?:BEGIN|COMMIT);\s*$', '', schema)
    with conn() as c:
        c.execute("SET LOCAL lock_timeout='10s'")
        c.execute("SET LOCAL statement_timeout='180s'")
        c.execute('SELECT pg_advisory_xact_lock(61013063)')
        fks = graph(c)
        order = table_order(fks)
        c.execute(sql.SQL('LOCK TABLE {} IN ACCESS EXCLUSIVE MODE').format(
            sql.SQL(',').join(map(sql.Identifier, sorted(order)))))
        shared = c.execute("""SELECT count(*) AS n FROM teams t JOIN matches m
            ON t.team_id IN(m.home_team_id,m.away_team_id)
            WHERE t.league_id=ANY(%s) AND NOT(m.league_id=ANY(%s))""", (IDS, IDS)).fetchone()['n']
        assert shared == 0, 'retired_domestic_clubs_used_by_other_competitions'
        before_triggers = triggers(c)
        protections = [t for t in before_triggers if t['table_name'] in order
                       and 'deny_mutation' in t['definition']]
        active = c.execute('SELECT model_version FROM model_artifacts WHERE is_active ORDER BY model_version').fetchall()
        sealed = c.execute('SELECT batch_id,payload_sha256,chain_sha256 FROM prediction_batches ORDER BY seq').fetchall()
        preserved = {}
        selected = {}
        backup = []
        for table in order:
            where = selector(table, 't', fks, set(order))
            c.execute(sql.SQL('CREATE TEMP TABLE {} ON COMMIT DROP AS SELECT ctid::text AS rid FROM {} t WHERE {}').format(
                sql.Identifier('retire_keys_' + table), sql.Identifier(table), where))
            selected[table] = c.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(
                sql.Identifier('retire_keys_' + table))).fetchone()['n']
            preserved[table] = fingerprint(c, table, sql.SQL('NOT ({})').format(where))
            if selected[table]:
                path = root / (table + '.copy.gz')
                with gzip.open(path, 'wb') as handle, c.cursor().copy(sql.SQL(
                    'COPY(SELECT t.* FROM {} t JOIN {} k ON t.ctid::text=k.rid) TO STDOUT (FORMAT BINARY)').format(
                        sql.Identifier(table), sql.Identifier('retire_keys_' + table))) as copy:
                    for block in copy:
                        handle.write(block)
                backup.append({'table':table,'rows':selected[table],'file':path.name,
                               'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        write(root / 'backup.json', {'restore_order':order,'files':backup,'selected':selected,
            'preserved':preserved,'active_model':active,'sealed_batches':sealed,
            'triggers':before_triggers,'authorized_exception':'explicit user reply 2026-10-13',
            'league_ids':IDS,'migration_sha256':hashlib.sha256(Path(migration).read_bytes()).hexdigest()})
        with c.transaction():
            trial = delete_selected(c, order, protections)
            again = delete_selected(c, order, protections)
            assert trial == selected and not any(again.values())
            c.execute(schema)
            for table in order:
                assert fingerprint(c, table) == preserved[table], table
            raise Rollback()
        assert triggers(c) == before_triggers
        for table in order:
            assert fingerprint(c, table)['n'] == preserved[table]['n'] + selected[table], table
        write(root / 'rollback.json', {'restored':True,'zero_repeat_writes':True,'deleted_trial':trial})
        print(json.dumps({'stage':'rollback_verified','selected':{t:n for t,n in selected.items() if n}}), flush=True)
        deleted = delete_selected(c, order, protections)
        assert deleted == selected
        c.execute(schema)
        for table in order:
            assert fingerprint(c, table) == preserved[table], table
        assert c.execute('SELECT model_version FROM model_artifacts WHERE is_active ORDER BY model_version').fetchall() == active
        assert c.execute('SELECT batch_id,payload_sha256,chain_sha256 FROM prediction_batches ORDER BY seq').fetchall() == sealed
        now_triggers = triggers(c)
        assert all(t in now_triggers for t in before_triggers)
        for league in IDS:
            with c.transaction():
                try:
                    c.execute('INSERT INTO leagues(league_id,country,name) VALUES(%s,%s,%s)', (league, 'retired', 'retired'))
                except Exception as exc:
                    assert 'retired_league' in str(exc), str(exc)
                    raise Rollback()
                raise AssertionError('retired_league_was_recreated')
        report = {'completed_at':datetime.now(timezone.utc).isoformat(),'league_ids':IDS,
            'deleted':deleted,'backup':backup,'unaffected_rows_verified':True,
            'triggers_restored':True,'rollback_and_repeat_verified':True,
            'reintroduction_blocked':True,'active_model':active,'sealed_batch_count':len(sealed)}
    write(root / 'result.json', report)
    print(json.dumps(report, default=str), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--migration',required=True)
    parser.add_argument('--execute-authorized-deletion',action='store_true',required=True)
    args = parser.parse_args()
    run(args.output,args.migration)
