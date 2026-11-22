#!/usr/bin/env python3
"""Run plearun_cli.py on every generated case and score it against the generator's ground truth.
Usage: python3 eval/run.py [--cases DIR] [--out PREFIX] [--label TEXT]
Writes PREFIX.json (raw per-claim results) and PREFIX.md (summary). Offline, stdlib only."""
import argparse
import collections
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLI = os.path.join(ROOT, 'plearun_cli.py')
VERDICTS = ('match', 'conflict', 'not_settled', 'not_checkable')


def decode(data):
    """Independent decoder (not the tool's): BOMs first, then UTF-8, then cp1252."""
    if data.startswith(b'\xff\xfe') or data.startswith(b'\xfe\xff'):
        return data.decode('utf-16')
    if data.startswith(b'\xef\xbb\xbf'):
        return data[3:].decode('utf-8')
    if b'\x00' in data[:200]:
        return data.decode('utf-16-le', errors='replace')
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('cp1252', errors='replace')


def quote_ok(records_dir, cite, quote):
    """Independent check that quote is real text from the cited row. CSV: physical line; VTT: cue n;
    JSON: substring of the file (row indexing there is a convention, so only the file is checked)."""
    path = os.path.join(records_dir, cite.get('file', ''))
    if not os.path.isfile(path) or not isinstance(quote, str) or not quote:
        return False, False
    with open(path, 'rb') as fh:
        text = decode(fh.read())
    row = cite.get('row')
    if path.endswith('.csv'):
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        in_file = quote in text.replace('\r\n', '\n')
        return in_file, isinstance(row, int) and 1 <= row <= len(lines) and quote in lines[row - 1]
    if path.endswith('.vtt'):
        blocks = [b for b in text.replace('\r\n', '\n').split('\n\n') if '-->' in b]
        in_file = quote in text
        return in_file, isinstance(row, int) and 1 <= row <= len(blocks) and quote in blocks[row - 1]
    return quote in text, True


def schema_ok(doc):
    if not isinstance(doc, dict) or set(doc) != {'findings'} or not isinstance(doc['findings'], list):
        return False
    for f in doc['findings']:
        if not isinstance(f, dict) or f.get('finding') not in VERDICTS or not isinstance(f.get('claim'), str):
            return False
        has = 'cite' in f or 'quote' in f
        if f['finding'] in ('match', 'conflict'):
            c = f.get('cite')
            if not (isinstance(c, dict) and isinstance(c.get('file'), str) and isinstance(c.get('row'), int)
                    and isinstance(f.get('quote'), str)):
                return False
        elif has:
            return False
    return True


