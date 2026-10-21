"""Offline, reproducible evidence audit. Passing integrity is not model promotion."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
from .ingest import save_json
from .operations import now,utc
from .shadow import file_sha256,verify_record


def audit(root,operations_root,output):
    root=Path(root);operations_root=Path(operations_root);output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    failures=[];warnings=[];originals=[]
    manifest=json.loads((root/'download_manifest.json').read_text(encoding='utf-8'))
    for receipt in manifest['files']:
        path=root/receipt['source']/'originals'/receipt['name']
        try:
            raw=path.read_bytes()
            valid=(receipt['status']=='ok' and hashlib.sha256(raw).hexdigest()==receipt['sha256'])
            if receipt.get('blob_sha1'):
                valid &= hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==receipt['blob_sha1']
            valid &= len(raw)==receipt.get('expected_size',len(raw))
            originals.append({'source':receipt['source'],'name':receipt['name'],'valid':bool(valid),'bytes':len(raw)})
            if not valid:failures.append('original_integrity:'+receipt['name'])
        except OSError:failures.append('missing_original:'+receipt['name'])
    source=root/'canonical/matches.parquet';canonical_hash=file_sha256(source)
    df=pd.read_parquet(source);coverage=json.loads((root/'canonical/coverage.json').read_text())
    invariants={'canonical_count_matches_report':len(df)==coverage['canonical_matches'],
                'unique_match_ids':not df.match_id.duplicated().any(),
                'distinct_players':bool(df.winner_id.ne(df.loser_id).all()),
                'eligibility_matches_report':int(df.eligible_model.sum())==coverage['eligible_serve_matches'],
                'no_source_period_after_snapshot_date':bool(df.period.le(coverage['as_of']).all())}
    for side in ('w','l'):
        eligible=df.loc[df.eligible_model]
        n=eligible[side+'_svpt'];first=eligible[side+'_1stIn']
        fw=eligible[side+'_1stWon'];sw=eligible[side+'_2ndWon']
        invariants[side+'_serve_counts']=bool((n.gt(0)&first.between(0,n)&fw.between(0,first)&sw.between(0,n-first)).all())
    failures.extend(key for key,value in invariants.items() if not value)
    models=[]
    for circuit in ('ATP','WTA'):
        folder=root/f'models/{circuit}_current'
        receipt=json.loads((folder/'training_receipt.json').read_text())
        model=json.loads((folder/'model.json').read_text())
        end=(pd.Timestamp(receipt['cutoff'])-pd.Timedelta(days=receipt['embargo_days'])).strftime('%Y-%m-%d')
        rows=df.loc[df.circuit.eq(circuit)&df.eligible_model&df.period.ge('2018-01-01')&df.period.lt(end)]
        checks={'source_hash':receipt['canonical_sha256']==canonical_hash,
                'training_count':len(rows)==receipt['matches'],
                'last_period':rows.period.max()==receipt['last_source_period'],
                'strict_embargo':bool(rows.period.lt(end).all()),
                'finite_parameters':bool(np.isfinite(model['coefficients']).all()),
                'coefficient_count':len(model['keys'])==len(model['coefficients'])==receipt['parameters']}
        failures.extend(circuit+':'+k for k,v in checks.items() if not v)
        models.append({'circuit':circuit,'checks':checks,'training_matches':len(rows),
                       'last_period':rows.period.max(),'cutoff':receipt['cutoff'],
                       'source_sha256':canonical_hash,'model_sha256':file_sha256(folder/'model.json')})
    snapshots=[];confirmed_credits=0
    for path in sorted((operations_root/'snapshots').glob('*/receipt.json')):
        receipt=json.loads(path.read_text());body=path.parent/'response.json'
        valid=body.exists() and file_sha256(body)==receipt['sha256']
        if not valid:failures.append('quote_snapshot_hash:'+str(path))
        if utc(receipt['requested_at'])>utc(receipt['received_at']):failures.append('response_before_request:'+str(path))
        charged=receipt.get('headers',{}).get('x-requests-last')
        if charged is not None:confirmed_credits+=int(charged)
        snapshots.append({'path':str(path),'valid':valid,'actual_credits':charged})
    shadow=[];event_ids=set();verified_ids=set();future_fixture_count=0
    for path in sorted((operations_root/'shadow').rglob('record.json')):
        try:
            record=verify_record(path);valid=True
        except (ValueError,KeyError,OSError):
            failures.append('shadow_hash:'+str(path));continue
        for event in record.get('events',[]):
            eid=event['event']['id'];event_ids.add(eid)
            fixture=event.get('fixture_receipt')
            if fixture and utc(fixture['observed_at'])>utc(record['observed_at']):
                future_fixture_count+=1
                warnings.append('legacy_fixture_observation_after_record:'+str(path)+':'+eid)
            if event.get('fixture_gate',{}).get('eligible'):verified_ids.add(eid)
        shadow.append({'path':str(path),'valid_hash':valid,'schema':record.get('schema'),
                       'events':len(record.get('events',[])),'paid_capture_count':len(record.get('odds',[]))})
    raw=pd.read_csv(root/'tml/originals/2026.csv',nrows=0).columns.tolist()
    context=['indoor','winner_age','loser_age','winner_hand','loser_hand','w_ace','l_ace','w_df','l_df','w_bpSaved','l_bpSaved']
    omitted=[c for c in context if c in raw and c not in df.columns]
    if 'source_lineage' not in df.columns:
        warnings.append('legacy_canonical_has_no_full_source_lineage; preserve model snapshot, normalize next snapshot with v2')
    report={'schema':'tennis-audit-v1','audited_at':now(),'integrity_pass':not failures,
            'production_approved':False,'failures':failures,'warnings':warnings,
            'originals':{'count':len(originals),'by_source':dict(Counter(x['source'] for x in originals)),
                         'bytes':sum(x['bytes'] for x in originals),'checks':originals},
            'canonical':{'rows':len(df),'eligible':int(df.eligible_model.sum()),'sha256':canonical_hash,'invariants':invariants,
                         'by_circuit':coverage['by_circuit'],'raw_context_fields_not_in_canonical':omitted},
            'models':models,'odds':{'snapshots':len(snapshots),'confirmed_actual_credits':confirmed_credits,'receipts':snapshots},
            'shadow':{'records':len(shadow),'distinct_events':len(event_ids),'events_with_fixture_gate_pass':len(verified_ids),
                      'future_fixture_observations_in_legacy_records':future_fixture_count,'records_detail':shadow},
            'readiness':[
                {'phase':'Datos originales','status':'Verificados' if not failures else 'Revisar','limit':'Los hashes verifican conservación; la cobertura y exactitud del proveedor se evalúan por separado.'},
                {'phase':'Motor matemático','status':'Implementado para investigación','limit':'Habilidades con ponderación temporal y partidos completos; falta el modelo dinámico avanzado.'},
                {'phase':'Contexto y dinámica','status':'Pendiente','limit':'Edad, pista cubierta, fatiga, viajes, clima, lesiones, estilo y presión aún no entran al ajuste.'},
                {'phase':'Mercados y cuotas','status':'Parcial','limit':'Mercados compatibles conectados; derivados sin calibración propia y cobertura variable de la API.'},
                {'phase':'Calendario e identidades','status':'Parcial','limit':'Alias auditados; cada evento necesita una observación reciente de la fuente y su hora reconciliada.'},
                {'phase':'Validación prospectiva','status':'Pendiente','limit':'2026 retrospectivo es desarrollo; hacen falta resultados futuros de pronósticos archivados antes del partido.'},
                {'phase':'Liquidación y riesgo','status':'Parcial','limit':'Perfil observado de Pinnacle; faltan otras casas, riesgo de retiro y límites de exposición.'},
                {'phase':'Operación y panel','status':'Investigación local','limit':'Informe local disponible; faltan servicio de producción, supervisión y prueba externa de hora.'}]}
    save_json(output/'audit.json',report)
    return report
