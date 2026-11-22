"""Read record files into Row objects. Every Row keeps the exact raw text it came from,
because a finding is only allowed to quote text that is a substring of that raw text.

Row numbering (an assumption, documented in the README):
  CSV   - 1-based physical line number where the record starts (marker line and header count)
  JSON  - 1-based position among the record objects (objects that sit inside a list), document order
  VTT   - 1-based cue number in file order
"""
import csv
import io
import json
import os
import re
import sys
from json.decoder import scanstring

from .timeutil import parse_stamp, Stamp

csv.field_size_limit(1 << 24)

TIME_KEYS = ('timestamp', 'time', 'logged', 'ts', 'datetime', 'date_time', 'when', 'created',
             'created_at', 'occurred', 'at')
TEXT_KEYS = ('note', 'notes', 'text', 'comment', 'message', 'description', 'narrative')
AUTHOR_KEYS = ('author', 'officer', 'by', 'source', 'speaker', 'user')
DEVICE_KEYS = ('device', 'camera', 'cam', 'sensor')
MAX_RECORD_LINES = 50      # a CSV "record" longer than this is a runaway quote, not data
STATS = {}                 # file name -> loader statistics for the stderr yield report


class Row:
    __slots__ = ('file', 'row', 'raw', 'kind', 'domain', 'stamp', 'text', 'fields')

    def __init__(self, file, row, raw, kind, domain, stamp=None, text='', fields=None):
        self.file, self.row, self.raw, self.kind, self.domain = file, row, raw, kind, domain
        self.stamp, self.text, self.fields = stamp, text, fields or {}


def decode_bytes(data):
    """BOM first (UTF-8, UTF-16), then UTF-16 without a BOM (tell-tale NUL bytes), then UTF-8, then
    Windows-1252 (which is what the notes file uses). Never raises."""
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16', errors='replace')
    if data.startswith(b'\xef\xbb\xbf'):
        return data.decode('utf-8-sig', errors='replace')
    head = data[:400]
    if head and head.count(b'\x00') >= len(head) // 4:
        even, odd = head[0::2].count(b'\x00'), head[1::2].count(b'\x00')
        return data.decode('utf-16-be' if even > odd else 'utf-16-le', errors='replace')
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('cp1252', errors='replace')


def read_text(path):
    with open(path, 'rb') as fh:
        return decode_bytes(fh.read())


def _first_index(header, names, contains=False):
    for n in names:
        if n in header:
            return header.index(n)
    if contains:
        for i, h in enumerate(header):
            if any(n in h for n in names):
                return i
    return None


def _num(text):
    m = re.search(r'-?\d+(?:\.\d+)?', text or '')
    return float(m.group()) if m else None


# ---------------------------------------------------------------- CSV
HEADER_WORDS = set(TIME_KEYS + TEXT_KEYS + AUTHOR_KEYS + DEVICE_KEYS) | {'id', 'unit', 'type', 'zone', 'limit'}


def sniff_delimiter(text):
    """The header (first non-marker line) decides: the candidate that splits it into the most columns."""
    for ln in io.StringIO(text, newline=''):
        if ln.strip() and not ln.lstrip().startswith('#'):
            counts = {d: ln.count(d) for d in (',', ';', '\t', '|')}
            best = max(counts, key=lambda d: (counts[d], d == ','))
            return best if counts[best] > 0 else ','
    return ','


def _iter_records(text, delim):
    """Yield (first_line, last_line, fields, raw) per CSV record, streaming: only the lines of the record
    being read are held, and raw is their exact text (what a quote is checked against)."""
    buf = []

    def feed():
        for ln in io.StringIO(text, newline=''):
            buf.append(ln)
            yield ln
    reader = csv.reader(feed(), delimiter=delim)
    prev = 0
    for fields in reader:
        end = reader.line_num
        raw = ''.join(buf).rstrip('\r\n')
        buf.clear()
        yield prev + 1, end, fields, raw
        prev = end


def _looks_like_header(fields):
    cells = [f.strip().lower() for f in fields if f.strip()]
    if not cells or any(parse_stamp(c) is not None for c in cells):
        return False
    return any(c in HEADER_WORDS or 'speed' in c or 'zone' in c for c in cells)


