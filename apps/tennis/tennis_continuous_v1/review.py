"""Compile visually reviewed official PDF cells into strictly gated forecasts.

Reviews are made by the scheduled research agent, not assumed from fuzzy names.
The original PDF bytes, exact cell, date and fresh calendar are checked again.
"""
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import re
from pypdf import PdfReader
from tennis_engine.identities import normalized
from tennis_engine.operations import now,utc
from tennis_engine.paper_validation import digest
from tennis_engine.state_capture import state
from tennis_quality_v3.prospective import read,write_new,seal_prediction,load


def abbreviation_matches(short,full):
    if normalized(short)==normalized(full):return True
    a,b=normalized(short.replace('-',' ')).split(),normalized(full.replace('-',' ')).split();initials=[]
    while a and len(a[0])==1:initials.append(a.pop(0))
    return bool(initials and a and len(b)>len(a) and b[-len(a):]==a and [v[0] for v in b[:-len(a)]]==initials)


def cell_text(path,rect):
    if len(rect)!=4 or any(isinstance(x,bool) or not isinstance(x,(int,float)) for x in rect) or not 0<=rect[0]<rect[2]<=1 or not 0<=rect[1]<rect[3]<=1:
        raise ValueError('Reviewed rectangle required')
    page=PdfReader(path).pages[0];w=float(page.mediabox.width);h=float(page.mediabox.height);parts=[]
    def visitor(text,cm,tm,font,size):
        x=(tm[4]*cm[0]+tm[5]*cm[2]+cm[4])/w;top=1-(tm[4]*cm[1]+tm[5]*cm[3]+cm[5])/h
        if rect[0]<=x<=rect[2] and rect[1]<=top<=rect[3]:parts.append(text)
    page.extract_text(visitor_text=visitor)
    return normalized(' '.join(parts))


def official_proof(review,spec,decision):
    receipt=read(review['receipt_path'])
    if not receipt.get('accepted_document') or receipt.get('http_status')!=200 or receipt['url']!=spec['url'] or digest(receipt['source_path'])!=receipt['sha256']:
        raise ValueError('Original reviewed official source required')
    if not 0<(utc(decision)-utc(receipt['received_at'])).total_seconds()<=900:
        raise ValueError('Official source unavailable or stale')
    day=datetime.fromisoformat(review['date']).date()
    document=normalized(' '.join(p.extract_text() for p in PdfReader(receipt['source_path']).pages))
    dates=[f'{day.day} {day.strftime("%B").lower()} {day.year}',f'{day.strftime("%B").lower()} {day.day} {day.year}']
    if 'order of play' not in document or not any(value in document for value in dates):raise ValueError('Official program date/title differs')
    text=cell_text(receipt['source_path'],review['rect'])
    if any(token in text for token in ('tbf','resum','continuation')):
        raise ValueError('Resumed or unfinished match is outside the pre-match contract')
    if len(review['players'])!=2 or len(re.findall(r'\bvs\b',text))!=1 or any(not re.search(r'\b'+re.escape(normalized(name))+r'\b',text) for name in review['players']):
        raise ValueError('Exact opposing singles pair absent from reviewed cell')
    earliest=datetime.fromisoformat(review['date']+'T'+review['official_earliest_local']).replace(tzinfo=ZoneInfo(spec['timezone'])).astimezone(timezone.utc)
    if utc(decision)>=earliest:raise ValueError('Official earliest bound elapsed; verified live status required')
    return receipt,earliest


