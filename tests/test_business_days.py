"""Tests for business day calculation utilities."""

from datetime import datetime

import pytest

from pwm.summary.business_days import get_previous_business_day, format_date_range


class TestGetPreviousBusinessDay:
    """Tests for get_previous_business_day function."""

    def test_monday_gets_friday(self):
        """Monday should return Friday 00:00."""
        monday = datetime(2025, 1, 13, 12, 0)  # Monday Jan 13, 2025 at noon
        result = get_previous_business_day(monday)

        assert result.weekday() == 4  # Friday
        assert result.day == 10
        assert result.month == 1
        assert result.year == 2025
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0

    def test_tuesday_gets_monday(self):
        """Tuesday should return Monday 00:00."""
        tuesday = datetime(2025, 1, 14, 12, 0)  # Tuesday Jan 14, 2025
        result = get_previous_business_day(tuesday)

        assert result.weekday() == 0  # Monday
        assert result.day == 13
        assert result.month == 1
        assert result.year == 2025
        assert result.hour == 0

    def test_wednesday_gets_tuesday(self):
        """Wednesday should return Tuesday 00:00."""
        wednesday = datetime(2025, 1, 15, 12, 0)  # Wednesday Jan 15, 2025
        result = get_previous_business_day(wednesday)

        assert result.weekday() == 1  # Tuesday
        assert result.day == 14
        assert result.hour == 0

    def test_thursday_gets_wednesday(self):
        """Thursday should return Wednesday 00:00."""
        thursday = datetime(2025, 1, 16, 12, 0)  # Thursday Jan 16, 2025
        result = get_previous_business_day(thursday)

        assert result.weekday() == 2  # Wednesday
        assert result.day == 15
        assert result.hour == 0

    def test_friday_gets_thursday(self):
        """Friday should return Thursday 00:00."""
        friday = datetime(2025, 1, 17, 12, 0)  # Friday Jan 17, 2025
        result = get_previous_business_day(friday)

        assert result.weekday() == 3  # Thursday
        assert result.day == 16
        assert result.hour == 0

    def test_saturday_gets_friday(self):
        """Saturday should return Friday 00:00."""
        saturday = datetime(2025, 1, 11, 12, 0)  # Saturday Jan 11, 2025
        result = get_previous_business_day(saturday)

        assert result.weekday() == 4  # Friday
        assert result.day == 10
        assert result.hour == 0

    def test_sunday_gets_friday(self):
        """Sunday should return Friday 00:00."""
        sunday = datetime(2025, 1, 12, 12, 0)  # Sunday Jan 12, 2025
        result = get_previous_business_day(sunday)

        assert result.weekday() == 4  # Friday
        assert result.day == 10
        assert result.hour == 0

    def test_preserves_timezone_info(self):
        """Should preserve timezone information if present."""
        # Note: This test assumes datetime with tzinfo, but the implementation
        # uses replace() which should preserve tzinfo
        from datetime import timezone
        monday = datetime(2025, 1, 13, 12, 0, tzinfo=timezone.utc)
        result = get_previous_business_day(monday)

        assert result.tzinfo == timezone.utc

    def test_early_morning_monday(self):
        """Monday at 1am should still return Friday 00:00."""
        monday_early = datetime(2025, 1, 13, 1, 0)
        result = get_previous_business_day(monday_early)

        assert result.weekday() == 4  # Friday
        assert result.day == 10
        assert result.hour == 0

    def test_late_night_friday(self):
        """Friday at 11pm should return Thursday 00:00."""
        friday_late = datetime(2025, 1, 17, 23, 30)
        result = get_previous_business_day(friday_late)

        assert result.weekday() == 3  # Thursday
        assert result.day == 16
        assert result.hour == 0

    def test_month_boundary(self):
        """Should handle month boundaries correctly (Monday Feb 3 -> Friday Jan 31)."""
        monday = datetime(2025, 2, 3, 12, 0)  # Monday Feb 3, 2025
        result = get_previous_business_day(monday)

        assert result.weekday() == 4  # Friday
        assert result.day == 31
        assert result.month == 1  # January
        assert result.year == 2025

    def test_year_boundary(self):
        """Should handle year boundaries correctly (Monday Jan 5, 2026 -> Friday Jan 2, 2026)."""
        monday = datetime(2026, 1, 5, 12, 0)  # Monday Jan 5, 2026
        result = get_previous_business_day(monday)

        assert result.weekday() == 4  # Friday
        assert result.day == 2
        assert result.month == 1
        assert result.year == 2026


class TestFormatDateRange:
    """Tests for format_date_range function."""

    def test_same_day_range(self):
        """Format range within same day."""
        start = datetime(2025, 1, 13, 9, 0)
        end = datetime(2025, 1, 13, 17, 0)
        result = format_date_range(start, end)

        assert "Monday, Jan 13 2025 09:00" in result
        assert "Monday, Jan 13 2025 17:00" in result
        assert " - " in result

    def test_different_days(self):
        """Format range across different days."""
        start = datetime(2025, 1, 10, 0, 0)
        end = datetime(2025, 1, 13, 12, 0)
        result = format_date_range(start, end)

        assert "Friday, Jan 10 2025 00:00" in result
        assert "Monday, Jan 13 2025 12:00" in result

    def test_format_includes_all_components(self):
        """Ensure format includes day name, month, date, year, time."""
        start = datetime(2025, 12, 25, 14, 30)
        end = datetime(2025, 12, 26, 10, 15)
        result = format_date_range(start, end)

        # Check for day name
        assert "Thursday" in result or "Friday" in result
        # Check for month
        assert "Dec" in result
        # Check for year
        assert "2025" in result
        # Check for time format
        assert "14:30" in result
        assert "10:15" in result

    def test_midnight_formatting(self):
        """Test formatting of midnight time."""
        start = datetime(2025, 1, 13, 0, 0)
        end = datetime(2025, 1, 13, 12, 0)
        result = format_date_range(start, end)

        assert "00:00" in result
        assert "12:00" in result