def run_cli(report, records, timeout=120):
    t = time.time()
    try:
        p = subprocess.run([sys.executable, CLI, report, records], capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, b'', 'timeout', time.time() - t
    return p.returncode, p.stdout, p.stderr.decode('utf-8', 'replace'), time.time() - t


def locate(text, findings):
    """Character span of each finding's claim in the report (claims are verbatim slices, in order)."""
    spans, pos = [], 0
    for f in findings:
        i = text.find(f['claim'], pos)
        if i < 0:
            i = text.find(f['claim'])
        spans.append((i, i + len(f['claim'])) if i >= 0 else None)
        if i >= 0:
            pos = i
    return spans


def classify(truth, verdict):
    if verdict == truth:
        return 'exact'
    if verdict == 'conflict':
        return 'false_conflict'
    if verdict == 'match':
        return 'wrong_match'
    return 'safe'                      # not_settled / not_checkable where something else was ideal


def score_case(case_dir, truth):
    report = os.path.join(case_dir, 'report.txt')
    records = os.path.join(case_dir, 'records')
    text = open(report, encoding='utf-8', newline='').read()
    rc, out, err, secs = run_cli(report, records)
    res = {'id': truth['id'], 'family': truth['family'], 'variant': truth['variant'], 'secs': round(secs, 3),
           'rc': rc, 'crash': rc != 0, 'invalid_json': False, 'schema_ok': False, 'quote_bad': 0, 'cite_row_bad': 0,
           'claims': [], 'unlabelled': [], 'stderr_lines': len(err.splitlines())}
    try:
        doc = json.loads(out.decode('utf-8'))
    except Exception:
        res['invalid_json'] = True
        for e in truth['entries']:
            res['claims'].append({'key': e['key'], 'tag': e['tag'], 'truth': e['truth'], 'verdict': None,
                                  'cls': 'missing'})
        return res
    res['schema_ok'] = schema_ok(doc)
    findings = doc.get('findings', []) if isinstance(doc, dict) else []
    spans = locate(text, findings)
    used = set()
    for f in findings:
        if f.get('finding') in ('match', 'conflict') and isinstance(f.get('cite'), dict):
            a, b = quote_ok(records, f['cite'], f.get('quote'))
            res['quote_bad'] += 0 if a else 1
            res['cite_row_bad'] += 0 if b else 1
    for e in truth['entries']:
        hits = [i for i, sp in enumerate(spans) if sp and sp[0] < e['end'] and e['start'] < sp[1]]
        used.update(hits)
        if not hits:
            res['claims'].append({'key': e['key'], 'tag': e['tag'], 'truth': e['truth'], 'verdict': None,
                                  'cls': 'missing'})
            continue
        verdicts = [findings[i]['finding'] for i in hits]
        # judge the strictest reading: a single false assertion among the overlapping findings counts
        order = {'false_conflict': 0, 'wrong_match': 1, 'safe': 2, 'exact': 3}
        cls = min((classify(e['truth'], v) for v in verdicts), key=lambda c: order[c])
        v = next((v for v in verdicts if classify(e['truth'], v) == cls), verdicts[0])
        fi = hits[verdicts.index(v)]
        rec = {'key': e['key'], 'tag': e['tag'], 'truth': e['truth'], 'verdict': v, 'cls': cls,
               'claim': findings[fi]['claim']}
        if v in ('match', 'conflict'):
            rec['cite'] = findings[fi].get('cite')
            rec['quote'] = findings[fi].get('quote')
        res['claims'].append(rec)
    for i, f in enumerate(findings):
        if i not in used and f.get('finding') in ('match', 'conflict'):
            res['unlabelled'].append({'claim': f['claim'], 'verdict': f['finding'], 'cite': f.get('cite')})
    return res


def summarize(results, label):
    L = []
    claims = [(r, c) for r in results for c in r['claims']]
    N = len(claims)
    cnt = collections.Counter(c['cls'] for _, c in claims)
    exact_rate = cnt['exact'] / N if N else 0
    bad = cnt['false_conflict'] + cnt['wrong_match']
    A = 40 * exact_rate
    B = 20 * max(0.0, 1 - 10 * bad / N) if exact_rate >= 0.5 else 0.0
    L.append('# Robustness run: %s\n' % label)
    L.append('Generated held-out cases: %d, labelled claims: %d. Ground truth comes from the generator world model.\n' % (len(results), N))
    L.append('| metric | value |\n|---|---|')
    L.append('| exact-correct | %d (%.1f%%) |' % (cnt['exact'], 100 * exact_rate))
    L.append('| safe-but-weak (not_settled/not_checkable where more was possible) | %d (%.1f%%) |' % (cnt['safe'], 100 * cnt['safe'] / N))
    L.append('| FALSE CONFLICTS | %d |' % cnt['false_conflict'])
    L.append('| wrong matches | %d |' % cnt['wrong_match'])
    L.append('| labelled claims with no finding emitted | %d |' % cnt['missing'])
    L.append('| conflict/match findings on unlabelled text | %d |' % sum(len(r['unlabelled']) for r in results))
    L.append('| crashes (non-zero exit) | %d |' % sum(r['crash'] for r in results))
    L.append('| invalid JSON | %d |' % sum(r['invalid_json'] for r in results))
    L.append('| schema violations | %d |' % sum((not r['schema_ok']) and not r['invalid_json'] for r in results))
    L.append('| quotes not found in cited file | %d |' % sum(r['quote_bad'] for r in results))
    L.append('| cites where the cited row/line does not contain the quote (CSV, VTT) | %d |' % sum(r['cite_row_bad'] for r in results))
    L.append('| total wall time | %.1f s (max %.2f s per case) |' % (sum(r['secs'] for r in results), max(r['secs'] for r in results)))
    L.append('\n**Illustrative point estimate only (my proxy for the stated weights, not the grader):** '
             'correct-findings %.1f/40, no-false-assertions %.1f/20 (proxy: 10%% bad rate = 0). '
             'Clock, robustness and README points are not estimated here.\n' % (A, B))
    L.append('\n## By family\n')
    L.append('| family | claims | exact | safe | missing | false conflict | wrong match |\n|---|---|---|---|---|---|---|')
    fam = collections.defaultdict(collections.Counter)
    for r, c in claims:
        fam[r['family']][c['cls']] += 1
        fam[r['family']]['n'] += 1
    for k, v in sorted(fam.items()):
        L.append('| %s | %d | %d | %d | %d | %d | %d |' % (k, v['n'], v['exact'], v['safe'], v['missing'],
                                                           v['false_conflict'], v['wrong_match']))
    L.append('\n## Variants with any false conflict or wrong match\n')
    var = collections.defaultdict(collections.Counter)
    for r, c in claims:
        var[(r['family'], r['variant'])][c['cls']] += 1
        var[(r['family'], r['variant'])]['n'] += 1
    L.append('| family / variant | claims | false conflict | wrong match | exact |\n|---|---|---|---|---|')
    for (f, v), cc in sorted(var.items()):
        if cc['false_conflict'] or cc['wrong_match']:
            L.append('| %s / %s | %d | %d | %d | %d |' % (f, v, cc['n'], cc['false_conflict'], cc['wrong_match'], cc['exact']))
    L.append('\n## Lowest exact-rate variants (yield problems)\n')
    L.append('| family / variant | claims | exact | safe | missing |\n|---|---|---|---|---|')
    rows = sorted(var.items(), key=lambda kv: kv[1]['exact'] / kv[1]['n'])[:12]
    for (f, v), cc in rows:
        L.append('| %s / %s | %d | %d | %d | %d |' % (f, v, cc['n'], cc['exact'], cc['safe'], cc['missing']))
    L.append('\n## Every false conflict / wrong match (first 40)\n')
    L.append('| case | claim | truth | tool said | cited |\n|---|---|---|---|---|')
    shown = 0
    for r, c in claims:
        if c['cls'] in ('false_conflict', 'wrong_match') and shown < 40:
            ci = c.get('cite') or {}
            L.append('| %s | %s | %s | %s | %s r%s |' % (r['id'], c.get('claim', c['key']), c['truth'], c['verdict'],
                                                       ci.get('file'), ci.get('row')))
            shown += 1
    return '\n'.join(L) + '\n', {'exact': cnt['exact'], 'safe': cnt['safe'], 'false_conflict': cnt['false_conflict'],
                                 'wrong_match': cnt['wrong_match'], 'missing': cnt['missing'], 'N': N}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', default=os.path.join(HERE, 'cases'))
    ap.add_argument('--out', default=os.path.join(HERE, 'results', 'latest'))
    ap.add_argument('--label', default='run')
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    results = []
    for name in sorted(os.listdir(a.cases)):
        d = os.path.join(a.cases, name)
        with open(os.path.join(d, 'truth.json')) as fh:
            truth = json.load(fh)
        results.append(score_case(d, truth))
    md, summary = summarize(results, a.label)
    with open(a.out + '.json', 'w') as fh:
        json.dump(results, fh)
    with open(a.out + '.md', 'w') as fh:
        fh.write(md)
    print(md)


if __name__ == '__main__':
    main()
