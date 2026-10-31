from leadpulse.confidence import compute_confidence


def test_full_data_no_issues_is_100_high():
    assert compute_confidence([], unrecognised=0, flags=0) == (100, "High")


def test_two_flags_cost_ten():
    assert compute_confidence([], unrecognised=0, flags=2) == (90, "High")


def test_critical_field_costs_twenty_other_costs_eight():
    assert compute_confidence(["job_title"], 0, 0) == (80, "High")
    assert compute_confidence(["industry"], 0, 0) == (92, "High")


def test_both_email_and_phone_missing_counts_once_as_critical():
    assert compute_confidence(["email", "phone"], 0, 0) == (80, "High")
    assert compute_confidence(["email"], 0, 0) == (92, "High")


def test_labels_and_clamp():
    assert compute_confidence(["job_title", "requirement"], 0, 0) == (60, "Medium")
    assert compute_confidence(["job_title", "requirement", "company_size"], 0, 0) == (40, "Low")
    assert compute_confidence(["job_title", "requirement", "company_size"], 10, 10) == (0, "Low")
