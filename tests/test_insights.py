from purrse.database import MonthSummary
from purrse.insights import generate_insights, mascot_mood


def summary(**changes):
    values = dict(
        month_id=1, year=2026, month=9, status="open", opening_bank=0, opening_debt=0,
        target_savings=100_000, income=300_000, expenses=100_000, borrowed=0, repayments=0,
        expected_bank=200_000, expected_debt=0, savings=200_000, actual_bank=None, actual_debt=None,
        bank_adjustment=0, debt_adjustment=0, note="",
    )
    values.update(changes)
    return MonthSummary(**values)


def test_target_insight_and_mascot_are_positive():
    current = summary()
    insights = generate_insights(current, None, [("Groceries", 70_000)])
    assert any("Target reached" in line for line in insights)
    assert mascot_mood(current)[0] == "celebrate"


def test_negative_savings_uses_non_shaming_copy():
    current = summary(savings=-50_000, income=50_000, expenses=100_000)
    insights = generate_insights(current, None, [])
    assert any("useful information" in line for line in insights)