def _infer_headerless(sample):
    """Name the columns of a file with no header row from what the cells look like, or raise."""
    n = max(len(r) for r in sample)
    cols = [[(r[i].strip() if i < len(r) else '') for r in sample] for i in range(n)]

    def frac(pred, c):
        return sum(1 for x in c if x and pred(x)) / max(1, len(c))
    is_num = lambda x: re.fullmatch(r'-?\d+(?:\.\d+)?', x) is not None
    time_i = max(range(n), key=lambda i: frac(lambda x: parse_stamp(x) is not None, cols[i]))
    if frac(lambda x: parse_stamp(x) is not None, cols[time_i]) < 0.8:
        raise ValueError('no header row and no column that looks like a timestamp')
    names = [''] * n
    names[time_i] = 'timestamp'
    numeric = [i for i in range(n) if i != time_i and frac(is_num, cols[i]) >= 0.9]
    if len(numeric) >= 2:                                   # camera-like: timestamp, device, speed, zone
        distinct = {i: len(set(cols[i])) for i in numeric}
        zone_i = min(numeric, key=lambda i: distinct[i])
        if distinct[zone_i] > 4 or any(float(x) % 5 for x in cols[zone_i] if x):
            raise ValueError('no header row and the numeric columns are ambiguous')
        speed_i = max((i for i in numeric if i != zone_i), key=lambda i: distinct[i])
        names[zone_i], names[speed_i] = 'zone_mph', 'speed_mph'
        for i in range(n):
            if not names[i]:
                names[i] = 'device' if 'device' not in names else 'col%d' % i
        return names
    rest = [i for i in range(n) if i != time_i]            # notes-like: id, author, text, time
    text_i = max(rest, key=lambda i: sum(len(x) for x in cols[i]) / max(1, len(cols[i])))
    names[text_i] = 'note'
    others = [i for i in rest if i != text_i]
    ids = [i for i in others if len(set(cols[i])) == len(cols[i]) and len(cols[i]) > 1]
    for i in others:
        names[i] = 'id' if i in ids else ('author' if 'author' not in names else 'col%d' % i)
    return names


def load_csv(path, name):
    text = read_text(path)
    delim = sniff_delimiter(text)
    records = _iter_records(text, delim)
    header = None
    cols = {}
    rows = []
    pending = []
    stats = {'records': 0, 'headerless': False}
    # the first usable record is either the header or (headerless file) the first data row
    for rec in records:
        if _usable(rec[2]):
            if _looks_like_header(rec[2]):
                header = [h.strip().lower() for h in rec[2]]
            else:
                pending.append(rec)
                for more in records:
                    if _usable(more[2]):
                        pending.append(more)
                        if len(pending) >= 60:
                            break
                header = _infer_headerless([p[2] for p in pending])
                stats['headerless'] = True
            cols = _classify_columns(header)
            break
    if header is None:
        STATS[name] = stats
        return []

    def consume(stream):
        for start, end, fields, raw in stream:
            if not _usable(fields):
                continue
            stats['records'] += 1
            if [f.strip().lower() for f in fields] == header:
                continue                                   # header repeated by a concatenated export
            if end - start > MAX_RECORD_LINES:
                continue                                   # runaway quote swallowed many lines
            r = _csv_row(name, start, raw, fields, header, cols)
            if r is not None:
                rows.append(r)
    consume(iter(pending))
    consume(records)
    STATS[name] = stats
    return rows


def _usable(fields):
    """Not blank, and not a single-field marker/comment line starting with #."""
    if not fields or all(not f.strip() for f in fields):
        return False
    return not (len(fields) == 1 and fields[0].lstrip().startswith('#'))


def _classify_columns(header):
    t = _first_index(header, TIME_KEYS)
    speed = _first_index(header, ('speed',), contains=True)
    text = _first_index(header, TEXT_KEYS)
    if t is not None and speed is not None:
        kind = 'camera'
    elif text is not None:
        kind = 'notes'
    else:
        kind = 'other'
    return {
        'kind': kind, 'time': t, 'speed': speed, 'text': text,
        'zone': _first_index(header, ('zone', 'limit'), contains=True),
        'device': _first_index(header, DEVICE_KEYS),
        'author': _first_index(header, AUTHOR_KEYS),
    }


def _cell(fields, idx):
    return fields[idx].strip() if idx is not None and idx < len(fields) else ''


