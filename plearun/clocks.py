"""Estimate clock offsets between sources from events that BOTH sources record.

For one event seen in domains A and B, B_time - A_time = (offset_B - offset_A) up to the precision of
the two timestamps, which gives an interval, not a number. A domain pair is aligned only if
  * at least two different kinds of event anchor it (one coincidence proves nothing),
  * every anchor kind appears exactly once per domain (otherwise we do not know which pairs with which),
  * the intervals from all anchors intersect (they agree), and
  * the intersection is narrower than MAX_WIDTH (a minute-resolution note cannot pin a clock tighter).
Anything that fails stays unaligned: callers then treat its times as "could be off by Clocks.skew".
"""
from collections import defaultdict, deque
from itertools import combinations

from .events import AUTHORITY

MAX_WIDTH = 30.0
MIN_SKEW = 180.0          # least clock error we ever allow an unaligned source
MAX_SKEW = 900.0          # beyond 15 min two sources are disagreeing about the event, not about the clock
REF_SKEW = 90.0           # even an aligned group is only as good as its reference clock


class Clocks:
    def __init__(self, offsets, notes, skew=MIN_SKEW):
        self.offsets = offsets            # domain -> (lo, hi) of (domain_clock - reference_clock)
        self.notes = notes
        self.skew = skew                  # how far an UNALIGNED source may be off: at least MIN_SKEW, more if the
                                          # sources visibly disagree with each other by more than that

    def adjust(self, event):
        """(lo, hi, aligned) of the event on the reference clock."""
        off = self.offsets.get(event.domain)
        if off is None:
            return event.lo, event.hi, False
        return event.lo - off[1], event.hi - off[0], True

    def skew_for(self, aligned):
        return REF_SKEW if aligned else self.skew


def estimate(ev):
    notes = []
    unique = defaultdict(dict)            # domain -> kind -> Event (only kinds seen exactly once)
    counts = defaultdict(int)
    for kind, events in ev.by_kind.items():
        for e in events:
            counts[(e.domain, kind)] += 1
    for kind, events in ev.by_kind.items():
        for e in events:
            if counts[(e.domain, kind)] == 1:
                unique[e.domain][kind] = e

    links = {}                            # (A, B) -> (lo, hi) for clock_B - clock_A
    spread = 0.0                          # largest rough disagreement seen between any two sources
    for a, b in combinations(sorted(unique), 2):
        shared = set(unique[a]) & set(unique[b])
        for k in shared:                  # even ONE shared event says how far apart the clocks can be
            ea, eb = unique[a][k], unique[b][k]
            spread = max(spread, abs((eb.lo + eb.hi) / 2 - (ea.lo + ea.hi) / 2))
        if len(shared) < 2:
            if shared:
                notes.append('%s ~ %s: only one shared event kind (%s), not enough to align'
                             % (a, b, ', '.join(sorted(shared))))
            continue
        lo, hi = -float('inf'), float('inf')
        for k in shared:
            ea, eb = unique[a][k], unique[b][k]
            lo, hi = max(lo, eb.lo - ea.hi), min(hi, eb.hi - ea.lo)
        if lo > hi:
            notes.append('%s ~ %s: anchors disagree, left unaligned' % (a, b))
        elif hi - lo > MAX_WIDTH:
            notes.append('%s ~ %s: offset only known to within %.0fs, left unaligned' % (a, b, hi - lo))
        else:
            links[(a, b)] = (lo, hi)

    graph = defaultdict(list)
    for (a, b), (lo, hi) in links.items():
        graph[a].append((b, lo, hi))
        graph[b].append((a, -hi, -lo))
    offsets = {}
    if graph:
        # One reference clock only: offsets from two different components would not be comparable.
        start = min(graph, key=lambda d: (AUTHORITY.get(d.split(':')[0], 9), d))
        offsets[start] = (0.0, 0.0)
        queue = deque([start])
        while queue:
            cur = queue.popleft()
            for nxt, lo, hi in graph[cur]:
                if nxt in offsets:
                    continue
                total = (offsets[cur][0] + lo, offsets[cur][1] + hi)
                if total[1] - total[0] <= MAX_WIDTH:
                    offsets[nxt] = total
                    queue.append(nxt)
    return Clocks(offsets, notes, min(MAX_SKEW, max(MIN_SKEW, 1.5 * spread + 60.0)))
