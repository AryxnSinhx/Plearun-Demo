"""Split a report into atomic claims. Every claim's text is a verbatim slice of the report.

A sentence is cut into clauses (at commas, 'and', 'but'...). Each clause yields zero or more atoms:
  time      "<event> at about 21:14"            -> judged against events of that kind
  speed     "travelling 58 mph"                 -> judged against statements (and carefully, the camera)
  zone      "in a posted 45 zone"
  relative  "a unit on scene roughly 2 minutes after the stop"
  count     "two units responded"
  uncheckable  anything else that asserts something (location, lane, colour ...) - no record type can settle it
Attribution words ("Dispatch records show", "Officer Lee states") are not claims and are dropped when
other atoms exist in the clause.
"""
import re
from dataclasses import dataclass, field

from .semantics import classify_text, HEDGE

MONTHS = {m: i + 1 for i, m in enumerate(
    ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
     'november', 'december'])}
NUM_WORDS = {'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
             'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12}

_ABBR = re.compile(r'\b(?:Mr|Mrs|Ms|Dr|St|Rd|Ave|No|Lt|Sgt|Cpl|Capt|Det|vs|approx|etc|Inc|Co)\.$', re.I)
_SENT_BREAK = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"\'(\[])')
_LEAD_ONLY = re.compile(r'^\s*(?:(?:at|by|around|about|approximately|approx\.?|roughly)\s+)+$', re.I)   # >= 1 lead word: a bare "22:20 the driver..." is the tail of a range
_INTRO_TIME = re.compile(
    r'^\s*(?:(?:at|by|around|about|approximately|roughly)\s+)+'
    r'(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?(?:\s*[ap]\.?m\.?)?'
    r'(?:\s+on\s+(?:\d{4}-\d{2}-\d{2}|'
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+'
    r'\d{1,2},?\s+\d{4}))?(,)\s', re.I)
_CLAUSE_BREAK = re.compile(r'\s*[;,]\s+|\s+(?:and|but|while|whereas|then|which)\s+|\s+[\u2013\u2014-]\s+')
_ISO_DATE = re.compile(r'\b(\d{4})-(\d{2})-(\d{2})\b')
_LONG_DATE = re.compile(r'\b(January|February|March|April|May|June|July|August|September|October|November|'
                        r'December)\s+(\d{1,2}),?\s+(\d{4})\b', re.I)
_ATTR = re.compile(
    r'^\s*(?:(?:the\s+)?(?:\w+\s+){0,2}?(?:records?|logs?|data|exports?|reports?)\s+(?:also\s+)?'
    r'(?:show|shows|showed|indicate|indicates|state|states|confirm|confirms)\s+(?:that\s+)?'
    r'|(?:officer|ofc\.?|sgt\.?|deputy|detective|det\.?)\s+\w+\s+(?:states?|stated|says|said|reports?|'
    r'reported|noted|wrote|testified|claims?)\s+(?:that\s+)?)', re.I)
_TIME = re.compile(r'(?<![\d:.])([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?(?:\s*([ap])\.?m\.?)?(?![\d:])', re.I)
_ZONE = [
    re.compile(r'(?:(?:in|within)\s+an?\s+|the\s+)?posted\s+(?:speed\s+limit\s+(?:of|is|was)\s+)?'
               r'(\d{2,3})(?:\s*-?\s*mph)?(?:\s+(?:zone|limit|speed limit))?', re.I),
    re.compile(r'(?:(?:in|within)\s+an?\s+)?(\d{2,3})(?:\s*-?\s*mph)?\s+(?:zone|speed limit|limit)\b', re.I),
    re.compile(r'speed limit\s+(?:of|is|was)\s+(\d{2,3})(?:\s*mph)?', re.I),
]
_SPEED_IN_ZONE = re.compile(r'(\d{2,3})\s+in\s+an?\s+(\d{2,3})\b', re.I)
_SPEED = re.compile(r'(?:(?:travel+ing|driving|going|doing|clocked(?:\s+at)?|speeding(?:\s+at)?|at)\s+)?'
                    r'(\d{2,3}(?:\.\d+)?)\s*-?\s*(?:mph|miles per hour|mi/h)\b', re.I)
_REL = re.compile(r'(\d+(?:\.\d+)?|an?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*'
                  r'(seconds?|secs?|minutes?|mins?|hours?)\s+(after|before|later|earlier|following|prior to)'
                  r'(?:\s+(?:the|that|his|her|their)\s+([A-Za-z0-9 ]+?))?(?=\s*[.,;]|\s*$)', re.I)
_COUNT = re.compile(r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+'
                    r'(?:(?:police|patrol|emergency|separate|additional|other|more)\s+)?'
                    r'(units?|officers?|cars?|vehicles?|calls?|people|persons|occupants|passengers|witnesses|'
                    r'cruisers)\b', re.I)
_OFFICER = re.compile(r'\b(?:Officer|Ofc\.?|Sgt\.?|Deputy|Detective)\s+([A-Z\u00C0-\u00DE][^\W\d_]+)')
REF_KINDS = [('stop', 'stop'), ('halt', 'stop'), ('call', 'call'), ('dispatch', 'dispatch'),
             ('arriv', 'on_scene'), ('scene', 'on_scene'), ('observ', 'observed'), ('sight', 'observed'),
             ('spott', 'observed')]


@dataclass
class Claim:
    text: str
    start: int
    end: int
    kind: str                       # time | speed | zone | relative | count | uncheckable
    params: dict = field(default_factory=dict)


def _num(word):
    w = word.lower()
    return NUM_WORDS[w] if w in NUM_WORDS else float(w)


def _hedged_before(clause, pos):
    return bool(HEDGE.search(clause[max(0, pos - 16):pos]))


def _time_token(m):
    h, mi, s, ap = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
    if ap:
        if h > 12 or h == 0:
            return None
        h = h % 12 + (12 if ap.lower() == 'p' else 0)
    return h * 3600 + mi * 60 + int(s or 0), 0.0 if s else 59.0


def _sentences(text):
    for line in re.finditer(r'[^\n]+', text):
        base, body, start = line.start(), line.group(), 0
        for m in _SENT_BREAK.finditer(body):
            if _ABBR.search(body[start:m.start()]):
                continue
            yield base + start, base + m.start()
            start = m.end()
        if start < len(body):
            yield base + start, base + len(body)


def _trim(text, s, e):
    while s < e and text[s].isspace():
        s += 1
    while e > s and (text[e - 1].isspace() or text[e - 1] in '.!?'):
        e -= 1
    return s, e


def _report_date(text):
    m = _ISO_DATE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = _LONG_DATE.search(text)
    if m:
        return int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))
    return None


