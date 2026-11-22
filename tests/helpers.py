import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from plearun.pipeline import analyse  # noqa: E402


def make_case(report, files):
    """Write a report and record files (name -> str or bytes) to a temp dir; return (report_path, records_dir)."""
    base = tempfile.mkdtemp(prefix='plearun_test_')
    records = os.path.join(base, 'records')
    os.makedirs(records)
    rp = os.path.join(base, 'report.txt')
    with open(rp, 'w', encoding='utf-8') as f:
        f.write(report)
    for name, content in files.items():
        mode = 'wb' if isinstance(content, bytes) else 'w'
        kw = {} if mode == 'wb' else {'encoding': 'utf-8', 'newline': ''}
        with open(os.path.join(records, name), mode, **kw) as f:
            f.write(content)
    return rp, records


def run(report, files):
    rp, rd = make_case(report, files)
    result, notes = analyse(rp, rd)
    return result['findings'], notes


def verdicts(findings):
    return [f['finding'] for f in findings]


HEADER = 'Incident 2026-03-02, Route 21 corridor.\n'
DISPATCH = ('{"events":[{"id":"D-1","type":"911_call","logged":"2026-03-02 21:10:19"},'
            '{"id":"D-2","type":"unit_on_scene","logged":"2026-03-02T21:17:19-05:00","unit":"L-12"},'
            '{"id":"D-3","type":"unit_dispatched","logged":1772504040000,"unit":"L-12"}]}')