def _csv_row(name, line, raw, fields, header, cols):
    stamp = parse_stamp(_cell(fields, cols['time'])) if cols['time'] is not None else None
    if cols['kind'] == 'camera':
        device = _cell(fields, cols['device']) or '?'
        unit_header = header[cols['speed']]
        speed = None if ('kph' in unit_header or 'km' in unit_header) else _num(_cell(fields, cols['speed']))
        zone = _num(_cell(fields, cols['zone']))
        if speed is not None and not (0 <= speed <= 200):
            speed = None                   # sensor glitch (999, -5): the row still exists but gives no speed
        if zone is not None and not (5 <= zone <= 100 and zone % 5 == 0):
            zone = None
        return Row(name, line, raw, 'camera', 'camera:%s:%s' % (name, device), stamp, '',
                   {'device': device, 'speed': speed, 'zone': zone})
    if cols['kind'] == 'notes':
        author = _cell(fields, cols['author'])
        body = _cell(fields, cols['text'])
        return Row(name, line, raw, 'notes', 'notes:%s' % name, stamp, body,
                   {'author': author, 'body': body})
    return Row(name, line, raw, 'other', 'other:%s' % name, stamp, ' '.join(fields), {})


# ---------------------------------------------------------------- JSON
_WS = re.compile(r'[ \t\r\n]*')
_SCAN = json.JSONDecoder().scan_once      # the C scanner: parses one value and says where it ended
MAX_DEPTH = 200


def _spans(s):
    """Walk the JSON document and return, for every list, the (start, end, object, time_key) of each object inside it.
    Values are parsed by the C scanner, so a million-event export is a loop of C calls; only the containers
    on the way down to a list are walked by hand. Raises ValueError on malformed JSON."""
    groups = []

    def skip(i):
        return _WS.match(s, i).end()

    def value(i, depth):
        if depth > MAX_DEPTH:
            raise ValueError('nesting too deep')
        c = s[i]
        if c == '{':
            return walk_obj(i, depth)
        if c == '[':
            return walk_arr(i, depth)
        try:
            return _SCAN(s, i)[1]
        except StopIteration:
            raise ValueError('bad token at %d' % i)

    def walk_obj(i, depth):
        i = skip(i + 1)
        if s[i] == '}':
            return i + 1
        while True:
            if s[i] != '"':
                raise ValueError('expected key')
            try:
                _, i = _SCAN(s, i)
            except StopIteration:
                raise ValueError('bad key')
            i = skip(i)
            if s[i] != ':':
                raise ValueError('expected colon')
            i = value(skip(i + 1), depth + 1)
            i = skip(i)
            if s[i] == ',':
                i = skip(i + 1)
            elif s[i] == '}':
                return i + 1
            else:
                raise ValueError('expected , or }')

    def walk_arr(i, depth):
        group = []
        groups.append(group)
        i = skip(i + 1)
        if s[i] == ']':
            return i + 1
        while True:
            start = i
            if s[i] == '{':
                try:
                    obj, end = _SCAN(s, i)
                except StopIteration:
                    raise ValueError('bad object')
                key = _time_key(obj)
                group.append((start, end, obj, key))
                i = end
                if key is None:
                    walk_obj(start, depth + 1)      # no timestamp of its own: it may hold lists that do
            else:
                i = value(i, depth + 1)
            i = skip(i)
            if s[i] == ',':
                i = skip(i + 1)
            elif s[i] == ']':
                return i + 1
            else:
                raise ValueError('expected , or ]')

    i = value(skip(0), 0)
    if skip(i) != len(s):
        raise ValueError('trailing data')
    return groups


def _time_key(d):
    for k in d:
        if k.lower() in TIME_KEYS and parse_stamp(d[k]) is not None:
            return k
    for k in d:
        if k.lower() != 'id' and parse_stamp(d[k]) is not None:
            return k
    return None


def load_json(path, name):
    text = read_text(path)
    try:
        groups = _spans(text)
    except (ValueError, IndexError, RecursionError):
        raise ValueError('malformed JSON')
    rows = []
    n = 0
    for group in groups:
        usable = [g for g in group if g[3] is not None]
        if not usable:
            continue                       # a list of dicts without timestamps is not an event list
        for s, e, d, key in usable:
            n += 1
            raw = text[s:e]
            kind_val = next((d[k] for k in d if k.lower() in ('type', 'event', 'event_type', 'kind')), '')
            rows.append(Row(name, n, raw, 'dispatch', 'dispatch:%s' % name, parse_stamp(d[key]),
                            ' '.join(str(v) for v in d.values() if not isinstance(v, (dict, list))),
                            {'type': str(kind_val), 'unit': d.get('unit'), 'id': d.get('id'),
                             'time_key': key}))
    STATS[name] = {'records': len(group_total(groups)), 'headerless': False}
    return rows


