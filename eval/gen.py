#!/usr/bin/env python3
"""Write the held-out cases to eval/cases/<id>/{report.txt,records/,truth.json}.
Usage: python3 eval/gen.py [--seed N] [--scale K]      (generator is deterministic for a given seed)"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cases import all_cases  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--scale', type=int, default=1)
    ap.add_argument('--out', default=os.path.join(HERE, 'cases'))
    a = ap.parse_args()
    shutil.rmtree(a.out, ignore_errors=True)
    cases = all_cases(a.seed, a.scale)
    for c in cases:
        d = os.path.join(a.out, c.id)
        os.makedirs(os.path.join(d, 'records'))
        with open(os.path.join(d, 'report.txt'), 'w', encoding='utf-8', newline='') as f:
            f.write(c.text)
        for name, data in c.files.items():
            with open(os.path.join(d, 'records', name), 'wb') as f:
                f.write(data)
        with open(os.path.join(d, 'truth.json'), 'w') as f:
            json.dump({'id': c.id, 'family': c.family, 'variant': c.variant, 'entries': c.entries,
                       'meta': c.meta}, f, indent=1)
    print('wrote %d cases (%d labelled claims) to %s' % (len(cases), sum(len(c.entries) for c in cases), a.out))


if __name__ == '__main__':
    main()
