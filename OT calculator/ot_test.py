# ot_utils.py
# Utility functions for OT and TA calculation

def calculate_rounded_ot(ot_minutes, period, grace_first, grace_other):
    """
    Calculate rounded OT based on grace thresholds and rounding period.

    Logic:
    - If OT minutes < grace_first → return 0
    - Otherwise:
        - Compute number of full periods (floor division)
        - Compare the remainder to grace_other
            - If remainder <= grace_other → round down
            - Else → round up
    Returns total rounded OT in minutes.
    """
    if ot_minutes < grace_first:
        return 0

    full_periods = ot_minutes // period
    remainder = ot_minutes % period

    if remainder <= grace_other:
        return full_periods * period
    else:
        return (full_periods + 1) * period

from datetime import datetime, timedelta

def parse_time_input(value):
    """
    Parse various formats into a datetime object.
    Supports:
    - "6:30"
    - "2025.06.14 06:30:00"
    - Excel float time (e.g. 0.270833 or 45822.27083)
    - "6/14/2025 6:30:00 AM"
    """
    if isinstance(value, (float, int)):
        # Excel float (days since 1899-12-30)
        excel_base = datetime(1899, 12, 30)
        return excel_base + timedelta(days=float(value))

    value_str = str(value).strip()

    known_formats = [
        "%H:%M",
        "%Y.%m.%d %H:%M:%S",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %H:%M:%S",
    ]

    for fmt in known_formats:
        try:
            return datetime.strptime(value_str, fmt)
        except ValueError:
            continue

    # Fallback: try HH:MM style manually
    try:
        parts = [int(p) for p in value_str.replace(":", " ").split()]
        if len(parts) == 2:
            return datetime.combine(datetime.today(), datetime.min.time()) + timedelta(hours=parts[0], minutes=parts[1])
    except:
        pass

    raise ValueError(f"Unsupported time format: {value}")

def get_ot_minutes(start, end, working_hours):
    """
    Compute OT minutes from start/end time and official working hours.
    Handles multiple time formats and overnight shifts.
    """
    start_dt = parse_time_input(start)
    end_dt = parse_time_input(end)

    if end_dt < start_dt:
        end_dt += timedelta(days=1)

    worked_minutes = (end_dt - start_dt).total_seconds() / 60
    return max(0, worked_minutes - working_hours * 60)
