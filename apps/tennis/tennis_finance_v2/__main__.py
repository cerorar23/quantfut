"""Offline audit or strictly gated paper order; no credentials/network required."""
import argparse
import json
from pathlib import Path
from .audit import audit, read, write_new
from tennis_engine.paper_validation import digest, quote_receipt_from_archive, seal_paper_order


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("audit")
    check.add_argument("--config", type=Path, required=True)
    check.add_argument("--output", type=Path, required=True)
    seal = commands.add_parser("seal-paper")
    for name in ("config", "record", "quote-receipt"):
        seal.add_argument("--"+name, type=Path, required=True)
    seal.add_argument("--event-id", required=True)
    seal.add_argument("--selection", required=True)
    args = parser.parse_args()
    if args.command == "audit":
        report = audit(args.config)
        write_new(args.output, report)
        print(json.dumps(dict(status=report["status"], valid_orders=report["financial_report"]["valid_orders"],
                              blockers=report["blockers"], output=str(args.output.resolve())), ensure_ascii=False))
    else:
        config = read(args.config)
        if digest(config["policy_path"]) != config["policy_sha256"]:
            raise ValueError("Configured policy changed")
        target = seal_paper_order(Path(config["orders_root"]), args.record, args.event_id, args.selection,
                                  quote_receipt_from_archive(args.quote_receipt), Path(config["policy_path"]))
        print(json.dumps(dict(paper_order=str(target), real_money_approved=False)))


if __name__ == "__main__":
    main()
