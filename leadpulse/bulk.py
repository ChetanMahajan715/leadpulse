"""Bulk CSV scoring: column validation, bad-row reporting, row cap, ranked results."""

import csv
import io
from dataclasses import dataclass

import pandas as pd

from leadpulse.models import FIELD_LABELS, SAMPLE_LEAD_FIELDS, LeadInput, ScoreResult
from leadpulse.scoring import score_lead

MAX_ROWS = 500


class BulkError(ValueError):
    """The file cannot be scored at all (empty, unreadable, missing columns)."""


@dataclass
class BulkResult:
    """Ranked table for display/download, the scored leads (for per-row AI explanations) and row problems."""

    table: pd.DataFrame
    results: list[tuple[LeadInput, ScoreResult]]
    errors: list[str]

    def to_csv(self) -> str:
        """Results as CSV text for download."""
        return self.table.to_csv(index=False)


def template_csv() -> str:
    """CSV template: the 11 column headers plus the sample lead as an example row."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(FIELD_LABELS.values())
    writer.writerow(SAMPLE_LEAD_FIELDS[field] for field in FIELD_LABELS)
    return out.getvalue()


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def score_csv(data: bytes) -> BulkResult:
    """Score every lead row in an uploaded CSV with the rule engine. Raises BulkError if unusable."""
    reader = csv.reader(io.StringIO(_decode(data)))
    try:
        header = next(reader, [])
        index = {name.strip().lower(): i for i, name in enumerate(header)}
        missing = [label for label in FIELD_LABELS.values() if label.lower() not in index]
        if not any(name.strip() for name in header) or missing:
            found = ", ".join(missing) if any(h.strip() for h in header) else "all"
            raise BulkError(f"Missing columns: {found}. Download the template to see the expected format.")

        results: list[tuple[LeadInput, ScoreResult]] = []
        errors: list[str] = []
        over_cap = 0
        for row in reader:
            if not row:
                continue
            if len(row) != len(header):
                errors.append(f"Line {reader.line_num}: wrong number of columns, skipped")
            elif not any(cell.strip() for cell in row):
                errors.append(f"Line {reader.line_num}: empty row, skipped")
            elif len(results) >= MAX_ROWS:
                over_cap += 1
            else:
                lead = LeadInput(**{field: row[index[label.lower()]] for field, label in FIELD_LABELS.items()})
                results.append((lead, score_lead(lead)))
    except csv.Error as exc:
        raise BulkError(f"Could not read the file as CSV ({exc}).") from exc

    if over_cap:
        errors.append(f"Only the first {MAX_ROWS} rows were scored ({over_cap} skipped)")
    if not results:
        raise BulkError("No valid lead rows found in the file.")

    results.sort(key=lambda pair: -pair[1].score)  # stable: ties keep file order
    table = pd.DataFrame([
        {
            "Rank": rank,
            "Name": lead.name,
            "Company": lead.company,
            "Score": r.score,
            "Class": r.classification,
            "Confidence": f"{r.confidence}% {r.confidence_label}",
            "Top flag": r.flags[0] if r.flags else "",
            "Next action": r.next_action,
        }
        for rank, (lead, r) in enumerate(results, start=1)
    ])
    return BulkResult(table=table, results=results, errors=errors)
