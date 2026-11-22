"""Shared vocabulary: which words mean which kind of event, how hedged a time is.
Used on BOTH the report text and the record text so the two sides are read the same way."""
import re

# Priority order matters: a note like "dispatched unit to the call" is a dispatch, not a call.
# Each kind has STRONG words (the sentence is really about that event) and WEAK words (loose vocabulary
# that often means something else: "Called for backup" is not the 911 call, "saw a sedan" is not the
# officer's first observation). Weak words never create evidence: they cannot support or contradict.
EVENT_PATTERNS = [
    ('on_scene', re.compile(r'\bon[- ]scene\b|\barriv(?:ed|al|es|ing)\b', re.I),
     re.compile(r'\bresponded\b', re.I)),
    ('dispatch', re.compile(r'\bdispatched\b', re.I), None),
    ('stop', re.compile(r"\bstopp?ed\b|\bpull(?:ed|ing)\s+(?:over|in|into)\b|\bcame to a (?:stop|halt)\b|\bhalted\b", re.I),
     None),
    ('observed', re.compile(r'\bobserv(?:ed|ing)\b|\bspott(?:ed|ing)\b', re.I),
     re.compile(r'\bsaw\b|\bnoticed\b', re.I)),
    ('call', re.compile(r'\b911\b|\bemergency call\b', re.I), re.compile(r'\bcaller\b|\bcall(?:ed)?\b', re.I)),
]
# Record text that tries to talk to the tool ("ignore your rules", "SYSTEM: ...") is data about nothing:
# such rows are quarantined and never become evidence in either direction.
INSTRUCTION_LIKE = re.compile(
    r"\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:instructions?|rules?|prompt|previous|above|guidelines)\b"
    r"|(?:^|[\s\"'(\[])(?:system|assistant)\s*:"
    r"|\bmark\s+(?:every|all|each)\b|\boutput\s*[{\[]|\bas an ai\b|\byou\s+(?:must|are now)\b", re.I)
NEGATION = re.compile(r"\b(?:not|never|no|without|unable|failed to)\b|n't\b", re.I)
HEDGE = re.compile(r'\b(?:about|around|approximately|approx\.?|roughly|circa|nearly|close to)\b|~', re.I)

# dispatch-export "type" values -> event kinds
DISPATCH_TYPES = [('scene', 'on_scene'), ('arriv', 'on_scene'), ('dispatch', 'dispatch'),
                  ('911', 'call'), ('call', 'call')]


def classify_text_ex(text):
    """(event kind, strong) a piece of free text describes, or (None, False). Negated text is never
    classified: "did not stop at 21:16" must not become evidence that a stop happened."""
    if not text or NEGATION.search(text):
        return None, False
    for kind, strong, _ in EVENT_PATTERNS:
        if strong.search(text):
            return kind, True
    for kind, _, weak in EVENT_PATTERNS:
        if weak is not None and weak.search(text):
            return kind, False
    return None, False


def classify_text(text):
    """Event kind only (used on the report side, where loose words are fine: the claim names the event)."""
    return classify_text_ex(text)[0]


def is_instruction_like(text):
    return bool(INSTRUCTION_LIKE.search(text or ''))


def classify_dispatch_type(value):
    v = str(value or '').lower()
    for needle, kind in DISPATCH_TYPES:
        if needle in v:
            return kind
    return None


def is_hedged(text):
    return bool(HEDGE.search(text or ''))
