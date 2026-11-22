#!/usr/bin/env python3
"""Metamorphic invariance tests: transform a case's records in a way that must not change any finding,
re-run, compare. Needs no expected answers. Usage: python3 eval/meta.py [--every K] [--out FILE]"""
import argparse
import datetime as dt
import json
import os
import random
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run import run_cli, decode  # noqa: E402

CSV_HEAD = re.compile(r'^(timestamp,|ID,)', re.I)
EP = dt.datetime(1970, 1, 1)


def is_text(b):
    return not (b.startswith(b'\xff\xfe') or b.startswith(b'\xfe\xff') or b'\x00' in b[:200])


def split_csv(text):
    lines = text.split('\n')
    for i, ln in enumerate(lines):
        if CSV_HEAD.match(ln.lstrip('\ufeff')):
            data = [x for x in lines[i + 1:] if x.strip()]
            return lines[:i + 1], data
    return None, None


def t_crlf_to_lf(name, b, rng):
    return b.replace(b'\r\n', b'\n') if name.endswith(('.csv', '.vtt')) and is_text(b) else b


def t_lf_to_crlf(name, b, rng):
    if name.endswith(('.csv', '.vtt')) and is_text(b):
        return b.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    return b


def _rewrite(name, b, rng, fn):
    if not name.endswith('.csv') or not is_text(b):
        return b
    text = b.decode('utf-8', errors='surrogateescape')
    head, data = split_csv(text.replace('\r\n', '\n'))
    if head is None:
        return b
    eol = '\r\n' if '\r\n' in text else '\n'
    data = fn(data)
    return (eol.join(head + data) + eol).encode('utf-8', errors='surrogateescape')


def t_shuffle(name, b, rng):
    def f(d):
        d = list(d)
        rng.shuffle(d)
        return d
    return _rewrite(name, b, rng, f)


def t_dup_row(name, b, rng):
    return _rewrite(name, b, rng, lambda d: d + ([rng.choice(d)] if d else []))


def t_noise(name, b, rng):
    def f(d):
        out = list(d)
        for ln in rng.sample(d, min(4, len(d))):
            m = re.search(r'T(\d\d):', ln)
            if m and 'camera' in name:
                out.append(ln.replace(m.group(0), 'T%02d:' % ((int(m.group(1)) - 6) % 24)))
        if 'notes' in name:
            out.append('N-99,Dispatch,Radio check complete,%s' % (d[0].rsplit(',', 1)[-1] if d else '12:00'))
        return out
    return _rewrite(name, b, rng, f)


def t_cam_format(name, b, rng):
    def f(d):
        out = []
        for ln in d:
            first, rest = ln.split(',', 1)
            if re.fullmatch(r'\d{13}', first):
                s = (EP + dt.timedelta(milliseconds=int(first)) - dt.timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M:%S')
                out.append(s + '-05:00,' + rest)
            elif re.match(r'\d{4}-\d\d-\d\dT[\d:]+-05:00$', first):
                d0 = dt.datetime.strptime(first[:19], '%Y-%m-%dT%H:%M:%S') + dt.timedelta(hours=5)
                out.append('%d,%s' % (int((d0 - EP).total_seconds() * 1000), rest))
            else:
                out.append(ln)
        return out
    return _rewrite(name, b, rng, f) if 'camera' in name else b


# name -> (fn, compare_quote)
TRANSFORMS = {'crlf_to_lf': (t_crlf_to_lf, True), 'lf_to_crlf': (t_lf_to_crlf, True),
              'shuffle_rows': (t_shuffle, False), 'duplicate_row': (t_dup_row, False),
              'unrelated_noise': (t_noise, False), 'camera_timestamp_format': (t_cam_format, False)}


def sig(doc, with_quote):
    return [(f['claim'], f['finding']) + ((f.get('quote'),) if with_quote else ()) for f in doc['findings']]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', default=os.path.join(HERE, 'cases'))
    ap.add_argument('--every', type=int, default=4)
    ap.add_argument('--out', default=os.path.join(HERE, 'results', 'metamorphic_latest.md'))
    a = ap.parse_args()
    rng = random.Random(3)
    names = sorted(os.listdir(a.cases))[::a.every]
    viol, total = [], 0
    for cname in names:
        d = os.path.join(a.cases, cname)
        rep = os.path.join(d, 'report.txt')
        rc, out, _, _ = run_cli(rep, os.path.join(d, 'records'))
        base = json.loads(out)
        for tname, (fn, cq) in TRANSFORMS.items():
            tmp = tempfile.mkdtemp()
            try:
                changed = False
                for f in os.listdir(os.path.join(d, 'records')):
                    b = open(os.path.join(d, 'records', f), 'rb').read()
                    nb = fn(f, b, rng)
                    changed |= nb != b
                    open(os.path.join(tmp, f), 'wb').write(nb)
                if not changed:
                    continue
                total += 1
                rc, out, _, _ = run_cli(rep, tmp)
                try:
                    got = json.loads(out)
                except Exception:
                    viol.append((cname, tname, 'invalid JSON'))
                    continue
                if sig(got, cq) != sig(base, cq):
                    diff = [(x, y) for x, y in zip(sig(base, cq), sig(got, cq)) if x != y][:2]
                    viol.append((cname, tname, str(diff)[:300]))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    L = ['# Metamorphic invariance\n', 'Transformed runs: %d; invariance violations: %d\n' % (total, len(viol))]
    if viol:
        L.append('| case | transform | first difference |\n|---|---|---|')
        by = {}
        for c, t, d in viol:
            by.setdefault(t, []).append((c, d))
        for t, items in sorted(by.items()):
            L.append('| (%s: %d violations) | | |' % (t, len(items)))
            for c, d in items[:4]:
                L.append('| %s | %s | %s |' % (c, t, d.replace('|', '/')))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
