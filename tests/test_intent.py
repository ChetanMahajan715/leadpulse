from leadpulse.intent import score_intent


def test_specific_solution_scores_base_plus_solution():
    points, reason = score_intent("looking for crm software")
    assert points == 15
    assert "crm" in reason


def test_urgency_budget_and_action_add_up():
    # base 5 + solution 10 + urgency 5 + budget 3 + action 2 = 25
    points, _ = score_intent("need crm urgently, budget approved, please share a demo")
    assert points == 25


def test_intent_is_capped_at_25():
    text = "urgent crm erp automation asap budget ₹10 lakh demo quote trial proposal call"
    points, _ = score_intent(text)
    assert points == 25


def test_short_text_without_keywords_scores_3():
    points, reason = score_intent("hello there")
    assert points == 3
    assert "vague" in reason.lower()


def test_long_text_without_keywords_gets_base_only():
    points, _ = score_intent("we would like to know more about your company")
    assert points == 5
