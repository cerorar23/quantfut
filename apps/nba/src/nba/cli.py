import argparse
import json
from pathlib import Path

from .audit import Ledger, digest, write_json
from .config import Settings
from .coverage import audit_hoopr
from .evaluate import backtest
from .github_archive import download_inventory, select_shufinskiy, audit_tar_csv
from .ingest import capture, import_archive, read_dataset
from .model import forecast, contract_probabilities
from .sportsdataverse import import_release
from .current import capture_rosters
from .startup import startup_forecast, startup_backtest
from .context import build_context, capture_public_context
from .calibration import calibration_report
from .delivery import Outbox, telegram_sender
from .markets import validate_quote
from .extra_sources import capture_supplemental, audit_lineups, audit_rotations
from .backfill import build_inventory, capture_batch
from .injury_pdf import capture_reports
from .event_listing import event_listing, source_review
from .odds_sources import source_plan
from .prop_feed import capture_props, attach_official_identities
from .paper import register, score_result, capture_official_result, run_pilot, summarize_scores, PROTOCOL as PAPER_PROTOCOL
from .paper_followup import build_plan, advance
from .basketball_reference import capture_days, seed_cache, recover_dataset


def main():
    parser = argparse.ArgumentParser(description="NBA independent local research pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    props = sub.add_parser("capture-props", help="finite US/AU player-prop collection with explicit credit budget")
    props.add_argument("--credit-cap", type=int, required=True)
    props.add_argument("--max-events", type=int, default=8)
    props.add_argument("--key-file", type=Path, help="explicit local file containing ODDS_API_KEY; only that variable is read")
    props.add_argument("--output-dir", type=Path, required=True)
    props.add_argument("--identity-file", type=Path, help="optional previously captured official identity reference JSON")
    props.add_argument("--regular-only", action="store_true", help="exclude preseason from this finite capture")
    paper = sub.add_parser("paper-register", help="seal a new conditional shadow cohort; no bets or publication")
    paper.add_argument("--feed", type=Path, required=True)
    paper.add_argument("--identity-file", type=Path, required=True)
    paper.add_argument("--fullgame-labels", type=Path, required=True)
    paper.add_argument("--boxes", type=Path, required=True)
    paper.add_argument("--protocol", type=Path, default=PAPER_PROTOCOL)
    paper.add_argument("--injury-receipt", type=Path, help="optional current ESPN injury receipt; never final availability")
    paper.add_argument("--output-dir", type=Path, required=True)
    pilot = sub.add_parser("paper-run", help="validate history, capture regular props and seal in one bounded operation")
    pilot.add_argument("--credit-cap", type=int, required=True)
    pilot.add_argument("--max-events", type=int, default=3)
    pilot.add_argument("--key-file", type=Path)
    pilot.add_argument("--identity-file", type=Path, required=True)
    pilot.add_argument("--fullgame-labels", type=Path, required=True)
    pilot.add_argument("--boxes", type=Path, required=True)
    pilot.add_argument("--injury-receipt", type=Path)
    pilot.add_argument("--output-dir", type=Path, required=True)
    result_capture = sub.add_parser("paper-capture-result", help="one free public official NBA final-boxscore request")
    result_capture.add_argument("--nba-game-id", required=True)
    result_capture.add_argument("--game-slug", help="official NBA web boxscore slug, e.g. hou-vs-okc-0022500001; alternate to CDN")
    result_capture.add_argument("--output-dir", type=Path, required=True)
    paper_score = sub.add_parser("paper-score", help="score a sealed event against received final official NBA data")
    paper_score.add_argument("--registration", type=Path, required=True)
    paper_score.add_argument("--event-id", required=True)
    paper_score.add_argument("--receipt", type=Path, required=True)
    paper_score.add_argument("--output-dir", type=Path, required=True)
    paper_summary=sub.add_parser("paper-summary",help="descriptive evaluation summary; reject duplicate observation units")
    paper_summary.add_argument("--evaluations",type=Path,nargs='+',required=True)
    paper_summary.add_argument("--output-dir",type=Path,required=True)
    followup=sub.add_parser('paper-followup-plan',help='seal exact official mappings and bounded lifecycle for an existing cohort')
    followup.add_argument('--cohort',type=Path,required=True)
    followup.add_argument('--receipts',type=Path,required=True)
    followup.add_argument('--raw-folder',type=Path,required=True)
    followup.add_argument('--output-dir',type=Path,required=True)
    advance_parser=sub.add_parser('paper-advance',help='run due paper jobs once; no bets, no automatic retries')
    advance_parser.add_argument('--plan',type=Path,required=True)
    advance_parser.add_argument('--state',type=Path,required=True)
    advance_parser.add_argument('--output-dir',type=Path,required=True)
    advance_parser.add_argument('--key-file',type=Path,help='only ODDS_API_KEY read for one bounded future closing capture')
    sources = sub.add_parser("odds-source-plan", help="offline selected-bookmaker plan; no API calls")
    sources.add_argument("--event-id")
    sources.add_argument("--sport", choices=["basketball_nba", "basketball_nba_preseason"], default="basketball_nba")
    listing = sub.add_parser("audit-event-listing")
    listing.add_argument("--raw", type=Path, required=True)
    listing.add_argument("--receipt", type=Path, required=True)
    listing.add_argument("--game-id", required=True)
    listing.add_argument("--listing-as-of", required=True)
    listing.add_argument("--as-of", required=True)
    listing.add_argument("--observations", type=Path, required=True)
    listing.add_argument("--output-dir", type=Path, required=True)
    get = sub.add_parser("capture")
    get.add_argument("--years", type=int, nargs="+", default=[2022, 2023, 2024, 2025, 2026])
    imp = sub.add_parser("import")
    imp.add_argument("manifest", type=Path)
    sdv = sub.add_parser("import-sdv")
    sdv.add_argument("manifest", type=Path)
    sdv.add_argument("--team-manifest", type=Path, required=True)
    sdv.add_argument("--years", type=int, nargs="+", default=[2022, 2023, 2024, 2025, 2026])
    current = sub.add_parser("capture-rosters")
    current.add_argument("--season-year", type=int, required=True)
    context = sub.add_parser("current-context")
    context.add_argument("--roster-manifest", type=Path, required=True)
    context.add_argument("--probe-manifest", type=Path, required=True)
    context.add_argument("--profile-manifest", type=Path)
    context.add_argument("--dataset", type=Path, required=True)
    context.add_argument("--as-of", required=True)
    context.add_argument("--output-dir", type=Path, required=True)
    context_capture = sub.add_parser("capture-context")
    context_capture.add_argument("--date", required=True)
    context_capture.add_argument("--reference-manifest", type=Path, required=True)
    calibration = sub.add_parser("calibration-diagnostics")
    calibration.add_argument("--dataset", type=Path, required=True)
    calibration.add_argument("--predictions", type=Path, required=True)
    calibration.add_argument("--output-dir", type=Path, required=True)
    quote_audit = sub.add_parser("audit-quotes")
    quote_audit.add_argument("input", type=Path)
    quote_audit.add_argument("--as-of", required=True)
    quote_audit.add_argument("--output-dir", type=Path, required=True)
    test_message = sub.add_parser("telegram-test")
    test_message.add_argument("--as-of", required=True)
    test_message.add_argument("--send", action="store_true", help="explicit operational test; requires NBA private configuration")
    evaluation = sub.add_parser("backtest")
    evaluation.add_argument("--protocol", type=Path, default=Path(__file__).resolve().parents[2] / "protocol.json")
    evaluation.add_argument("--dataset", type=Path)
    evaluation.add_argument("--output-dir", type=Path)
    startup = sub.add_parser("startup-backtest")
    startup.add_argument("--dataset", type=Path, required=True)
    startup.add_argument("--output-dir", type=Path, required=True)
    startup.add_argument("--protocol", type=Path, default=Path(__file__).resolve().parents[2] / "startup_protocol.json")
    opening = sub.add_parser("startup-scenario")
    opening.add_argument("--dataset", type=Path, required=True)
    opening.add_argument("--player-id", type=int, required=True)
    opening.add_argument("--as-of", required=True)
    opening.add_argument("--season", required=True)
    scenario = sub.add_parser("scenario")
    scenario.add_argument("--player-id", type=int, required=True)
    scenario.add_argument("--as-of", required=True)
    scenario.add_argument("--season", required=True)
    scenario.add_argument("--minutes", type=float, required=True)
    scenario.add_argument("--line", type=float)
    archives = sub.add_parser("capture-pbp")
    archives.add_argument("inventory", type=Path)
    archives.add_argument("--start", type=int, default=1996)
    archives.add_argument("--end", type=int, default=2025)
    audit = sub.add_parser("audit-pbp")
    audit.add_argument("manifest", type=Path)
    hoopr = sub.add_parser("audit-hoopr")
    hoopr.add_argument("manifest", type=Path)
    sub.add_parser("capture-lineups")
    rotations = sub.add_parser("capture-rotations")
    rotations.add_argument("--game-ids", nargs="+", required=True)
    lineup_audit = sub.add_parser("audit-lineups")
    lineup_audit.add_argument("manifest", type=Path)
    lineup_audit.add_argument("--context-manifest", type=Path, required=True)
    lineup_audit.add_argument("--as-of", required=True)
    lineup_audit.add_argument("--output-dir", type=Path, required=True)
    rotation_audit = sub.add_parser("audit-rotations")
    rotation_audit.add_argument("manifest", type=Path)
    rotation_audit.add_argument("--dataset", type=Path, required=True)
    rotation_audit.add_argument("--output-dir", type=Path, required=True)
    sub.add_parser("status")
    sub.add_parser("verify-ledger")
    pending = sub.add_parser("backfill-inventory")
    pending.add_argument("release_manifest", type=Path)
    pending.add_argument("--team-manifest", type=Path, required=True)
    pending.add_argument("--base-report", type=Path, required=True)
    pending.add_argument("--years", type=int, nargs="+", default=[2022, 2023, 2024, 2025, 2026])
    pending.add_argument("--output", type=Path, required=True)
    batch = sub.add_parser("capture-backfill")
    batch.add_argument("--kind", choices=["boxscore", "rotation"], required=True)
    batch.add_argument("--game-ids", nargs="+", required=True)
    injury_capture = sub.add_parser("capture-injury-reports")
    injury_capture.add_argument("--urls", nargs="+", required=True)
    bref_capture = sub.add_parser("capture-bref")
    bref_capture.add_argument("--dates", nargs="+", required=True)
    bref_capture.add_argument("--seed-manifest", type=Path)
    bref_import = sub.add_parser("recover-bref")
    bref_import.add_argument("--inventory", type=Path, required=True)
    bref_import.add_argument("--release-manifest", type=Path, required=True)
    bref_import.add_argument("--team-manifest", type=Path, required=True)
    bref_import.add_argument("--base-report", type=Path, required=True)
    bref_import.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "paper-register":
        print(json.dumps(register(args.feed,args.identity_file,args.fullgame_labels,args.boxes,args.output_dir,args.protocol,args.injury_receipt)))
        return
    if args.command == "paper-capture-result":
        receipt=capture_official_result(args.nba_game_id,args.output_dir,args.game_slug)
        print(json.dumps(dict(receipt=receipt.as_posix(),**json.loads(receipt.read_bytes()))))
        return
    if args.command == "paper-score":
        print(json.dumps(score_result(args.registration,args.event_id,args.receipt,args.output_dir)))
        return
    if args.command == "paper-summary":
        print(json.dumps(summarize_scores(args.evaluations,args.output_dir)))
        return
    if args.command == 'paper-followup-plan':
        plan=build_plan(args.cohort,args.receipts,args.raw_folder,args.output_dir)
        print(json.dumps(dict(events=len(plan['mappings']),units=plan['unique_units'],future_closing_credit_cap=plan['total_closing_credit_cap'],production_ready=False)))
        return
    if args.command == 'paper-advance':
        ownership=args.state.with_suffix('.owner.json')
        if ownership.exists():
            handoff=json.loads(ownership.read_bytes())
            if handoff.get('retired_local_executor') is not False:
                parser.error('this local executor was retired after VPS handoff; observe the server, never duplicate its closing capture')
        import os,re
        key=os.environ.get('NBA_ODDS_API_KEY')
        if args.key_file:
            match=re.search(r'^ODDS_API_KEY\s*=\s*(.+)$',args.key_file.read_text(encoding='utf-8-sig'),re.M)
            key=match[1].strip().strip('\"\'') if match else None
        print(json.dumps(advance(args.plan,args.state,args.output_dir,key)))
        return
    if args.command in ("capture-props", "paper-run"):
        import os
        import re
        key = os.environ.get("NBA_ODDS_API_KEY")
        if args.key_file:
            match = re.search(r'^ODDS_API_KEY\s*=\s*(.+)$', args.key_file.read_text(encoding='utf-8-sig'), re.M)
            key = match[1].strip().strip('\"\'') if match else None
        if not key or key == "YOUR_KEY":
            parser.error("existing provider key required via NBA_ODDS_API_KEY or explicit --key-file")
        if args.command=="paper-run":
            print(json.dumps(run_pilot(args.output_dir,key,args.credit_cap,args.identity_file,args.fullgame_labels,args.boxes,
                maximum_events=args.max_events,injury_receipt=args.injury_receipt)))
            return
        result = capture_props(args.output_dir, key, args.credit_cap, maximum_events=args.max_events, regular_only=args.regular_only)
        if args.identity_file:
            from datetime import UTC, datetime
            joined = attach_official_identities(json.loads((args.output_dir/"pairs.json").read_bytes()),
                json.loads(args.identity_file.read_bytes()), datetime.now(UTC).isoformat())
            write_json(args.output_dir/"pairs_identified.json", joined)
            result['identified_pairs'] = sum(p['identity_verified'] for p in joined)
            result['identified_quote_file'] = (args.output_dir/"pairs_identified.json").as_posix()
            write_json(args.output_dir/"result.json", result)
        print(json.dumps(result))
        return
    if args.command == "odds-source-plan":
        print(json.dumps(source_plan(args.event_id, args.sport), ensure_ascii=False, indent=2))
        return
    if args.command == "audit-event-listing":
        if args.output_dir.exists() and any(args.output_dir.iterdir()):
            raise ValueError("output must be empty; preserve previous evidence")
        event = event_listing(args.raw.read_bytes(), json.loads(args.receipt.read_bytes()),
            args.game_id, args.listing_as_of)
        result = source_review(event, json.loads(args.observations.read_bytes()), args.as_of)
        write_json(args.output_dir / "event_listing.json", event)
        write_json(args.output_dir / "source_review.json", result)
        print(json.dumps(dict(listed_players=result['listed_players'],
            blockers=result['blockers'], pregame_window_open=result['pregame_window_open'],actionable=False)))
        return
    if args.command == "backtest" and bool(args.dataset) != bool(args.output_dir):
        parser.error("custom backtest requires both --dataset and --output-dir")
    settings = Settings.load()
    root = settings.data_dir
    ledger = Ledger(root / "audit.sqlite")
    if args.command == "capture-bref":
        cache = root / "raw" / "basketball_reference"
        if args.seed_manifest:
            seed_cache(cache, args.seed_manifest)
        manifest = capture_days(cache, args.dates)
        ledger.append("basketball_reference_capture", dict(path=manifest.as_posix(), sha256=digest(manifest)))
        print(manifest)
        return
    if args.command == "recover-bref":
        result = recover_dataset(root / "raw" / "basketball_reference", args.inventory,
            args.release_manifest, args.team_manifest, args.base_report, args.output_dir)
        report = args.output_dir / "recovery.json"
        ledger.append("basketball_reference_recovery", dict(path=report.as_posix(), sha256=digest(report), summary=result["summary"]))
        print(json.dumps(result["summary"]))
        return
    if args.command == "backfill-inventory":
        result = build_inventory(args.release_manifest, args.team_manifest, args.base_report, args.years, args.output)
        ledger.append("backfill_inventory", dict(path=args.output.as_posix(), sha256=digest(args.output), summary=result["summary"]))
        print(json.dumps(result["summary"]))
        return
    if args.command == "capture-backfill":
        manifest = capture_batch(root / "raw" / "official_backfill", args.game_ids, args.kind)
        ledger.append("official_backfill_capture", dict(manifest=manifest.as_posix(), sha256=digest(manifest)))
        print(manifest)
        return
    if args.command == "capture-injury-reports":
        manifest = capture_reports(root / "raw" / "injury_reports", args.urls)
        ledger.append("injury_pdf_capture", dict(manifest=manifest.as_posix(), sha256=digest(manifest)))
        print(manifest)
        return
    if args.command in {"current-context", "calibration-diagnostics", "audit-quotes", "audit-lineups", "audit-rotations"}:
        if args.output_dir.exists() and any(args.output_dir.iterdir()):
            raise ValueError("output must be empty; preserve previous evidence")
    if args.command in {"capture-lineups", "capture-rotations"}:
        result = capture_supplemental(root / "raw/supplemental", None if args.command == "capture-lineups" else args.game_ids)
        result["ledger_hash"] = ledger.append("supplemental_public_capture", result)
    elif args.command == "audit-lineups":
        result = audit_lineups(args.manifest, args.context_manifest, args.as_of)
        write_json(args.output_dir / "lineups.json", result)
        result = dict(summary=result["summary"], report_path=(args.output_dir / "lineups.json").as_posix(),
                      report_sha256=digest(args.output_dir / "lineups.json"), actionable=False)
        result["ledger_hash"] = ledger.append("public_lineup_observations", result)
    elif args.command == "audit-rotations":
        result = audit_rotations(args.manifest, read_dataset(args.dataset))
        result["input_hashes"][str(args.dataset)] = digest(args.dataset)
        write_json(args.output_dir / "rotations.json", result)
        result = dict(summary=result["summary"], report_path=(args.output_dir / "rotations.json").as_posix(),
                      report_sha256=digest(args.output_dir / "rotations.json"), actionable=False)
        result["ledger_hash"] = ledger.append("historical_quarter_lineup_audit", result)
    elif args.command == "capture":
        result = {"manifest": str(capture(root / "raw/github", args.years))}
    elif args.command == "import":
        result = import_archive(args.manifest, root / "normalized")
        result["ledger_hash"] = ledger.append("archive_import", result)
    elif args.command == "import-sdv":
        result = import_release(args.manifest, args.team_manifest, root / "normalized/sportsdataverse", args.years)
        result = {**result, "ledger_hash": ledger.append("sportsdataverse_import", result)}
    elif args.command == "capture-rosters":
        result = capture_rosters(root / "raw/espn/rosters", args.season_year)
        result["ledger_hash"] = ledger.append("current_roster_snapshot", result)
    elif args.command == "current-context":
        protocol_path = Path(__file__).resolve().parents[2] / "startup_protocol.json"
        protocol = json.loads(protocol_path.read_text())
        result = build_context(args.roster_manifest, args.probe_manifest, args.dataset, protocol, args.as_of, args.profile_manifest)
        write_json(args.output_dir / "context.json", result)
        result = dict(summary=result["summary"], report_path=(args.output_dir / "context.json").as_posix(),
                      report_sha256=digest(args.output_dir / "context.json"), actionable=False)
        result["ledger_hash"] = ledger.append("current_context_research", result)
    elif args.command == "capture-context":
        result = capture_public_context(root / "raw/public_context", args.date, args.reference_manifest)
        result["ledger_hash"] = ledger.append("prospective_public_context_capture", result)
    elif args.command == "calibration-diagnostics":
        package = Path(__file__).resolve().parents[2]
        protocol = json.loads((package / "startup_protocol.json").read_text())
        hashes = {str(p): digest(p) for p in (args.dataset, args.predictions, package / "startup_protocol.json",
                  package / "calibration_protocol.json", package / "src/nba/calibration.py", package / "src/nba/startup.py")}
        ledger.append("diagnostic_protocol_before_evaluation", dict(input_hashes=hashes))
        result = calibration_report(read_dataset(args.dataset), json.loads(args.predictions.read_text()), protocol)
        result["input_hashes"] = hashes
        write_json(args.output_dir / "calibration.json", result)
        result["ledger_hash"] = ledger.append("startup_calibration_diagnostic", result)
    elif args.command == "audit-quotes":
        accepted, rejected = [], []
        for index, quote in enumerate(json.loads(args.input.read_text())):
            try:
                accepted.append(dict(row=index, research_validation=validate_quote(quote, args.as_of)))
            except (ValueError, TypeError, KeyError) as exc:
                rejected.append(dict(row=index, reason=str(exc)))
        result = dict(accepted=accepted, rejected=rejected, actionable=False, input_sha256=digest(args.input))
        write_json(args.output_dir / "quotes.json", result)
        result["ledger_hash"] = ledger.append("contract_quote_audit", result)
    elif args.command == "telegram-test":
        sender = telegram_sender(root / "private/telegram_link.json") if args.send else None
        outbox = Outbox(root / "delivery")
        identifier = outbox.queue_test(args.as_of)
        result = outbox.dispatch_test(identifier, args.as_of, sender=sender, dry_run=not args.send)
        result.update(id=identifier, delivery_ledger=outbox.ledger.verify())
    elif args.command in ("backtest", "startup-backtest"):
        protocol = json.loads(args.protocol.read_text())
        dataset = args.dataset or root / "normalized/player_games.jsonl.gz"
        output = args.output_dir or root / "reports"
        if args.output_dir and output.exists() and any(output.iterdir()):
            raise ValueError("custom evaluation output must be empty; preserve previous evidence")
        ledger.append("research_protocol_before_evaluation", dict(protocol=protocol, protocol_sha256=digest(args.protocol),
                      dataset_path=dataset.as_posix(), dataset_sha256=digest(dataset)))
        evaluate = startup_backtest if args.command == "startup-backtest" else backtest
        result, predictions = evaluate(read_dataset(dataset), protocol)
        result.update(dataset_sha256=digest(dataset), protocol_sha256=digest(args.protocol))
        result.update(dataset_path=dataset.as_posix())
        write_json(output / "backtest.json", result)
        write_json(output / "backtest_rows.json", predictions)
        result["ledger_hash"] = ledger.append("retrospective_backtest", result)
    elif args.command == "startup-scenario":
        protocol_path = Path(__file__).resolve().parents[2] / "startup_protocol.json"
        protocol = json.loads(protocol_path.read_text())
        history = [r for r in read_dataset(args.dataset) if r["player_id"] == args.player_id]
        result = startup_forecast(history, args.as_of, args.season, protocol)
        result.pop("pmf", None)
        result.pop("baseline_pmf", None)
        result.update(player_id=args.player_id, as_of=args.as_of, season=args.season,
                      dataset_sha256=digest(args.dataset), protocol_sha256=digest(protocol_path), actionable=False)
        result["ledger_hash"] = ledger.append("hypothetical_startup_scenario", result)
    elif args.command == "scenario":
        protocol = json.loads((Path(__file__).resolve().parents[2] / "protocol.json").read_text())
        rows = [r for r in read_dataset(root / "normalized/player_games.jsonl.gz") if r["player_id"] == args.player_id]
        result = forecast(rows, args.as_of, args.season, protocol, args.minutes)
        if result["status"] != "abstain":
            if args.line is not None:
                result["line_probabilities"] = contract_probabilities(result["pmf"], args.line)
            result.pop("pmf")
            result.pop("baseline_pmf")
        result.update(mode="hypothetical_minutes_scenario", player_id=args.player_id, as_of=args.as_of,
                      season=args.season, requested_minutes=args.minutes, actionable=False)
        result["ledger_hash"] = ledger.append("hypothetical_scenario", result)
    elif args.command == "capture-pbp":
        inventory = json.loads(args.inventory.read_text())
        if inventory["repository"] != "shufinskiy/nba_data" or inventory["truncated"]:
            raise ValueError("expected full shufinskiy inventory")
        result = {"manifest": str(download_inventory(inventory, select_shufinskiy(inventory, args.start, args.end), root / "raw/github"))}
        ledger.append("pbp_capture_manifest", result)
    elif args.command == "audit-pbp":
        manifest = json.loads(args.manifest.read_text())
        reports = []
        for entry in manifest["files"]:
            if "sha256" not in entry:
                continue
            path = args.manifest.parent / entry["name"]
            if digest(path) != entry["sha256"]:
                raise ValueError("raw integrity mismatch")
            if path.name.endswith(".tar.xz"):
                reports.append(audit_tar_csv(path))
        result = dict(source=manifest["source"], source_commit=manifest["commit"], files=reports,
                      completeness_verified=False)
        write_json(root / "reports/pbp_coverage.json", result)
        ledger.append("pbp_coverage", result)
    elif args.command == "audit-hoopr":
        result = audit_hoopr(args.manifest)
        write_json(root / "reports/hoopr_coverage.json", result)
        ledger.append("hoopr_coverage", result)
    elif args.command == "verify-ledger":
        result = ledger.verify()
    else:
        result = dict(data_dir=str(root), nba_telegram_active=False, paid_capture_active=False,
                      operational_test_delivery_implemented=True, pick_delivery_implemented=False, production_ready=False,
                      normalized_data_exists=(root / "normalized/player_games.jsonl.gz").exists(),
                      backtest_exists=(root / "reports/backtest.json").exists())
    print(json.dumps(result, indent=2, allow_nan=False))
