"""Decide match / conflict / not_settled / not_checkable for one claim.

The asymmetry that drives every rule below:
  MATCH needs agreement under the tightest reading of the evidence.
  CONFLICT needs disagreement under the loosest reading (clock skew, rounding, hedging all allowed for),
  from a source that is about the same thing the claim is about.
  Anything in between is not_settled.
"""
import re

from .clocks import MIN_SKEW
from .events import AUTHORITY
from .loaders import json_fragment
from .timeutil import Stamp

TOL_PLAIN, TOL_HEDGED = 60.0, 120.0       # slack for "21:11" vs "about 21:14"
MIN_CONFLICT_MARGIN = 120.0               # a conflict must be this far outside tolerance + skew
CAMERA_ATTR = re.compile(r'\b(?:camera|cam-?\d+|radar|speed sensor|sensor)\b', re.I)
_SPEEDS = [re.compile(r'(\d{2,3}(?:\.\d+)?)\s*(?:mph|miles per hour)\b', re.I),
           re.compile(r'(\d{2,3})\s+in\s+an?\s+\d{2,3}\b', re.I)]
_ZONES = [re.compile(r'\d{2,3}\s+in\s+an?\s+(\d{2,3})\b', re.I),
          re.compile(r'(\d{2,3})\s*(?:mph)?\s*(?:zone|speed limit)\b', re.I),
          re.compile(r'speed limit\s+(?:of|is|was)\s+(\d{2,3})', re.I),
          re.compile(r'posted\s+(\d{2,3})\b', re.I)]


class Verdict:
    def __init__(self, finding, row=None, needle=None):
        self.finding, self.row, self.needle = finding, row, needle


# Numbers written next to "limit", "zone" or "posted" are limits, not speeds ("The limit here is 45 mph").
_LIMIT_CTX = re.compile(r'(?:speed\s+limit|limit|zone|posted)\b[^.;,]{0,25}?\d{2,3}(?:\s*mph)?'
                        r'|\d{2,3}\s*(?:mph\s*)?(?:speed\s+limit|limit|zone)\b|posted\s+\d{2,3}', re.I)
MAX_SPEED = 200.0
OFFICER_TITLE = re.compile(r'\b(?:officer|ofc|sgt|sergeant|deputy|det|detective|trooper|cpl|lt)\b', re.I)


def sane_speed(v):
    return v is not None and 0 < v <= MAX_SPEED


def sane_zone(v):
    return v is not None and 5 <= v <= 100 and v % 5 == 0


def speed_numbers(text):
    """Speeds a statement gives. The second number of "58 in a 45" is the limit; any number tied to the
    words limit / zone / posted is a limit; values outside 0..200 are sensor or typing noise."""
    text = text or ''
    out = {float(m.group(1)) for m in _SPEEDS[1].finditer(text)}
    cleaned = _LIMIT_CTX.sub(' ', text)
    out.update(float(m.group(1)) for m in _SPEEDS[0].finditer(cleaned))
    return {v for v in out if sane_speed(v)}


def zone_numbers(text):
    out = set()
    for p in _ZONES:
        out.update(float(m.group(1)) for m in p.finditer(text or ''))
    return {v for v in out if sane_zone(v)}


def _last_name(row):
    who = (row.fields.get('speaker') or row.fields.get('author') or '').split()
    return who[-1] if who else ''


def make_quote(row, needle=None):
    """The text a finding quotes. It is always a slice of row.raw; pipeline.finalize re-checks that."""
    if row.kind == 'dispatch':
        return json_fragment(row, row.fields.get('time_key') or '')
    if row.kind == 'bodycam':
        lines = row.fields.get('payload') or []
        if needle:
            for ln in lines:
                if needle.lower() in ln.lower():
                    return ln
        return lines[0] if lines else None
    return row.raw.strip()


