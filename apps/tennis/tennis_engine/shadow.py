"""Prospective, append-only tennis forecasts and bounded odds snapshots.

The module deliberately separates a provider's estimated market-close time from
verified match status.  It records research forecasts, but never publishes or
places a wager.
"""
from datetime import timedelta
import hashlib
import json
import math
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse

from .identities import Registry, reconcile
from .ingest import save_json
from .operations import Capture, coverage, now, quote_gate, select_books, utc
from .research import hybrid_forecast


PHASES = {"t_minus_120": 120, "t_minus_15": 15}


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture_phase(commence_time, observed_at, tolerance_minutes=7):
    """Return the due capture phase, or a transparent waiting/passed state."""
    if not isinstance(tolerance_minutes,(int,float)) or not 0<=tolerance_minutes<=7:
        raise ValueError('Tolerance must be from zero to seven minutes')
    start = utc(commence_time)
    observed = utc(observed_at)
    delta = (start - observed).total_seconds() / 60
    due = [name for name, minutes in PHASES.items() if abs(delta - minutes) <= tolerance_minutes]
    if len(due) > 1:
        raise ValueError("Capture windows overlap")
    if due:
        return due[0]
    if delta > max(PHASES.values()) + tolerance_minutes:
        return "waiting_t_minus_120"
    if delta > min(PHASES.values()) + tolerance_minutes:
        return "waiting_t_minus_15"
    if delta >= -tolerance_minutes:
        return "outside_capture_window"
    return "estimated_start_passed"


def capture_targets(commence_time):
    start = utc(commence_time)
    return {name: (start - timedelta(minutes=minutes)).isoformat()
            for name, minutes in PHASES.items()}


def verified_fixture(event, fixture, decision_at, max_age_seconds=900):
    """Require fresh, exact evidence; a tournament page alone is insufficient."""
    reasons = []
    if not fixture or fixture.get("event_id") != event.get("id"):
        return {"eligible": False, "reasons": ["missing_exact_fixture_receipt"]}
    if fixture.get("status") != "scheduled":
        reasons.append("fixture_not_scheduled")
    if fixture.get("actual_start"):
        reasons.append("match_already_started")
    if fixture.get("participants_verified") is not True:
        reasons.append("participants_not_verified")
    if fixture.get("provider_time_reconciled") is not True:
        reasons.append("provider_time_not_reconciled")
    source=urlparse(str(fixture.get('source_url','')))
    if not fixture.get("evidence") or source.scheme!='https' or not source.hostname:
        reasons.append("missing_source_evidence")
    if source.hostname is None or not any(source.hostname==host or source.hostname.endswith('.'+host)
                                          for host in ('atptour.com','wtatennis.com','itftennis.com','protennislive.com')):
        reasons.append('unrecognized_official_source')
    if fixture.get('source_kind')=='official_order_of_play':
        try:
            if utc(decision_at)>=utc(fixture['official_not_before']):
                reasons.append('published_not_before_passed_live_status_required')
        except (ValueError,KeyError,TypeError):reasons.append('invalid_official_not_before')
    if set(fixture.get('participants',[]))!={event.get('home_team'),event.get('away_team')}:
        reasons.append('fixture_participants_mismatch')
    if fixture.get('sport_key')!=event.get('sport_key'):
        reasons.append('fixture_sport_mismatch')
    try:
        if utc(fixture['provider_commence_time'])!=utc(event['commence_time']):
            reasons.append('fixture_schedule_changed')
    except (KeyError,ValueError,TypeError):
        reasons.append('fixture_schedule_not_bound')
    # A URL and a boolean are not an archived observation. The bytes must exist.
    try:
        if file_sha256(fixture['source_path'])!=fixture['source_sha256']:
            reasons.append('fixture_source_hash_mismatch')
    except (KeyError,OSError,ValueError,TypeError):
        reasons.append('missing_fixture_source_snapshot')
    try:
        observed = utc(fixture["observed_at"])
        decision = utc(decision_at)
        if observed > decision or (decision - observed).total_seconds() > max_age_seconds:
            reasons.append("stale_fixture_receipt")
    except (KeyError, TypeError, ValueError):
        reasons.append("invalid_fixture_time")
    return {"eligible": not reasons, "reasons": reasons}


