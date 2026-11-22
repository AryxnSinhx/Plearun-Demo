#!/usr/bin/env python3
"""Time and peak memory versus file size. Usage: python3 eval/perf.py [--rows 10000,100000,1000000]"""
import argparse
import json
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAUNCH = ("import resource,subprocess,sys,time;t=time.time();"
          "p=subprocess.run([sys.executable,sys.argv[1],sys.argv[2],sys.argv[3]],capture_output=True);"
          "print(p.returncode,round(time.time()-t,2),resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss//1024,len(p.stdout))")


def build(kind, n, d):
    rng = random.Random(1)
    rec = os.path.join(d, 'records')
    os.makedirs(rec)
    for f in os.listdir(os.path.join(ROOT, 'records')):
        if kind == 'camera' and f == 'camera_log.csv':
            continue
        if kind == 'notes' and f.startswith('notes'):
            continue
        if kind == 'dispatch' and f == 'dispatch.json':
            continue
        if kind == 'vtt' and f.endswith('.vtt'):
            continue
        open(os.path.join(rec, f), 'wb').write(open(os.path.join(ROOT, 'records', f), 'rb').read())
    if kind == 'camera':
        with open(os.path.join(rec, 'camera_log.csv'), 'w', newline='') as fh:
            fh.write('#PLEARUN SYNTHETIC\ntimestamp,device,speed_mph,zone_mph\r\n')
            for i in range(n):
                s = rng.randint(0, 86399)
                fh.write('2026-03-02T%02d:%02d:%02d-05:00,CAM-%02d,%d,45\r\n' % (s // 3600, s % 3600 // 60, s % 60,
                                                                                rng.randint(1, 9), rng.randint(20, 80)))
    elif kind == 'notes':
        with open(os.path.join(rec, 'notes.csv'), 'w', newline='') as fh:
            fh.write('ID,Author,Note,Time\r\n')
            for i in range(n):
                s = rng.randint(0, 86399)
                fh.write('N-%d,Officer X,"Routine check, nothing observed here",%02d:%02d\r\n' % (i, s // 3600, s % 3600 // 60))
    elif kind == 'dispatch':
        ev = [{'id': 'D-%d' % i, 'type': rng.choice(['911_call', 'unit_on_scene', 'unit_dispatched']),
               'logged': '2026-03-02 %02d:%02d:%02d' % (rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59)),
               'unit': 'L-%d' % rng.randint(1, 50)} for i in range(n)]
        json.dump({'export': {'events': ev}}, open(os.path.join(rec, 'dispatch.json'), 'w'))
    elif kind == 'vtt':
        with open(os.path.join(rec, 'bodycam.vtt'), 'w') as fh:
            fh.write('WEBVTT\n\n')
            for i in range(n):
                a = i * 2.0
                fh.write('%02d:%02d:%06.3f --> %02d:%02d:%06.3f\n[SYNTHETIC] Officer X: radio traffic %d\n\n'
                         % (a // 3600, a % 3600 // 60, a % 60, (a + 3) // 3600, (a + 3) % 3600 // 60, (a + 3) % 60, i))
    return os.path.join(ROOT, 'reports', 'report_fictional_02.txt'), rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', default='10000,100000,1000000')
    ap.add_argument('--kinds', default='camera,notes,dispatch,vtt')
    ap.add_argument('--out', default=os.path.join(HERE, 'results', 'perf_latest.md'))
    a = ap.parse_args()
    L = ['# Performance (wall seconds, peak RSS MB of the CLI process)\n', '| file kind | rows | exit | seconds | peak MB |', '|---|---|---|---|---|']
    for kind in a.kinds.split(','):
        for n in map(int, a.rows.split(',')):
            with tempfile.TemporaryDirectory() as d:
                rep, rec = build(kind, n, d)
                p = subprocess.run([sys.executable, '-c', LAUNCH, os.path.join(ROOT, 'plearun_cli.py'), rep, rec],
                                   capture_output=True, text=True, timeout=900)
                rc, secs, mb, _ = (p.stdout.split() + ['?'] * 4)[:4]
                L.append('| %s | %d | %s | %s | %s |' % (kind, n, rc, secs, mb))
                print(L[-1], flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