class Judge:
    def __init__(self, ev, clocks, ctx):
        self.ev, self.clocks, self.ctx = ev, clocks, ctx

    def evaluate(self, claim):
        fn = {'time': self._time, 'speed': self._speed, 'zone': self._zone,
              'relative': self._relative, 'count': self._count}.get(claim.kind)
        if fn is None:
            return Verdict('not_checkable')
        return fn(claim)

    # ------------------------------------------------------------ helpers
    def _window(self, t):
        """Claimed time (dict with secs/span/hedged) -> (lo, hi, tolerance) in UTC, or None."""
        if not t:
            return None
        iv = self.ctx.interval(Stamp('tod', t['secs'], t['span']))
        if iv is None:
            return None
        return iv[0], iv[1], (TOL_HEDGED if t['hedged'] else TOL_PLAIN)

    @staticmethod
    def _actor_ok(e, p):
        """Compare like with like: an officer's first observation is evidenced by that officer's records only
        (a witness who 'saw a sedan' says nothing about it). Other event kinds are not actor-specific."""
        if p['event'] != 'observed':
            return True
        who = e.row.fields.get('speaker') or e.row.fields.get('author') or ''
        named = p.get('named')
        if named:
            parts = who.split()
            return bool(parts) and parts[-1].lower() == named.lower()
        return bool(OFFICER_TITLE.search(who))

    # ------------------------------------------------------------ time of an event
    def _time(self, claim):
        p = claim.params
        if p['event'] is None:
            return Verdict('not_checkable')
        win = self._window(p)
        events = [e for e in self.ev.by_kind.get(p['event'], []) if self._actor_ok(e, p)]
        if win is None or not events:
            return Verdict('not_settled')
        clo, chi, tol = win
        # A time of day near midnight may belong to the neighbouring date: try the shifted day too, and
        # call a record "far" only if it is far under every reading.
        shifts = [0.0]
        if p['secs'] < 6 * 3600:
            shifts.append(86400.0)
        if p['secs'] >= 18 * 3600:
            shifts.append(-86400.0)
        scored = []
        for e in events:
            lo, hi, aligned = self.clocks.adjust(e)
            skew = self.clocks.skew_for(aligned)
            gap = wide = float('inf')
            for sh in shifts:
                a, b = clo + sh, chi + sh
                gap = min(gap, max(a - tol - hi, lo - (b + tol), 0.0))
                wide = min(wide, max(a - tol - skew - hi, lo - (b + tol + skew), 0.0))
            # A whole-hour gap is what a timezone or UTC-vs-local mix-up looks like: never a conflict.
            d = abs((lo + hi) / 2 - (clo + chi) / 2)
            slack = tol + skew + MIN_CONFLICT_MARGIN
            zone_like = any(abs(d - 3600.0 * k) <= slack for k in range(1, 15))
            scored.append((e, gap, wide, zone_like))
        per_source = {}
        for e, _, _, _ in scored:
            per_source[e.source] = per_source.get(e.source, 0) + 1
        matches = [x for x in scored if x[1] == 0.0]
        far = [x for x in scored if x[2] >= MIN_CONFLICT_MARGIN]
        if matches:
            if any(per_source[x[0].source] == 1 for x in far):
                return Verdict('not_settled')          # a source that only has one such event disagrees
            best = min(matches, key=lambda x: (AUTHORITY.get(x[0].row.kind, 9),
                                               abs((x[0].lo + x[0].hi) / 2 - (clo + chi) / 2)))
            return Verdict('match', best[0].row, None)
        if far and len(far) == len(scored) and all(n == 1 for n in per_source.values()) \
                and not any(x[3] for x in far):
            best = min(far, key=lambda x: AUTHORITY.get(x[0].row.kind, 9))
            return Verdict('conflict', best[0].row, None)
        return Verdict('not_settled')

    # ------------------------------------------------------------ speed
    def _speed(self, claim):
        p = claim.params
        speed = p['speed']
        stmts = [(r, speed_numbers(r.text)) for r in self.ev.statements]
        stmts = [(r, s) for r, s in stmts if s]
        support = [r for r, s in stmts if speed in s]
        against = [(r, s) for r, s in stmts if speed not in s]
        win = self._window(p['ctx'])
        narrow, wide = [], []
        if win:
            clo, chi, tol = win
            narrow = [r for _, r in self.ev.camera_between(clo - TOL_PLAIN, chi + TOL_PLAIN)
                      if r.fields.get('speed')]
            wide = [r for _, r in self.ev.camera_between(clo - tol - self.clocks.skew, chi + tol + self.clocks.skew)
                    if r.fields.get('speed')]
        cam_equal = [r for r in narrow if r.fields['speed'] == speed]
        cam_other = [r for r in narrow if r.fields['speed'] != speed]

        if support:
            # The officer's own statement agrees, but the officer also wrote the report, so this is
            # circular if an independent reading nearby disagrees: then we cannot settle it.
            if against or (cam_other and not cam_equal):
                return Verdict('not_settled')
            best = min(support, key=lambda r: AUTHORITY.get(r.kind, 9))
            return Verdict('match', best, '%g' % speed)

        if against:
            speeds = set().union(*[s for _, s in against])
            names = {_last_name(r) for r, _ in against}
            if len(speeds) == 1 and p['named'] and names == {p['named']} and not cam_equal:
                return Verdict('conflict', against[0][0], '%g' % next(iter(speeds)))
            return Verdict('not_settled')

        if CAMERA_ATTR.search(p.get('sentence', '')) and win:
            if len(narrow) == 1 and cam_equal:
                return Verdict('match', narrow[0], None)
            if len(narrow) == 1 and cam_other and abs(narrow[0].fields['speed'] - speed) >= 3 and \
                    not any(r.fields['speed'] == speed for r in wide):
                return Verdict('conflict', narrow[0], None)
        return Verdict('not_settled')

    # ------------------------------------------------------------ posted zone
    def _zone(self, claim):
        p = claim.params
        z = float(p['zone'])
        cam_rows = [r for _, r in self.ev.camera if r.fields.get('zone') is not None]
        cam_zones = {r.fields['zone'] for r in cam_rows}
        stmt = [(r, zone_numbers(r.text)) for r in self.ev.statements]
        stmt = [(r, s) for r, s in stmt if s]
        stmt_zones = set().union(*[s for _, s in stmt]) if stmt else set()
        all_zones = cam_zones | stmt_zones
        if not all_zones:
            return Verdict('not_settled')
        if z in all_zones:
            if all_zones != {z}:
                return Verdict('not_settled')           # sources disagree about the limit
            if cam_rows:
                win = self._window(p['ctx'])
                target = (win[0] + win[1]) / 2 if win else None
                pick = min(cam_rows, key=lambda r: abs(self.ctx.interval(r.stamp)[0] - target)) \
                    if target is not None else cam_rows[0]
                return Verdict('match', pick, None)
            return Verdict('match', next(r for r, s in stmt if z in s), '%g' % z)
        # only a conflict if two independent kinds of source agree on a different single value
        if len(cam_zones) == 1 and len(stmt_zones) == 1 and cam_zones == stmt_zones:
            return Verdict('conflict', cam_rows[0], None)
        return Verdict('not_settled')

    # ------------------------------------------------------------ "N minutes after the X"
    def _relative(self, claim):
        p = claim.params
        if p['event'] is None or p['ref'] is None:
            return Verdict('not_checkable')
        a_events = self.ev.by_kind.get(p['event'], [])
        b_events = self.ev.by_kind.get(p['ref'], [])
        if not a_events or not b_events:
            return Verdict('not_settled')
        n = p['seconds']
        tol = max(30.0, 0.25 * abs(n)) if p['hedged'] else max(15.0, 0.10 * abs(n))
        outcomes, first = [], None
        for a in a_events:
            for b in b_events:
                if a.domain == b.domain:
                    dlo, dhi = a.lo - b.hi, a.hi - b.lo          # same clock: skew cancels
                else:
                    alo, ahi, a_ok = self.clocks.adjust(a)
                    blo, bhi, b_ok = self.clocks.adjust(b)
                    if not (a_ok and b_ok):
                        outcomes.append('unknown')
                        continue
                    dlo, dhi = alo - bhi, ahi - blo
                mid, half = (dlo + dhi) / 2, (dhi - dlo) / 2
                if abs(mid - n) <= tol and half <= tol:
                    outcomes.append('match')
                elif abs(mid - n) - half > tol + MIN_CONFLICT_MARGIN:
                    outcomes.append('conflict')
                else:
                    outcomes.append('unknown')
                first = first or a
        if outcomes and set(outcomes) == {'match'}:
            return Verdict('match', first.row, None)
        if outcomes and set(outcomes) == {'conflict'}:
            return Verdict('conflict', first.row, None)
        return Verdict('not_settled')

    # ------------------------------------------------------------ "two units"
    def _count(self, claim):
        p = claim.params
        noun = p['noun']
        if noun in ('unit', 'call'):
            kind = 'call' if noun == 'call' else p['event'] if p['event'] in ('on_scene', 'dispatch') else None
        else:
            return Verdict('not_checkable')
        if kind is None:
            return Verdict('not_settled')
        events = [e for e in self.ev.by_kind.get(kind, []) if e.row.kind == 'dispatch']
        if not events:
            return Verdict('not_settled')
        if kind == 'call':
            seen = len(events)
        else:
            seen = len({e.row.fields.get('unit') or e.row.fields.get('id') or id(e) for e in events})
        if seen == p['n']:
            return Verdict('match', events[0].row, None)
        if seen > p['n'] and p['exact']:
            return Verdict('conflict', events[0].row, None)
        return Verdict('not_settled')