def metadata_gate(event, metadata):
    reasons=[]
    if not metadata or metadata.get('metadata_verified') is not True:
        return ['unverified_tournament_metadata']
    if metadata.get('surface') not in ('Hard','Clay','Grass','Carpet') or metadata.get('best_of') not in (3,5) or metadata.get('deciding_tiebreak') not in (7,10):
        reasons.append('unsupported_tournament_rules')
    if not str(metadata.get('source_url','')).startswith('https://'):
        reasons.append('missing_tournament_source')
    try:
        day=utc(event['commence_time']).date().isoformat()
        if not metadata['valid_from']<=day<=metadata['valid_to']:
            reasons.append('tournament_edition_expired')
    except (KeyError,ValueError,TypeError):
        reasons.append('missing_tournament_edition')
    return reasons


def _circuit(event):
    key = event.get("sport_key", "")
    if key.startswith("tennis_atp_"):
        return "ATP"
    if key.startswith("tennis_wta_"):
        return "WTA"
    raise ValueError("Unsupported tennis circuit")


def _artifacts(model, pool):
    model = Path(model)
    pool = Path(pool)
    paths = [model / "model.json", model / "precision.npz",
             model / "training_receipt.json", pool]
    control=pool.parent.parent/(pool.parent.name.split('_')[0]+'_controls.json')
    if control.exists():paths.append(control)
    return {str(path): file_sha256(path) for path in paths}


