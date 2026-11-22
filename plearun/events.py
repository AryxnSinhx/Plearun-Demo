"""From raw rows to (a) an incident-day context, (b) semantic events, (c) a de-duplicated camera index."""
import bisect
import re
from collections import Counter

from .loaders import strip_speaker
from .semantics import classify_text_ex, classify_dispatch_type, is_hedged, is_instruction_like
from .timeutil import wall_midnight

HEDGE_PAD = 60.0                          # a hedged time ("about 21:16") is widened by this much each side
AUTHORITY = {'dispatch': 0, 'camera': 1, 'notes': 2, 'bodycam': 3}   # who wins when several rows agree


class Context:
    """Two assumptions the whole run rests on, each inferred from the data and reported in the README:
    local_offset - the zone that zone-less times (notes "21:15", naive ISO text, the report) are written in.
                   Taken as the most common explicit UTC offset in the records.
    date_wall    - local midnight of the incident date (from the report header)."""

    def __init__(self, local_offset, date_wall):
        self.local_offset, self.date_wall = local_offset, date_wall

    def interval(self, stamp):
        """UTC (lo, hi) for a Stamp, or None when it cannot be placed on the clock."""
        if stamp is None:
            return None
        if stamp.kind == 'abs':
            if stamp.offset is None and self.local_offset is None:
                return None               # bare epoch with no zone evidence anywhere: do not guess
            lo = stamp.secs
        elif stamp.kind == 'naive':
            lo = stamp.secs - (self.local_offset or 0)
        else:
            if self.date_wall is None:
                return None
            lo = self.date_wall + stamp.secs - (self.local_offset or 0)
        return lo, lo + stamp.span

    def on_incident_day(self, lo):
        """Records from some other date must not act as evidence (stale or misleading rows)."""
        if self.date_wall is None:
            return True
        start = self.date_wall - (self.local_offset or 0)
        # the incident may run past midnight, but a row from the previous evening is another day's evidence
        return start - 3600 <= lo <= start + 30 * 3600


def infer_context(rows, report_date):
    # Each file votes once for its own most common explicit offset (a 1M-row camera export must not outvote
    # the dispatch export). Ties go to a non-zero offset: "Z" usually means a UTC export, while the report
    # and the notes are written in local time.
    per_file = {}
    for r in rows:
        if r.stamp is not None and r.stamp.kind == 'abs' and r.stamp.offset is not None:
            per_file.setdefault(r.file, Counter())[r.stamp.offset] += 1
    votes = Counter(c.most_common(1)[0][0] for c in per_file.values())
    local = max(votes, key=lambda o: (votes[o], o != 0)) if votes else None
    date_wall = None
    if report_date:
        date_wall = wall_midnight(*report_date)
    else:
        days = Counter()
        for r in rows:
            st = r.stamp
            if st is None:
                continue
            if st.kind == 'naive':
                days[int(st.secs // 86400)] += 1
            elif st.kind == 'abs' and (st.offset is not None or local is not None):
                days[int((st.secs + (st.offset if st.offset is not None else local)) // 86400)] += 1
        if days:
            date_wall = days.most_common(1)[0][0] * 86400.0
    return Context(local, date_wall)


class Event:
    __slots__ = ('kind', 'row', 'domain', 'source', 'lo', 'hi', 'hedged')

    def __init__(self, kind, row, lo, hi, hedged):
        self.kind, self.row, self.domain, self.source = kind, row, row.domain, row.file
        self.hedged = hedged
        pad = HEDGE_PAD if hedged else 0.0
        self.lo, self.hi = lo - pad, hi + pad


class Evidence:
    def __init__(self, rows, ctx):
        self.ctx = ctx
        self.by_kind = {}                 # event kind -> [Event]
        self.camera = []                  # [(lo, Row)] sorted by time, de-duplicated
        self.statements = []              # notes + bodycam rows usable as free-text evidence
        self.dispatch_rows = []
        seen = set()
        cam_seen = set()
        self.near_seen = set()
        self.quarantined = []             # rows whose text tries to instruct the tool
        for r in rows:
            if r.kind != 'camera' and is_instruction_like(r.text if r.kind == 'dispatch' else r.raw):
                self.quarantined.append(r)
                continue
            iv = ctx.interval(r.stamp)
            if iv is not None and not ctx.on_incident_day(iv[0]):
                continue
            if r.kind == 'camera':
                if iv is None:
                    continue
                key = (r.domain.split(':')[-1], iv[0], r.fields.get('speed'), r.fields.get('zone'))
                if key in cam_seen:
                    continue              # same reading written twice (even in two timestamp formats)
                cam_seen.add(key)
                self.camera.append((iv[0], r))
            elif r.kind == 'dispatch':
                self.dispatch_rows.append(r)
                kind = classify_dispatch_type(r.fields.get('type'))
                self._add(seen, kind, r, iv)
            elif r.kind in ('notes', 'bodycam'):
                self.statements.append(r)
                kind, strong = classify_text_ex(r.text)
                self._add(seen, kind if strong else None, r, iv)     # loose wording is not evidence
        self.camera.sort(key=lambda x: x[0])
        self._cam_times = [t for t, _ in self.camera]

    def _add(self, seen, kind, row, iv):
        if kind is None or iv is None:
            return
        key = (kind, row.domain, iv, row.text)
        if key in seen:
            return
        seen.add(key)
        # the same entry written twice a few seconds apart (same unit / same words) is one event
        who = (row.fields.get('type'), row.fields.get('unit')) if row.kind == 'dispatch' else row.text
        b = int(iv[0] // 5)
        if any((kind, row.domain, who, b + d) in self.near_seen for d in (-1, 0, 1)):
            return
        self.near_seen.add((kind, row.domain, who, b))
        self.by_kind.setdefault(kind, []).append(Event(kind, row, iv[0], iv[1], is_hedged(row.text)))

    def camera_between(self, lo, hi):
        i = bisect.bisect_left(self._cam_times, lo)
        j = bisect.bisect_right(self._cam_times, hi)
        return self.camera[i:j]