def group_total(groups):
    return [x for g in groups for x in g]


def json_fragment(row, key):
    """The exact `"key": value` text inside this record's raw JSON (used as the quote)."""
    m = re.search(re.escape(json.dumps(key)) + r'\s*:\s*("(?:[^"\\]|\\.)*"|[^,}\s]+)', row.raw)
    return m.group(0) if m else None


# ---------------------------------------------------------------- WebVTT
_TIMING = re.compile(r'^\s*((?:\d+:)?\d{1,2}:\d{2}[.,]\d{3})\s+-->\s+((?:\d+:)?\d{1,2}:\d{2}[.,]\d{3})')
_SPOKEN_TIME = re.compile(r'(?<![\d:.])([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?(?![\d:])')
_SPEAKER = re.compile(r'^\s*(?:\[[^\]]*\]\s*)*([A-Za-z][A-Za-z .\'-]{0,40}):\s*')


def _cue_seconds(t):
    parts = t.replace(',', '.').split(':')
    secs = 0.0
    for p in parts:
        secs = secs * 60 + float(p)
    return secs


def strip_speaker(text):
    m = _SPEAKER.match(text)
    return (m.group(1).strip(), text[m.end():]) if m else ('', text)


def load_vtt(path, name):
    text = read_text(path)
    lines = re.split(r'\r\n|\r|\n', text)
    blocks, cur = [], []
    for ln in lines:
        if ln.strip() == '':
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(ln)
    if cur:
        blocks.append(cur)
    rows, n = [], 0
    for b in blocks:
        timing_at = next((i for i, ln in enumerate(b) if '-->' in ln), None)
        if timing_at is None or timing_at > 1:
            continue                        # WEBVTT header, NOTE, STYLE, REGION blocks
        m = _TIMING.match(b[timing_at])
        if not m:
            continue
        n += 1
        payload = b[timing_at + 1:]
        clean = ' '.join(re.sub(r'<[^>]+>', '', p).strip() for p in payload).strip()
        speaker, spoken = strip_speaker(clean)
        stamp = None
        tm = _SPOKEN_TIME.search(spoken)
        if tm:
            stamp = parse_stamp('%s:%s%s' % (tm.group(1), tm.group(2), ':' + tm.group(3) if tm.group(3) else ''))
        rows.append(Row(name, n, '\n'.join(b), 'bodycam', 'bodycam:%s' % name, stamp, spoken,
                        {'speaker': speaker, 'payload': [p.strip() for p in payload if p.strip()],
                         'start': _cue_seconds(m.group(1)), 'end': _cue_seconds(m.group(2))}))
    return rows


# ---------------------------------------------------------------- directory
def load_records(directory):
    """-> (rows, notes). Notes carry per-file yield: what was read, what had a usable time, what looks wrong."""
    rows, notes = [], []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if name.startswith('.') or not os.path.isfile(path):
            continue
        ext = os.path.splitext(name)[1].lower()
        loader = {'.csv': load_csv, '.json': load_json, '.vtt': load_vtt}.get(ext)
        if loader is None:
            continue
        try:
            got = loader(path, name)
        except Exception as exc:           # one bad file must not take the whole run down
            notes.append('skipped %s: %s' % (name, exc))
            continue
        timed = sum(1 for r in got if r.stamp is not None)
        st = STATS.get(name, {})
        kinds = sorted({r.kind for r in got})
        notes.append('%s: %d rows read (%s), %d with a usable time%s' % (
            name, len(got), '/'.join(kinds) or 'none', timed, ', header inferred' if st.get('headerless') else ''))
        if not got:
            notes.append('WARNING %s: no usable rows (unknown columns, encoding or format?)' % name)
        elif any(r.kind == 'other' for r in got[:1]):
            notes.append('WARNING %s: no time/speed/text columns recognised, rows ignored' % name)
        elif timed < 0.8 * len(got) and got[0].kind not in ('other', 'bodycam'):
            notes.append('WARNING %s: only %d of %d rows have a parseable timestamp' % (name, timed, len(got)))
        rows.extend(got)
    return rows, notes