def _fixture_map(path):
    if not path:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("fixtures", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or any(not isinstance(row, dict) or not row.get("event_id") for row in rows):
        raise ValueError("Fixture receipts must be a list with event_id")
    if len({row["event_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate fixture receipt")
    return {row["event_id"]: row for row in rows}


def build_plan(events, data_root, models_root, pools_root, identity_db,
               tournament_config, observed_at=None, fixture_file=None,
               forecast_function=hybrid_forecast):
    observed_at = observed_at or now()
    observed = utc(observed_at).isoformat()
    config_path = Path(tournament_config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    fixtures = _fixture_map(fixture_file)
    if len({e['id'] for e in events})!=len(events): raise ValueError('Duplicate calendar events')
    reconciled = {row["event_id"]: row for row in reconcile(events, Registry(identity_db))}
    records = []
    for event in events:
        circuit = _circuit(event)
        identities = reconciled[event["id"]]
        tournament = config.get(event["sport_key"])
        reasons = []
        if not identities["identities_verified"]:
            reasons.append("unverified_identity")
        metadata_reasons=metadata_gate(event,tournament)
        reasons.extend(metadata_reasons)
        fixture_check = verified_fixture(event, fixtures.get(event["id"]), observed)
        reasons.extend(fixture_check["reasons"])
        phase = capture_phase(event["commence_time"], observed)
        prediction = None
        artifacts = None
        if utc(event['commence_time'])<=utc(observed): reasons.append('estimated_start_passed')
        if identities["identities_verified"] and not metadata_reasons and utc(event['commence_time'])>utc(observed):
            players = identities["players"]
            model = Path(models_root) / f"{circuit}_current"
            pool = Path(pools_root) / f"{circuit}_pool" / "pool.json"
            try:
                artifacts = _artifacts(model, pool)
                prediction = forecast_function(
                    data_root, model, pool, players[0]["player_id"], players[1]["player_id"],
                    tournament["surface"], tournament['best_of'], tournament['deciding_tiebreak'])
                if utc(prediction['cutoff']+'T00:00:00Z')>utc(observed):
                    raise ValueError('Future model cutoff')
                if _artifacts(model,pool)!=artifacts: raise ValueError('Artifacts changed during prediction')
            except (OSError,ValueError,KeyError) as error:
                reasons.append('forecast_unavailable:'+type(error).__name__)
                prediction=None
        if prediction is None: reasons.append('missing_prediction')
        records.append({
            "event": event,
            "circuit": circuit,
            "identities": identities,
            "tournament_metadata": tournament,
            "fixture_receipt": fixtures.get(event["id"]),
            "fixture_gate": fixture_check,
            "capture_blockers": sorted(set(reasons)),
            "capture_phase": phase,
            "capture_targets": capture_targets(event["commence_time"]),
            "prediction": prediction,
            "artifact_sha256": artifacts,
            "odds_capture_allowed": phase in PHASES and not reasons,
            "release_gate": {"eligible": False, "reasons": sorted(set(reasons + ["research_shadow_only"]))},
        })
    return {
        "schema": "tennis-shadow-plan-v2",
        "observed_at": observed,
        "tournament_config_sha256": file_sha256(config_path),
        "events": records,
        "production_approved": False,
        "wagers_placed": 0,
        "note": "commence_time is a provider estimate used for capture planning, not proof of actual start",
    }


def _h2h_market_view(event, prediction):
    """De-vig two-way H2H books and compare the exact selection with best observed price."""
    if not prediction:
        return []
    names = {event["home_team"], event["away_team"]}
    model = {event["home_team"]: prediction["winner_A"],
             event["away_team"]: prediction["winner_B"]}
    rows = []
    for book in event.get("bookmakers", []):
        for market in book.get("markets", []):
            if market.get("key") != "h2h":
                continue
            outcomes = market.get("outcomes", [])
            if len(outcomes) != 2 or {row.get("name") for row in outcomes} != names:
                continue
            implied = [1 / row["price"] for row in outcomes
                       if isinstance(row.get("price"), (int, float)) and row["price"] > 1]
            if len(implied) != 2:
                continue
            overround = sum(implied)
            for outcome, raw in zip(outcomes, implied):
                fair = raw / overround
                probability = model[outcome["name"]]
                rows.append({
                    "bookmaker": book["key"], "selection": outcome["name"],
                    "decimal_odds": outcome["price"], "overround": overround,
                    "de_vig_probability": fair, "model_probability": probability,
                    "model_edge": probability - fair,
                    "model_expected_return_per_unit": probability * outcome["price"] - 1,
                    "executable": False,
                })
    return rows


def write_immutable(root, payload):
    """Exclusive append-only local file; hash detects edits, not an external timestamp proof."""
    root = Path(root)
    record_id = uuid4().hex
    folder = root / "shadow" / payload["observed_at"].replace(":", "-") / record_id
    target = folder / "record.json"
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False).encode()
    wrapped = {**payload, "record_id": record_id,
               "payload_sha256": hashlib.sha256(canonical).hexdigest()}
    folder.mkdir(parents=True,exist_ok=False)
    with target.open('x',encoding='utf-8') as handle:
        json.dump(wrapped,handle,ensure_ascii=False,indent=2,allow_nan=False)
    return target


def verify_record(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    digest=data.pop('payload_sha256'); data.pop('record_id')
    raw=json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
    if hashlib.sha256(raw).hexdigest()!=digest: raise ValueError('Shadow record hash mismatch')
    return data


def run_shadow(data_root, models_root, pools_root, operations_root, identity_db,
               tournament_config, api_key, credit_cap=0, account_reserve=6000,
               regions="eu,uk", fixture_file=None, capture_odds=False,
               tolerance_minutes=7, client_factory=Capture, plan_builder=build_plan,
               calibration_root=None,refresh_official=False):
    """Refresh the free calendar and optionally capture only due, fully verified events."""
    capture_phase('2000-01-01T00:00:00Z','2000-01-01T00:00:00Z',tolerance_minutes)
    client = client_factory(operations_root, api_key, credit_cap, account_reserve)
    sports, sports_receipt = client.request("sports")
    events = []
    calendar_receipts = []
    for sport in sports:
        if sport.get("group") == "Tennis" and sport.get("key", "").startswith(("tennis_atp_", "tennis_wta_")):
            rows, receipt = client.request(f"sports/{sport['key']}/events")
            events.extend(rows)
            calendar_receipts.append(receipt)
    decision_at = now()
    if refresh_official:
        from .official import capture_official
        fixture_file=capture_official(events,operations_root)
        decision_at=now()
    plan = plan_builder(events, data_root, models_root, pools_root, identity_db,
                      tournament_config, decision_at, fixture_file)
    plan["calendar_receipts"] = [sports_receipt, *calendar_receipts]
    if fixture_file:plan['fixture_file']=str(fixture_file)
    plan["paid_capture_requested"] = bool(capture_odds)
    plan["odds"] = []
    if calibration_root:
        for row in plan['events']:
            if row.get('prediction'):
                path=Path(calibration_root)/(row['circuit']+'_calibration_v2')/'calibrators.json'
                try:
                    profiles=json.loads(path.read_text(encoding='utf-8'))
                    cutoff=utc(row['prediction']['cutoff']+'T00:00:00Z')
                    if any(utc(p['training_last_period']+'T00:00:00Z')>=cutoff-timedelta(days=35) for p in profiles.values()):
                        raise ValueError('Calibration overlaps forecast cutoff')
                    row['prediction']['derivative_calibrators']=profiles
                    row['calibration_artifact']={'path':str(path),'sha256':file_sha256(path)}
                except (OSError,ValueError,KeyError):
                    row['calibration_status']='unavailable_raw_markets_only'
    plan['prediction_sealed_at']=now()
    # Seal predictions BEFORE requesting prices, including when the next call fails.
    prequote=write_immutable(operations_root,plan)
    plan['prequote_record']={'path':str(prequote),'sha256':file_sha256(prequote)}
    plan['errors']=[]
    client.db.execute('CREATE TABLE IF NOT EXISTS shadow_claims(capture_key TEXT PRIMARY KEY,state TEXT,record_path TEXT)')
    client.db.commit()
    for record in plan["events"]:
        event = record["event"]
        checked_at=now()
        phase = capture_phase(event["commence_time"], checked_at, tolerance_minutes)
        record["capture_phase"] = phase
        fixture_gate=verified_fixture(event,record.get('fixture_receipt'),checked_at)
        allowed = (phase in PHASES and not record.get('capture_blockers') and
                   fixture_gate['eligible'] and record['prediction'] is not None and
                   not metadata_gate(event,record.get('tournament_metadata')) and
                   record['identities']['identities_verified'])
        record["odds_capture_allowed"] = bool(allowed)
        if not capture_odds or not allowed:
            continue
        capture_key='|'.join((event['sport_key'],event['id'],event['commence_time'],phase))
        # Unique database claim prevents concurrent/repeated paid captures of one window.
        with client.db:
            inserted=client.db.execute('INSERT OR IGNORE INTO shadow_claims VALUES (?,?,?)',
                                      (capture_key,'reserved',str(prequote))).rowcount
        if not inserted:
            record['capture_skipped']='window_already_claimed';continue
        try:
            path = f"sports/{event['sport_key']}/events/{event['id']}"
            client.request('sports')  # Refresh shared-account balance just before spending.
            inventory, inventory_receipt = client.request(path + "/markets", {"regions": regions})
            if inventory.get('id')!=event['id']: raise ValueError('Inventory event mismatch')
            books, markets = select_books(inventory)
            if not markets:
                record['capture_skipped']='no_observed_markets';continue
            before_quote=now()
            if capture_phase(event['commence_time'],before_quote,tolerance_minutes)!=phase or not verified_fixture(event,record['fixture_receipt'],before_quote)['eligible']:
                raise ValueError('Window or fixture expired during inventory request')
            quoted, quote_receipt = client.request(path + "/odds", {
                "bookmakers": ",".join(books), "markets": ",".join(markets),
                "oddsFormat": "decimal"})
            # Provider sides and time can change between requests; never reuse an old orientation.
            if any(quoted.get(key)!=event.get(key) for key in ('id','sport_key','home_team','away_team','commence_time')):
                raise ValueError('Quoted event changed; fresh reconciliation required')
            evaluated_at=now()  # A price cannot be available before its response is received.
            gate_rows = []
            for book in quoted.get("bookmakers", []):
                for market in book.get("markets", []):
                    gate=quote_gate(quoted,book,market,quote_receipt['received_at'],evaluated_at,
                                    True,record['fixture_receipt'])
                    fresh=verified_fixture(event,record['fixture_receipt'],evaluated_at)
                    reasons=sorted(set(gate['reasons']+fresh['reasons']))
                    if capture_phase(event['commence_time'],evaluated_at,tolerance_minutes)!=phase:
                        reasons.append('capture_window_elapsed')
                    gate_rows.append({'bookmaker':book['key'],'market':market['key'],
                                      'data_eligible':not reasons,'reasons':reasons,'executable':False})
            from .markets import compare_offered
            plan["odds"].append({
                "event_id": event["id"], "phase": phase,'evaluated_at':evaluated_at,
                "inventory_receipt": inventory_receipt, "quote_receipt": quote_receipt,
                "coverage": coverage([quoted]),
                "market_comparison": compare_offered(quoted,record['prediction'],gate_rows),
                "release_gates": gate_rows, "executable": False,
            })
            with client.db:
                client.db.execute('UPDATE shadow_claims SET state=? WHERE capture_key=?',('captured',capture_key))
        except (ValueError,RuntimeError,OSError,KeyError,TypeError) as error:
            # Do not persist raw exception strings, which could contain transport credentials.
            plan['errors'].append({'event_id':event['id'],'type':type(error).__name__,
                                   'reason':'Capture incomplete; inspect persisted receipts; claim retained'})
    plan["remaining_credits"] = client.remaining
    plan['budget']=client.budget_report(decision_at[:7])
    plan['completed_at']=now()
    target = write_immutable(operations_root, plan)
    client.db.close()
    return {"record_path": str(target), "observed_at": plan["observed_at"],
            "events": len(plan["events"]), "paid_odds_captures": len(plan["odds"]),
            'capture_errors':len(plan['errors']),'budget':plan['budget'],
            "remaining_credits": plan["remaining_credits"], "production_approved": False}
