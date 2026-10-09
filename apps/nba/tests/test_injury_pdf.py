import json

import httpx
import pytest

from nba.injury_pdf import capture_reports, records_from_cells, report_clock, select_report


@pytest.mark.parametrize("header,expected", [
    ("Injury Report: 04/25/25 05:30 PM", "2025-04-25T21:30:00+00:00"),
    ("Injury Report: 01/15/25 05:30 PM", "2025-01-15T22:30:00+00:00"),
])
def test_report_uses_header_and_eastern_dst(header, expected):
    assert report_clock(header) == expected


@pytest.mark.parametrize("header", ["Injury Report: 11/02/25 01:30 AM", "Injury Report: 03/09/25 02:30 AM", "05PM"])
def test_ambiguous_nonexistent_or_filename_clock_rejected(header):
    with pytest.raises(ValueError): report_clock(header)


def fixture():
    return [(1, [["04/25/2025", "07:00 (ET)", "BOS@ORL", "Boston Celtics", "Brown, Jaylen", "Questionable", "Injury/Illness - Knee"],
                 ["", "", "", "Orlando Magic", "Suggs, Jalen", "Out", "Injury/Illness - Knee"]]),
            (2, [["", "", "", "", "Wagner, Moritz", "Out", "Injury/Illness - Knee"],
                 ["04/26/2025", "03:30 (ET)", "OKC@MEM", "Memphis Grizzlies", "", "", "NOT YET SUBMITTED"]])]


def test_cross_page_context_and_unsubmitted_team_preserved():
    rows = records_from_cells(fixture())
    assert rows[2]["team"] == "Orlando Magic" and rows[2]["source_page"] == 2
    assert rows[3]["status_raw"] is None and not rows[3]["report_submitted"]
    assert all(not r["pregame_availability_verified"] and r["nba_player_id"] is None for r in rows)


@pytest.mark.parametrize("failure", ["unknown_status", "missing_context", "submitted_player", "duplicate"])
def test_pdf_rows_cannot_silently_invent_state(failure):
    pages = fixture()
    if failure == "unknown_status": pages[0][1][0][5] = "Healthy"
    elif failure == "missing_context": pages[0][1][0][3] = ""
    elif failure == "submitted_player": pages[1][1][1][4] = "Someone, Test"
    else: pages[1][1].insert(0, ["", "", "", "", "Suggs, Jalen", "Out", "Injury/Illness - Knee"])
    with pytest.raises(ValueError): records_from_cells(pages)


def test_retrospective_source_clock_never_counts_as_original_receipt():
    reports = [dict(report_timestamp_utc="2025-04-25T21:30:00+00:00", first_received_at_utc="2026-10-05T22:48:40+00:00"),
               dict(report_timestamp_utc="2025-04-25T22:30:00+00:00", first_received_at_utc="2026-10-05T22:49:40+00:00")]
    cutoff = "2025-04-25T22:00:00+00:00"
    assert select_report(reports, cutoff) is None
    assert select_report(reports, cutoff, retrospective=True) == reports[0]
    with pytest.raises(ValueError): select_report(reports, "2025-04-25T22:00:00")


def test_pdf_capture_stops_on_denial_preserves_raw_and_never_retries(tmp_path):
    urls = [f"https://ak-static.cms.nba.com/referee/injury/Injury-Report_2025-04-25_0{n}PM.pdf" for n in (5, 6)]
    calls = []
    def denied(request):
        calls.append(request)
        return httpx.Response(403, text="denied")
    t = httpx.MockTransport(denied)
    p = capture_reports(tmp_path, urls, transport=t)
    meta = json.loads(p.read_text())
    assert len(calls) == 1 and meta["status"] == "stopped_after_failure"
    assert (p.parent / meta["files"][0]["name"]).read_text() == "denied"
    capture_reports(tmp_path, urls, transport=t)
    assert len(calls) == 1


@pytest.mark.parametrize("url", ["https://example.com/report.pdf", "http://ak-static.cms.nba.com/referee/injury/Injury-Report_2025-04-25_05PM.pdf",
    "https://ak-static.cms.nba.com/referee/injury/Injury-Report_2025-04-25_05PM.pdf?token=secret"])
def test_only_canonical_public_report_urls_allowed(tmp_path, url):
    with pytest.raises(ValueError): capture_reports(tmp_path, [url])
