import calendar
from datetime import date, datetime


def universal_date_format(date: date | datetime) -> str:
    return f"{date:%Y-%m-%d}"


def human_daterange(
    date_left: date | datetime | None,
    date_right: date | datetime | None,
    no_date_left: str = "???",
    no_date_right: str = "???",
    separator: str = " - ",
    common_month_left: str = "%b %d",
    common_month_right: str = "%d, %Y",
    common_year_left: str = "%b %d",
    common_year_right: str = "%b %d, %Y",
    nothing_common_left: str = "%b %d, %Y",
    nothing_common_right: str = "%b %d, %Y",
) -> str:
    if not date_left and not date_right:
        return f"{no_date_left}{separator}{no_date_right}"

    if date_left and not date_right:
        return f"{date_left:{nothing_common_left}}{separator}{no_date_right}"

    elif date_right and not date_left:
        return f"{no_date_left}{separator}{date_right:{nothing_common_right}}"

    common_year = date_left.year == date_right.year  # type: ignore
    common_month = date_left.month == date_right.month  # type: ignore

    if common_year and common_month:
        return f"{date_left:{common_month_left}}{separator}{date_right:{common_month_right}}"

    elif common_year:
        return f"{date_left:{common_year_left}}{separator}{date_right:{common_year_right}}"

    else:
        return f"{date_left:{nothing_common_left}}{separator}{date_right:{nothing_common_right}}"


def rollover_end_date(previous_end: date) -> date:
    """Calculate end date of a rolled-over agreement (membership or partnership): one year after
    the previous agreement's end.

    If the previous agreement ended on the last day of a month, the new one ends on the last day
    of the same month a year later. This correctly handles leap years, e.g.:
    * 2024-02-29 -> 2025-02-28 (new agreement 2024-03-01 - 2025-02-28),
    * 2023-02-28 -> 2024-02-29 (new agreement 2023-03-01 - 2024-02-29).
    """
    year = previous_end.year + 1
    last_day_previous = calendar.monthrange(previous_end.year, previous_end.month)[1]
    last_day_new = calendar.monthrange(year, previous_end.month)[1]
    if previous_end.day == last_day_previous:
        return date(year, previous_end.month, last_day_new)
    return date(year, previous_end.month, min(previous_end.day, last_day_new))
