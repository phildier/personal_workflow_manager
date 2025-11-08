"""Business day calculation utilities for work summaries."""

from datetime import datetime, timedelta


def get_previous_business_day(current_time: datetime) -> datetime:
    """
    Calculate the start of the previous business day.

    Logic:
    - Monday → Friday 00:00
    - Tuesday-Friday → Previous day 00:00
    - Saturday → Friday 00:00
    - Sunday → Friday 00:00

    Args:
        current_time: The reference time (usually datetime.now())

    Returns:
        Start of the previous business day (00:00:00)

    Examples:
        >>> # Monday Jan 13, 2025 at noon
        >>> get_previous_business_day(datetime(2025, 1, 13, 12, 0))
        datetime(2025, 1, 10, 0, 0, 0)  # Friday

        >>> # Tuesday Jan 14, 2025 at noon
        >>> get_previous_business_day(datetime(2025, 1, 14, 12, 0))
        datetime(2025, 1, 13, 0, 0, 0)  # Monday
    """
    weekday = current_time.weekday()  # 0=Monday, 6=Sunday

    if weekday == 0:  # Monday
        days_back = 3  # Go back to Friday
    elif weekday == 5:  # Saturday
        days_back = 1  # Go back to Friday
    elif weekday == 6:  # Sunday
        days_back = 2  # Go back to Friday
    else:  # Tuesday-Friday (1-4)
        days_back = 1  # Go back one day

    previous_day = current_time - timedelta(days=days_back)
    return previous_day.replace(hour=0, minute=0, second=0, microsecond=0)


def format_date_range(start: datetime, end: datetime) -> str:
    """
    Format a date range for display.

    Args:
        start: Start datetime
        end: End datetime

    Returns:
        Formatted string like "Monday, Jan 13 2025 00:00 - Monday, Jan 13 2025 12:00"

    Examples:
        >>> start = datetime(2025, 1, 13, 0, 0)
        >>> end = datetime(2025, 1, 13, 12, 0)
        >>> format_date_range(start, end)
        'Monday, Jan 13 2025 00:00 - Monday, Jan 13 2025 12:00'
    """
    start_str = start.strftime("%A, %b %d %Y %H:%M")
    end_str = end.strftime("%A, %b %d %Y %H:%M")
    return f"{start_str} - {end_str}"
