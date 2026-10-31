from pathlib import Path

import pytest

from leadpulse.bulk import MAX_ROWS, BulkError, score_csv, template_csv
from leadpulse.models import FIELD_LABELS

HEADER = ",".join(FIELD_LABELS.values())
SAMPLE_ROW = ("Rahul Sharma,ABC Technologies,www.abctechnologies.com,Founder,IT Services,Bangalore,"
              "50-100 Employees,Website,Looking for CRM software,rahul@example.com,+91 9876543210")
COLD_ROW = "Amit,Small Shop,smallshop.in,Intern,Agriculture,Patna,5,Cold outreach,just browsing,amit@gmail.com,9876501234"


def test_valid_csv_is_scored_and_ranked_hot_first():
    out = score_csv(f"{HEADER}\n{COLD_ROW}\n{SAMPLE_ROW}\n".encode())
    assert list(out.table["Name"]) == ["Rahul Sharma", "Amit"]
    assert list(out.table["Score"]) == [84, 29]
    assert list(out.table["Class"]) == ["Hot", "Cold"]
    assert out.table.loc[0, "Top flag"] == "Placeholder or disposable email domain"
    assert out.errors == []
    assert "Score" in out.to_csv().splitlines()[0]


def test_columns_are_matched_case_insensitively_and_extra_columns_ignored():
    header = HEADER.lower().replace("name,", " NAME ,", 1) + ",Notes"
    out = score_csv(f"{header}\n{SAMPLE_ROW},ignore me\n".encode())
    assert list(out.table["Score"]) == [84]


def test_missing_columns_raise_a_friendly_error():
    with pytest.raises(BulkError, match="Missing columns: Email, Phone"):
        score_csv(b"Name,Company Name,Website,Job Title,Industry,Company Location,Company Size,"
                  b"Lead Source,Requirement\nA,B,c.com,CEO,IT,Pune,10,Website,crm\n")


def test_bad_rows_are_skipped_and_reported():
    bad_wide = SAMPLE_ROW + ",extra,cells"
    empty = "," * 10
    out = score_csv(f"{HEADER}\n{SAMPLE_ROW}\n{bad_wide}\n{empty}\n{COLD_ROW}\n".encode())
    assert len(out.table) == 2
    assert out.errors == ["Line 3: wrong number of columns, skipped", "Line 4: empty row, skipped"]


def test_row_cap():
    rows = "\n".join([SAMPLE_ROW] * (MAX_ROWS + 5))
    out = score_csv(f"{HEADER}\n{rows}\n".encode())
    assert len(out.table) == MAX_ROWS
    assert out.errors == [f"Only the first {MAX_ROWS} rows were scored (5 skipped)"]


def test_empty_or_garbage_file():
    with pytest.raises(BulkError):
        score_csv(b"")
    with pytest.raises(BulkError):
        score_csv(b"\x00\x01binary")


def test_template_and_sample_files_score_cleanly():
    assert template_csv().splitlines()[0] == HEADER
    sample = Path("data/sample_leads.csv").read_bytes()
    out = score_csv(sample)
    assert len(out.table) >= 8 and out.errors == []
    assert {"Hot", "Warm", "Cold"} <= set(out.table["Class"])