def emit(config_path,reviews_path,report_path):
    config=read(config_path)
    if digest(config['quality_protocol'])!=config['quality_protocol_sha256']:raise ValueError('Configured quality protocol changed')
    protocol=load(config['quality_protocol']);reviews=read(reviews_path)
    if not isinstance(reviews,list):raise ValueError('Explicit list of reviewed cells required')
    calendar=[]
    originals=Path(config['root'])/'state_capture/originals'
    # Use latest successful batch per tour; a stale duplicate is not another event.
    latest={}
    for receipt_path in originals.glob('*/receipt.json'):
        receipt=read(receipt_path)
        if receipt.get('http_status')==200 and receipt.get('method')=='get_fixtures':
            key=receipt['params']['event_type_key']
            if key not in latest or utc(receipt['received_at'])>utc(latest[key]['received_at']):latest[key]=receipt
    for receipt in latest.values():
        if digest(receipt['source_path'])!=receipt['sha256']:raise ValueError('Calendar source changed')
        calendar.extend((row,receipt) for row in read(receipt['source_path'])['result'])
    scheduled=defaultdict(set)
    for row,receipt in calendar:
        if state(row.get('event_status'))=='scheduled_unverified':
            for key in ('first_player_key','second_player_key'):scheduled[(str(row[key]),row['event_date'])].add(str(row['event_key']))
    conflicts=set(identity for events in scheduled.values() if len(events)>1 for identity in events)
    output=[]
    for review in reviews:
        try:
            spec=config['official_sources'][review['source_label']];at=now()
            receipt,earliest=official_proof(review,spec,at)
            matches=[]
            for row,calendar_receipt in calendar:
                if str(row['tournament_key'])!=str(spec['provider_tournament_id']) or row['event_date']!=review['date'] or str(row['tournament_season'])!=str(datetime.fromisoformat(review['date']).year):continue
                if row['event_type_type']!=('Atp Singles' if spec['circuit']=='ATP' else 'Wta Singles'):continue
                if all(abbreviation_matches(row[field],name) for field,name in zip(('event_first_player','event_second_player'),review['players'])):matches.append((row,calendar_receipt))
            if len(matches)!=1:raise ValueError('Unique oriented calendar match required')
            row,calendar_receipt=matches[0];identity=str(row['event_key'])
            if identity in conflicts:raise ValueError('Provider double booking requires source reconciliation')
            if state(row['event_status'])!='scheduled_unverified' or str(row.get('event_live'))!='0':raise ValueError('Provider reports match unavailable or started')
            if not 0<(utc(at)-utc(calendar_receipt['received_at'])).total_seconds()<=900:raise ValueError('Calendar unavailable or stale')
            start=row['event_date']+'T'+row['event_time']+':00Z'
            if utc(start)<earliest or utc(start)<=utc(at):raise ValueError('Provider estimate conflicts with official bound')
            circuit=spec['circuit'];event=dict(id='api_tennis:'+identity,sport_key='tennis_'+circuit.lower()+'_api_'+str(row['tournament_key']),
                home_team=review['players'][0],away_team=review['players'][1],commence_time=start)
            names=read(Path(protocol['data_root'])/f'models/{circuit}_current/model.json')['names'];ids=[]
            for full in review['players']:
                candidates=[pid for pid,name in names.items() if normalized(name)==normalized(full)]
                if len(candidates)!=1:raise ValueError('Canonical full name absent or ambiguous')
                ids.append(candidates[0])
            fixture=dict(event_id=event['id'],sport_key=event['sport_key'],status='scheduled',actual_start=None,
                participants=review['players'],participants_verified=True,provider_time_reconciled=True,
                provider_commence_time=start,source_kind='official_order_of_play',official_not_before=earliest.isoformat(),
                observed_at=receipt['received_at'],source_url=receipt['url'],source_path=receipt['source_path'],source_sha256=receipt['sha256'],
                evidence='Exact pair in visually reviewed official PDF cell, fresh calendar, decision before official earliest bound',
                calendar_source_path=calendar_receipt['source_path'],calendar_source_sha256=calendar_receipt['sha256'],
                calendar_received_at=calendar_receipt['received_at'],review_path=str(Path(reviews_path).resolve()),review_sha256=digest(reviews_path),
                rect=review['rect'],court=review['court'],live_status_verified=False)
            metadata=dict(metadata_verified=True,surface=spec['surface'],best_of=spec['best_of'],deciding_tiebreak=spec['deciding_tiebreak'],
                source_url=spec['url'],valid_from=review['date'],valid_to=review['date'])
            path=seal_prediction(config['quality_protocol'],dict(event=event,circuit=circuit,player_ids=ids,fixture_receipt=fixture,tournament_metadata=metadata),
                Path(config['quality_protocol']).parent/'future_predictions')
            output.append(dict(players=review['players'],status='sealed',record_path=str(path.resolve())))
        except FileExistsError:output.append(dict(players=review.get('players'),status='already_sealed'))
        except (ValueError,KeyError,TypeError,OSError) as error:
            output.append(dict(players=review.get('players'),status='excluded',reason=str(error) if isinstance(error,ValueError) else type(error).__name__))
    report=dict(schema='tennis-continuous-reviewed-emission-v1',evaluated_at=now(),reviewed=len(reviews),
        sealed=sum(r['status']=='sealed' for r in output),rows=output,provider_conflict_event_ids=sorted(conflicts),
        new_odds_credits=0,actual_bets=0)
    write_new(report_path,report)
    return report