def _is_metadata(seg):
    if 'SYNTHETIC' in seg or 'FICTIONAL' in seg:
        return True
    return bool(re.search(r'\bincident\b', seg, re.I) and (_ISO_DATE.search(seg) or _LONG_DATE.search(seg))
                and len(seg.split()) <= 14)


_VEHICLE_CLASS = re.compile(
    r'\b(?:sedan|suv|car|truck|pickup|van|motorcycle|motorbike|bus|vehicle)\b', re.I)
_REFERENTIAL_VEHICLE_START = re.compile(
    r'^\s*(?:the|this|that)\s+(?:[\w-]+\s+){0,2}'
    r'(?:sedan|suv|car|truck|pickup|van|motorcycle|motorbike|bus|vehicle)\b', re.I)


def _vehicle_classes(sentence):
    return {m.group(0).lower() for m in _VEHICLE_CLASS.finditer(sentence)}


def parse_report(text):
    """-> (claims in report order, report date as (y, m, d) or None).

    A speed claim may inherit a timestamp from the immediately preceding sentence only
    when that sentence explicitly timestamps an observation of a vehicle and the next
    sentence begins with a definite reference to the same vehicle class. This narrow
    rule avoids carrying time context across paragraphs, unrelated sentences, or vehicle
    types; it is still an inference, so it is used only to widen evidence evaluation.
    """
    claims = []
    previous_observation = None
    previous_end = None
    for s, e in _sentences(text):
        # Blank paragraphs break conversational/entity context.
        if previous_end is not None and re.search(r'\n[ \t]*\n', text[previous_end:s]):
            previous_observation = None
        s, e = _trim(text, s, e)
        if e <= s or _is_metadata(text[s:e]):
            previous_observation = None
            previous_end = e
            continue
        sentence = text[s:e]
        current = _sentence_claims(text, s, e)

        # Conservative one-sentence temporal inheritance for anaphoric speed claims.
        if previous_observation:
            prev_classes = previous_observation['vehicle_classes']
            current_classes = _vehicle_classes(sentence)
            shared = prev_classes & current_classes
            if len(prev_classes) == 1 and prev_classes == current_classes and \
                    _REFERENTIAL_VEHICLE_START.match(sentence):
                inherited = previous_observation['time']
                for claim in current:
                    if claim.kind == 'speed' and claim.params.get('ctx') is None:
                        claim.params['ctx'] = inherited

        claims.extend(current)
        observed_times = [c.params for c in current
                         if c.kind == 'time' and c.params.get('event') == 'observed'
                         and c.params.get('secs') is not None]
        vehicle_classes = _vehicle_classes(sentence)
        previous_observation = None
        if len(observed_times) == 1 and vehicle_classes:
            p = observed_times[0]
            previous_observation = {
                'time': {'secs': p['secs'], 'span': p.get('span', 59.0),
                         'hedged': p.get('hedged', False)},
                'vehicle_classes': vehicle_classes,
            }
        previous_end = e
    claims.sort(key=lambda c: (c.start, c.end))
    return claims, _report_date(text)


