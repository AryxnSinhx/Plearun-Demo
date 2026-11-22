"""Independent world model + renderers for the held-out evaluation.
Deliberately imports nothing from plearun/: the generator must not share the tool's blind spots.

World clock = the report clock = the dispatch (CAD) clock. Every other source gets its own offset
(seconds added to the true time before it is written down), so 'clock skew' is explicit ground truth.
"""
import datetime as dt
import json

EPOCH = dt.datetime(1970, 1, 1)


def tzstr(off):
    a = abs(off)
    return '%s%02d:%02d' % ('-' if off < 0 else '+', a // 3600, a % 3600 // 60)


def make_world(rng, tz=-5 * 3600, date=None, base=None):
    date = date or dt.date(2026, rng.randint(1, 12), rng.randint(1, 28))
    b = base if base is not None else rng.randint(20 * 3600, 22 * 3600 + 1800)
    w = {'date': date, 'tz': tz, 'call': b}
    w['disp'] = b + rng.randint(60, 240)
    w['obs'] = b + rng.randint(260, 320)
    w['stop'] = w['obs'] + rng.randint(90, 150)
    w['scene'] = w['stop'] + rng.randint(90, 200)
    w['officer'] = rng.choice(['Lee', 'Okafor', 'Nguyen', 'Brandt', 'Moreno', 'Patel', 'Kowalski'])
    w['zone'] = rng.choice([35, 40, 45, 50, 55])
    w['speed'] = w['zone'] + rng.randint(9, 25)
    w['unit'] = 'L-%d' % rng.randint(10, 40)
    return w


def local_dt(w, t):
    return dt.datetime.combine(w['date'], dt.time()) + dt.timedelta(seconds=t)


def ts(w, t, style):
    """Render local-seconds t (since local midnight of the incident date) in a timestamp style."""
    d = local_dt(w, t)
    tz = w['tz']
    if style == 'iso':
        return d.strftime('%Y-%m-%dT%H:%M:%S') + tzstr(tz)
    if style == 'iso_z':
        return (d - dt.timedelta(seconds=tz)).strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
    if style == 'naive':
        return d.strftime('%Y-%m-%d %H:%M:%S')
    if style == 'naive_utc':
        return (d - dt.timedelta(seconds=tz)).strftime('%Y-%m-%d %H:%M:%S')
    if style == 'epoch_ms':
        return int((d - dt.timedelta(seconds=tz) - EPOCH).total_seconds() * 1000)
    if style == 'epoch_s':
        return int((d - dt.timedelta(seconds=tz) - EPOCH).total_seconds())
    if style == 'tod':
        return d.strftime('%H:%M')
    if style == 'tod_s':
        return d.strftime('%H:%M:%S')
    raise ValueError(style)


def hhmm(t, style='24'):
    d = local_dt({'date': dt.date(2000, 1, 1)}, t)
    if style == '12':
        return d.strftime('%I:%M %p').lstrip('0')
    if style == 'hrs':
        return d.strftime('%H%M') + ' hrs'
    return d.strftime('%H:%M')


# ----------------------------------------------------------------------------- dispatch.json
def render_dispatch(w, events, layout='flat', indent=2, trailing_nl=False, ts_styles=('iso',), off=0):
    """events: [(type, true_t, extra)]; layout flat | nested | audit_first | alt_keys."""
    items = []
    for i, (typ, t, extra) in enumerate(events):
        style = ts_styles[i % len(ts_styles)]
        tkey = 'timestamp' if layout == 'alt_keys' else 'logged'
        d = {'id': 'D-%d' % (1001 + i), 'type' if layout != 'alt_keys' else 'event_type': typ,
             tkey: ts(w, t + off, style)}
        d.update(extra)
        items.append(d)
    if layout == 'nested':
        doc = {'export': {'system': 'CAD-SYNTH', 'incidents': [{'incident_id': 'INC-1', 'timeline': items}]}}
    elif layout == 'audit_first':
        doc = {'export': {'system': 'CAD-SYNTH',
                          'audit': [{'user': 'sys', 'at': ts(w, 19 * 3600, 'iso'), 'action': 'login'}],
                          'events': items}}
    else:
        doc = {'export': {'system': 'CAD-SYNTH', 'version': '3.1', 'events': items}}
    s = json.dumps(doc, indent=indent, ensure_ascii=False)
    return (s + ('\n' if trailing_nl else '')).encode('utf-8')


# ----------------------------------------------------------------------------- notes csv
def render_notes(w, rows, off=0, style='tod', encoding='cp1252', delim=',', header=True, nl='\r\n',
                 bom=False, marker=False):
    """rows: [(author, text, true_t)] -> bytes in the requested encoding/format."""
    def q(v):
        v = str(v)
        return '"%s"' % v.replace('"', '""') if (delim in v or '"' in v or '\n' in v) else v
    lines = []
    if marker:
        lines.append('#PLEARUN SYNTHETIC FICTIONAL RECORD FILE - notes export')
    if header:
        lines.append(delim.join(['ID', 'Author', 'Note', 'Time']))
    for i, (author, text, t) in enumerate(rows):
        lines.append(delim.join([q('N-%d' % (i + 1)), q(author), q(text), q(ts(w, t + off, style))]))
    data = nl.join(lines) + nl
    if encoding == 'utf-16':
        return (b'\xff\xfe' + data.encode('utf-16-le'))
    if encoding == 'utf-16-nobom':
        return data.encode('utf-16-le')
    raw = data.encode(encoding)
    return (b'\xef\xbb\xbf' + raw) if (bom or encoding == 'utf-8-sig') and encoding != 'cp1252' else raw


# ----------------------------------------------------------------------------- bodycam vtt
def render_vtt(w, cues, off=0, cue_ids=False, tags=False, nl='\n', hours=False):
    """cues: [(speaker, text)] -> overlapping cues, relative timings only. Spoken times are in text."""
    out = ['WEBVTT', '']
    start = 0.0
    for i, (speaker, text) in enumerate(cues):
        end = start + 4.0
        f = lambda x: ('00:' if hours else '') + '%02d:%06.3f' % (int(x // 60), x % 60)
        if cue_ids:
            out.append('cue-%d' % (i + 1))
        out.append('%s --> %s' % (f(start), f(end)))
        body = '[SYNTHETIC] %s: %s' % (speaker, text)
        out.append('<v %s>%s</v>' % (speaker, body) if tags else body)
        out.append('')
        start += 3.5
    return nl.join(out).encode('utf-8')


# ----------------------------------------------------------------------------- camera csv
def render_camera(w, readings, style='mixed', off=0, bom=True, marker=True, nl='\r\n', speed_hdr='speed_mph',
                  zone_hdr='zone_mph', device_hdr='device'):
    """readings: [(device, true_t, speed, zone)] in the order given (callers may shuffle)."""
    lines = []
    if marker:
        lines.append('#PLEARUN SYNTHETIC FICTIONAL RECORD FILE - camera export v2')
    lines.append(','.join(['timestamp', device_hdr, speed_hdr, zone_hdr]))
    for i, (dev, t, sp, zn) in enumerate(readings):
        st = style if style != 'mixed' else ('epoch_ms' if i % 3 == 0 else 'iso')
        lines.append('%s,%s,%s,%s' % (ts(w, t + off, st), dev, sp, zn))
    first_nl = '\n' if marker else nl
    body = (lines[0] + first_nl + nl.join(lines[1:]) + nl) if marker else nl.join(lines) + nl
    data = body.encode('utf-8')
    return (b'\xef\xbb\xbf' + data) if bom else data
