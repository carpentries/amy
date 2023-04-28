from datetime import date, datetime
from typing import Optional, Union


def universal_date_format(date: Union[date, datetime]) -> str:
    return "{:%Y-%m-%d}".format(date)


def human_daterange(
    date_left: Optional[Union[date, datetime]],
    date_right: Optional[Union[date, datetime]],
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
        return (
            f"{date_left:{common_month_left}}"
            f"{separator}"
            f"{date_right:{common_month_right}}"
        )

    elif common_year:
        return (
            f"{date_left:{common_year_left}}"
            f"{separator}"
            f"{date_right:{common_year_right}}"
        )

    else:
        return (
            f"{date_left:{nothing_common_left}}"
            f"{separator}"
            f"{date_right:{nothing_common_right}}"
        )
