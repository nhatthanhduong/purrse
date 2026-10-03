from __future__ import annotations

from .database import MonthSummary
from .money import format_k


def generate_insights(current: MonthSummary, previous: MonthSummary | None, top_categories: list[tuple[str, int]]) -> list[str]:
    lines: list[str] = []
    if current.income == 0 and current.expenses == 0:
        return ["This month is ready for its first entry. Miso is standing by!"]

    if current.savings < 0:
        lines.append(f"Spending was {format_k(abs(current.savings))} above income; this is useful information for planning next month.")
    elif current.savings >= current.target_savings and current.target_savings > 0:
        lines.append(f"Target reached — you saved {format_k(current.savings)}, meeting the {format_k(current.target_savings)} goal.")
    elif current.target_savings > 0:
        gap = current.target_savings - current.savings
        lines.append(f"You are {format_k(max(0, gap))} away from this month’s savings target.")
    elif current.savings >= 0:
        lines.append(f"Income was ahead of spending by {format_k(current.savings)} this month.")

    if top_categories:
        category, amount = top_categories[0]
        lines.append(f"The largest spending category was {category} at {format_k(amount)}.")

    if previous and previous.expenses:
        change = current.expenses - previous.expenses
        percent = abs(change) * 100 / previous.expenses
        direction = "higher" if change > 0 else "lower"
        if change:
            lines.append(f"Spending was {percent:.0f}% {direction} than last month.")

    debt_change = (current.actual_debt if current.actual_debt is not None else current.expected_debt) - current.opening_debt
    if debt_change < 0:
        lines.append(f"Debt decreased by {format_k(abs(debt_change))}. Nice progress!")
    elif debt_change > 0:
        lines.append(f"Debt increased by {format_k(debt_change)}; Miso has highlighted it for next month’s plan.")

    if current.bank_adjustment:
        lines.append(f"The confirmed bank balance included a reconciliation adjustment of {format_k(current.bank_adjustment)}.")
    if current.debt_adjustment:
        lines.append(f"The confirmed debt included a reconciliation adjustment of {format_k(current.debt_adjustment)}.")
    return lines


def mascot_mood(summary: MonthSummary) -> tuple[str, str]:
    if summary.income == 0 and summary.expenses == 0:
        return "curious", "Ready when you are!"
    if summary.target_savings > 0 and summary.savings >= summary.target_savings:
        return "celebrate", "Pawsome! Target reached!"
    if summary.savings >= 0:
        return "happy", "Looking tidy this month."
    return "gentle", "No judgment—just useful clues."
