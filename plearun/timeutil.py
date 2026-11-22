"""Turn the timestamp formats seen in records into a small, explicit Stamp.

Three kinds, because they need different handling later:
  abs    - an absolute instant (epoch number, or ISO text carrying a UTC offset)
  naive  - a date + time with no zone information
  tod    - a time of day only (no date), e.g. "21:15" in the notes file
"""
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class Stamp:
    kind: str                  # 'abs' | 'naive' | 'tod'
    secs: float                # abs: UTC epoch | naive: wall clock read as if UTC | tod: seconds since midnight
    span: float = 0.0          # writer's precision: 59 for "HH:MM" (the minute could be anywhere in it), else 0
    offset: Optional[int] = None   # explicit UTC offset in seconds east, when the text carried one


_ISO = re.compile(
    r'^\s*(\d{4})-(\d{2})-(\d{2})[T ](\d{1,2}):(\d{2})(?::(\d{2})(?:[.,](\d+))?)?'
    r'\s*(Z|z|[+-]\d{2}(?::?\d{2})?)?\s*$')
_TOD = re.compile(r'^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$')
_NUM = re.compile(r'^\s*\d+(?:\.\d+)?\s*$')


def _offset(text):
    if text in ('Z', 'z'):
        return 0
    sign = -1 if text[0] == '-' else 1
    digits = text[1:].replace(':', '')
    hours = int(digits[:2])
    minutes = int(digits[2:4]) if len(digits) >= 4 else 0
    return sign * (hours * 3600 + minutes * 60)


def _epoch(x):
    """Epoch seconds, milliseconds, microseconds or nanoseconds -> abs Stamp (sane years only)."""
    for scale in (1, 1e3, 1e6, 1e9):
        sec = x / scale
        if 946684800 <= sec <= 4102444800:   # years 2000..2100
            return Stamp('abs', sec)
    return None


def parse_stamp(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return _epoch(float(value))
    if not isinstance(value, str):
        return None
    if _NUM.match(value):
        return _epoch(float(value))
    m = _ISO.match(value)
    if m:
        y, mo, d, h, mi, s, frac, tz = m.groups()
        try:
            wall = datetime(int(y), int(mo), int(d), int(h), int(mi), min(int(s or 0), 59),
                            tzinfo=timezone.utc).timestamp()
        except ValueError:
            return None
        if frac:
            wall += float('0.' + frac)
        span = 59.0 if s is None else 0.0
        if tz:
            off = _offset(tz)
            return Stamp('abs', wall - off, span, off)
        return Stamp('naive', wall, span)
    m = _TOD.match(value)
    if m:
        h, mi, s = int(m.group(1)), int(m.group(2)), m.group(3)
        if h > 23 or mi > 59 or (s is not None and int(s) > 59):
            return None
        return Stamp('tod', h * 3600 + mi * 60 + int(s or 0), 59.0 if s is None else 0.0)
    return None


def wall_midnight(year, month, day):
    """Wall-clock midnight of a date, expressed as if it were UTC."""
    return datetime(year, month, day, tzinfo=timezone.utc).timestamp()
