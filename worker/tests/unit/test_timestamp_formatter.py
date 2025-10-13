"""
Tests for timestamp formatting utilities
"""

import sys
from pathlib import Path
import pytest

# Add src to path (go up from tests/unit/ to worker/, then into src/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from transcripts.utils.timestamp_formatter import (
    format_timestamp,
    format_duration,
    format_timestamp_range
)


class TestFormatTimestamp:
    """Tests for format_timestamp function"""

    def test_zero_seconds(self):
        """Test formatting 0 seconds"""
        assert format_timestamp(0) == "00:00"

    def test_under_one_minute(self):
        """Test formatting seconds under 1 minute"""
        assert format_timestamp(45) == "00:45"
        assert format_timestamp(30.5) == "00:30"  # Python rounds .5 to nearest even (30)

    def test_one_to_60_minutes(self):
        """Test formatting 1-60 minutes"""
        assert format_timestamp(65) == "01:05"
        assert format_timestamp(600) == "10:00"
        assert format_timestamp(3599) == "59:59"

    def test_one_hour_plus(self):
        """Test formatting 1+ hours"""
        assert format_timestamp(3600) == "01:00:00"
        assert format_timestamp(3661) == "01:01:01"
        assert format_timestamp(7322) == "02:02:02"

    def test_ten_hours_plus(self):
        """Test formatting 10+ hours"""
        assert format_timestamp(36000) == "10:00:00"
        assert format_timestamp(43200) == "12:00:00"

    def test_negative_defaults_to_zero(self):
        """Test that negative values default to 0"""
        assert format_timestamp(-10) == "00:00"

    def test_float_rounding(self):
        """Test that float values are rounded correctly"""
        assert format_timestamp(65.4) == "01:05"
        assert format_timestamp(65.6) == "01:06"


class TestFormatDuration:
    """Tests for format_duration function"""

    def test_under_two_minutes(self):
        """Test formatting under 2 minutes shows seconds"""
        assert format_duration(45) == "45 seconds"
        assert format_duration(90) == "90 seconds"
        assert format_duration(119) == "119 seconds"

    def test_two_to_120_minutes(self):
        """Test formatting 2-120 minutes shows minutes"""
        assert format_duration(120) == "2.0 minutes"
        assert format_duration(1800) == "30.0 minutes"
        assert format_duration(3600) == "60.0 minutes"

    def test_over_two_hours(self):
        """Test formatting over 2 hours shows hours"""
        assert format_duration(7200) == "2.0 hours"
        assert format_duration(10800) == "3.0 hours"
        assert format_duration(36000) == "10.0 hours"

    def test_negative_defaults_to_zero(self):
        """Test that negative values default to 0 seconds"""
        assert format_duration(-10) == "0 seconds"


class TestFormatTimestampRange:
    """Tests for format_timestamp_range function"""

    def test_both_under_one_hour(self):
        """Test range where both times are under 1 hour"""
        assert format_timestamp_range(0, 330) == "[00:00 - 05:30]"
        assert format_timestamp_range(330, 945) == "[05:30 - 15:45]"
        assert format_timestamp_range(1800, 3599) == "[30:00 - 59:59]"

    def test_both_over_one_hour(self):
        """Test range where both times are over 1 hour"""
        assert format_timestamp_range(3600, 7200) == "[01:00:00 - 02:00:00]"
        assert format_timestamp_range(3661, 7322) == "[01:01:01 - 02:02:02]"

    def test_mixed_under_and_over_one_hour(self):
        """Test range where start < 1hr but end > 1hr"""
        # Should pad start with hours to match end format
        assert format_timestamp_range(0, 3600) == "[00:00:00 - 01:00:00]"
        assert format_timestamp_range(1800, 5400) == "[00:30:00 - 01:30:00]"

    def test_zero_duration(self):
        """Test range with zero duration"""
        assert format_timestamp_range(0, 0) == "[00:00 - 00:00]"
        assert format_timestamp_range(3600, 3600) == "[01:00:00 - 01:00:00]"

    def test_very_long_duration(self):
        """Test range with very long durations"""
        # 10 hours
        assert format_timestamp_range(0, 36000) == "[00:00:00 - 10:00:00]"
        # 24 hours
        assert format_timestamp_range(0, 86400) == "[00:00:00 - 24:00:00]"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
