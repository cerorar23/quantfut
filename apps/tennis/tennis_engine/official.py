"""Strict adapter for the two reviewed 2026 official finals order-of-play PDFs.

This adapter is intentionally not a generic PDF schedule scraper. An unexpected
layout/date/pair is rejected. It verifies the published not-before schedule, not
live court status after that time.
"""
from datetime import datetime,timezone,timedelta
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from uuid import uuid4
from .operations import now,utc
from .identities import normalized
from .ingest import save_json

SOURCES={
    'tennis_atp_shanghai_masters':('https://www.protennislive.com/posting/2026/5014/op.pdf','ATP'),
    'tennis_wta_wuhan_open':('https://wtafiles.wtatennis.com/pdf/draws/2026/1075/OP.pdf','WTA')}


def parse_final(text,event):
    if event['sport_key'] not in SOURCES:raise ValueError('No reviewed official adapter for this tournament')
    flat=' '.join(text.split());names=[normalized(event[k]) for k in ('home_team','away_team')]
    if any(len(name.split())<2 for name in names):raise ValueError('Full known participant names required')
    clean=normalized(flat)
    positions=[clean.find(name) for name in names]
    if min(positions)<0:raise ValueError('Exact known participants absent from official order')
    low,high=sorted(positions)
    span=clean[low:high]
    if high-low>150 or len(re.findall(r'\bvs\b',span))!=1:
        raise ValueError('Participants not proved to be opposing each other')
    circuit=SOURCES[event['sport_key']][1]
    if circuit=='WTA':
        dates=re.findall(r'ORDER OF PLAY\s*[-–]\s*\w+,\s*(\d{1,2}\s+\w+\s+\d{4})',flat,re.I)
        clocks=re.findall(r'Not before\s+(\d{1,2}:\d{2}\s*[AP]M)',flat,re.I)
        if len(dates)!=1 or len(clocks)!=1:raise ValueError('Unrecognized or ambiguous WTA final layout')
        day=datetime.strptime(dates[0],'%d %B %Y')
        clock=datetime.strptime(clocks[0].upper().replace('  ',' '),'%I:%M %p').time()
    else:
        dates=re.findall(r'ORDER OF PLAY\s*[-–]\s*\w+,\s*(\w+\s+\d{1,2},\s*\d{4})',flat,re.I)
        clocks=re.findall(r'Not Before\s+(\d{1,2}:\d{2})(?!\s*[AP]M)',flat,re.I)
        if len(dates)!=1 or len(clocks)!=1:raise ValueError('Unrecognized or ambiguous ATP final layout')
        day=datetime.strptime(dates[0],'%B %d, %Y')
        clock=datetime.strptime(clocks[0],'%H:%M').time()
    if day.date().isoformat()!='2026-10-18' or 'hard' not in clean:
        raise ValueError('Adapter edition/date or surface mismatch')
    # Both reviewed venues are in China Standard Time, UTC+8, without DST.
    scheduled=datetime.combine(day.date(),clock,tzinfo=timezone(timedelta(hours=8))).astimezone(timezone.utc)
    return {'official_not_before':scheduled.isoformat(),'schedule_date':day.date().isoformat(),
            'timezone_basis':'China Standard Time UTC+08:00',
            'provider_time_reconciled':scheduled==utc(event['commence_time'])}


def capture_official(events,root,transport=None):
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError
    folder=Path(root)/'official'/uuid4().hex;folder.mkdir(parents=True,exist_ok=False)
    fixtures=[];errors=[];sources={}
    for event in events:
        sport=event.get('sport_key')
        if sport not in SOURCES:continue
        url,circuit=SOURCES[sport]
        try:
            if sport not in sources:
                requested=now()
                if transport:raw=transport(url)
                else:
                    with urlopen(Request(url,headers={'User-Agent':'TennisResearch/0.2 official schedule observation'}),timeout=30) as response:
                        if urlparse(response.url).hostname!=urlparse(url).hostname:raise ValueError('Unexpected source redirect')
                        raw=response.read(5000001)
                received=now()
                if len(raw)>5000000 or not raw.startswith(b'%PDF'):raise ValueError('Expected a bounded PDF response')
                path=folder/(circuit+'_order.pdf');path.write_bytes(raw)
                receipt={'source_url':url,'source_path':str(path.resolve()),'source_sha256':hashlib.sha256(raw).hexdigest(),
                         'requested_at':requested,'received_at':received}
                save_json(folder/(circuit+'_receipt.json'),receipt)
                reader=PdfReader(io.BytesIO(raw))
                if len(reader.pages)!=1:raise ValueError('Expected reviewed one-page final order')
                text=reader.pages[0].extract_text()
                (folder/(circuit+'_order.txt')).write_text(text,encoding='utf-8')
                sources[sport]=(receipt,text)
            receipt,text=sources[sport];parsed=parse_final(text,event)
            future=utc(receipt['received_at'])<utc(parsed['official_not_before'])
            fixtures.append({**receipt,**parsed,'event_id':event['id'],'sport_key':sport,
                             'participants':[event['home_team'],event['away_team']],
                             'participants_verified':True,'provider_commence_time':event['commence_time'],
                             'status':'scheduled' if future else 'requires_live_status',
                             'actual_start':None,'observed_at':receipt['received_at'],
                             'source_kind':'official_order_of_play',
                             'evidence':'Reviewed 2026 final order: exact participant pair, date, court surface and not-before time; observation before that time.',
                             'live_status_verified':False})
        except (OSError,ValueError,RuntimeError,ImportError,PyPdfError) as error:
            errors.append({'event_id':event.get('id'),'type':type(error).__name__,'reason':'Official order unavailable or did not match reviewed template'})
    target=folder/'fixtures.json';save_json(target,{'fixtures':fixtures,'errors':errors})
    return target
