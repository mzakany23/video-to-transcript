"""
Timestamp formatting utilities for transcription output
Converts seconds to human-readable timestamp formats
"""

from typing import Union


def format_timestamp(seconds: Union[float, int]) -> str:
    """
    Convert seconds to HH:MM:SS format

    Args:
        seconds: Time in seconds (can be float for decimal precision)

    Returns:
        Formatted timestamp string (HH:MM:SS or MM:SS for short durations)

    Examples:
        >>> format_timestamp(0)
        '00:00'
        >>> format_timestamp(65)
        '01:05'
        >>> format_timestamp(3661)
        '01:01:01'
        >>> format_timestamp(3661.5)
        '01:01:01'
        >>> format_timestamp(36000)
        '10:00:00'
    """
    if seconds < 0:
        seconds = 0

    # Round to nearest second for display
    total_seconds = int(round(seconds))

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    # For durations under 1 hour, use MM:SS format
    if hours == 0:
        return f"{minutes:02d}:{secs:02d}"

    # For durations 1 hour or more, use HH:MM:SS format
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_duration(seconds: Union[float, int]) -> str:
    """
    Convert seconds to human-readable duration with units

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string with appropriate units

    Examples:
        >>> format_duration(45)
        '45 seconds'
        >>> format_duration(90)
        '1.5 minutes'
        >>> format_duration(3661)
        '1.0 hours'
        >>> format_duration(7322)
        '2.0 hours'
    """
    if seconds < 0:
        seconds = 0

    # Less than 2 minutes: show seconds
    if seconds < 120:
        return f"{int(seconds)} seconds"

    # Less than 2 hours: show minutes
    if seconds < 7200:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"

    # 2 hours or more: show hours
    hours = seconds / 3600
    return f"{hours:.1f} hours"


def format_timestamp_range(start_seconds: Union[float, int],
                          end_seconds: Union[float, int]) -> str:
    """
    Format a time range with consistent formatting

    Args:
        start_seconds: Start time in seconds
        end_seconds: End time in seconds

    Returns:
        Formatted range string (e.g., "[00:00 - 05:30]")

    Examples:
        >>> format_timestamp_range(0, 330)
        '[00:00 - 05:30]'
        >>> format_timestamp_range(330, 945)
        '[05:30 - 15:45]'
        >>> format_timestamp_range(3600, 7200)
        '[01:00:00 - 02:00:00]'
    """
    start = format_timestamp(start_seconds)
    end = format_timestamp(end_seconds)

    # Ensure both timestamps have same format (both with or without hours)
    # If end time has hours, start time should too
    if ':' in end:
        end_parts = end.count(':')
        start_parts = start.count(':')

        if end_parts > start_parts:
            # Pad start with hours if needed
            start = f"00:{start}"

    return f"[{start} - {end}]"


def seconds_to_hhmmss(seconds: Union[float, int]) -> str:
    """
    Alias for format_timestamp for backward compatibility

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    return format_timestamp(seconds)