def _sentence_claims(text, s, e):
    sentence = text[s:e]
    times = [m for m in _TIME.finditer(sentence) if _time_token(m)]
    ctx_time = None
    if len(times) == 1:
        secs, span = _time_token(times[0])
        ctx_time = {'secs': secs, 'span': span, 'hedged': _hedged_before(sentence, times[0].start())}
    officer = _OFFICER.search(sentence)
    named = officer.group(1) if officer else None

    out = []
    cuts, pos = [], 0
    intro = _INTRO_TIME.match(sentence)          # "At 21:14, Officer Lee ...": the time belongs to the next clause
    for m in _CLAUSE_BREAK.finditer(sentence):
        if intro and intro.start() <= m.start() < intro.end():
            continue
        cuts.append((pos, m.start()))
        pos = m.end()
    cuts.append((pos, len(sentence)))
    for cs, ce in cuts:
        if ce <= cs:
            continue
        out.extend(_clause_claims(text, s + cs, s + ce, ctx_time, named, sentence))
    return out


def _clause_claims(text, cs, ce, ctx_time, named, sentence=''):
    clause = text[cs:ce]
    m = _ATTR.match(clause)
    a0 = m.end() if m else 0                      # atoms start after any attribution phrase
    atoms = []                                    # (start, end, kind, params) relative to clause

    if NEG_RE.search(clause):
        return [_unc(text, cs, ce)] if len(clause.split()) >= 3 else []

    zone_spans = []
    for pat in _ZONE:
        for zm in pat.finditer(clause, a0):
            if any(zm.start() < b and a < zm.end() for a, b in zone_spans):
                continue
            zone_spans.append((zm.start(), zm.end()))
            atoms.append((zm.start(), zm.end(), 'zone', {'zone': int(zm.group(1))}))
    for sm in _SPEED_IN_ZONE.finditer(clause, a0):
        if any(sm.start() < b and a < sm.end() for a, b in zone_spans):
            continue
        atoms.append((sm.start(), sm.start() + len(sm.group(1)), 'speed', {'speed': float(sm.group(1))}))
        atoms.append((sm.start() + len(sm.group(1)), sm.end(), 'zone', {'zone': int(sm.group(2))}))
        zone_spans.append((sm.start(), sm.end()))
    for sm in _SPEED.finditer(clause, a0):
        if any(sm.start() < b and a < sm.end() for a, b in zone_spans):
            continue
        atoms.append((sm.start(), sm.end(), 'speed', {'speed': float(sm.group(1))}))

    tm = next((t for t in _TIME.finditer(clause, a0) if _time_token(t)), None)
    local_time = None
    if tm:
        secs, span = _time_token(tm)
        local_time = {'secs': secs, 'span': span, 'hedged': _hedged_before(clause, tm.start())}
        event = classify_text(clause[a0:tm.end()])
        end = tm.end()
        if event is None and not atoms and _LEAD_ONLY.match(clause[a0:tm.start()]):
            # time-first phrasing ("At 21:14 Officer Lee observed the sedan"): the event follows the time
            event = classify_text(clause[tm.end():])
            if event is not None:
                end = len(clause)
        if event is not None or not any(a[2] in ('speed', 'zone') for a in atoms):
            atoms.append((a0, end, 'time', dict(local_time, event=event, named=named)))
    else:
        rm = _REL.search(clause, a0)
        if rm:
            n = _num(rm.group(1))
            unit = rm.group(2).lower()
            seconds = n * (3600 if unit.startswith('h') else 60 if unit.startswith('m') else 1)
            if rm.group(3).lower() in ('before', 'earlier', 'prior to'):
                seconds = -seconds
            ref_words = (rm.group(4) or '').lower()
            ref = next((k for needle, k in REF_KINDS if needle in ref_words), None)
            hedged = _hedged_before(clause, rm.start())
            atoms.append((a0, rm.end(), 'relative',
                          {'seconds': seconds, 'event': classify_text(clause[a0:rm.start()]),
                           'ref': ref, 'hedged': hedged}))
        else:
            cm = _COUNT.search(clause, a0)
            if cm:
                atoms.append((a0, len(clause), 'count',
                              {'n': int(_num(cm.group(1))), 'noun': cm.group(2).lower().rstrip('s'),
                               'event': classify_text(clause), 'exact': bool(EXACT_RE.search(clause))}))

    atoms.sort(key=lambda a: (a[0], a[1]))
    if atoms and atoms[0][2] in ('speed', 'zone') and atoms[0][0] > a0:
        # "The car was travelling 58 mph": the words before the number are the subject, not a claim
        atoms[0] = (a0,) + atoms[0][1:]
    ctx = local_time or ctx_time
    claims = []
    for a, b, kind, params in atoms:
        if kind in ('speed', 'zone'):
            params = dict(params, ctx=ctx, named=named, sentence=sentence)
        claims.append(Claim(clause[a:b], cs + a, cs + b, kind, params))

    # leftovers: stretches of the clause no atom explains still assert something
    covered = sorted((a, b) for a, b, _, _ in atoms)
    cursor = a0 if atoms else 0
    pieces = []
    for a, b in covered:
        if a > cursor:
            pieces.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < len(clause):
        pieces.append((cursor, len(clause)))
    for a, b in pieces:
        piece = clause[a:b]
        lead = re.match(r'[\s,;:\u2013\u2014-]*(?:(?:and|but|which|where|that)\s+)?', piece)
        a += lead.end()
        a, b = _trim(clause, a, b)
        if len(clause[a:b].split()) >= 3 and not _ATTR.fullmatch(clause[a:b] + ' '):
            claims.append(_unc(text, cs + a, cs + b))
    return claims


NEG_RE = re.compile(r"\b(?:not|never|no|without|unable|failed to)\b|n't\b", re.I)
EXACT_RE = re.compile(r'\b(?:only|exactly|just|a total of)\b', re.I)


def _unc(text, s, e):
    return Claim(text[s:e], s, e, 'uncheckable')
