"""Glue: report + records dir -> findings. Also the single place where quotes are verified."""
import json
import os
import sys

from .claims import parse_report
from .clocks import estimate
from .events import Evidence, infer_context
from .judge import Judge, make_quote
from .loaders import load_records, read_text


def finalize(claim, verdict):
    """Rule 1: a match or conflict is written only if its quote is a real, non-empty substring of the
    cited row's raw text. Anything else is downgraded to not_settled (and loses cite and quote)."""
    out = {'claim': claim.text, 'finding': verdict.finding}
    if verdict.finding in ('match', 'conflict'):
        row = verdict.row
        quote = make_quote(row, verdict.needle) if row is not None else None
        if not row or not quote or quote not in row.raw:
            out['finding'] = 'not_settled'
            return out
        out['cite'] = {'file': row.file, 'row': row.row}
        out['quote'] = quote
    return out


def analyse(report_path, records_dir):
    text = read_text(report_path)
    claims, report_date = parse_report(text)
    rows, warnings = load_records(records_dir)
    ctx = infer_context(rows, report_date)
    evidence = Evidence(rows, ctx)
    clocks = estimate(evidence)
    if evidence.quarantined:
        warnings.append('quarantined %d row(s) whose text tries to instruct the tool: %s' % (
            len(evidence.quarantined), ', '.join('%s:%s' % (r.file, r.row) for r in evidence.quarantined[:5])))
    judge = Judge(evidence, clocks, ctx)
    findings = []
    for c in claims:
        try:
            findings.append(finalize(c, judge.evaluate(c)))
        except Exception as exc:                      # a bug on one claim must never become a wrong finding
            warnings.append('claim %r: %s' % (c.text, exc))
            findings.append({'claim': c.text, 'finding': 'not_settled'})
    return {'findings': findings}, warnings + clocks.notes


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print('usage: python3 plearun_cli.py REPORT RECORDS_DIR > findings.json', file=sys.stderr)
        return 2
    report, records = argv
    if not os.path.isfile(report) or not os.path.isdir(records):
        print('REPORT must be a file and RECORDS_DIR a directory', file=sys.stderr)
        return 2
    result, notes = analyse(report, records)
    for n in notes:
        print('note: ' + n, file=sys.stderr)
    out = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    sys.stdout.buffer.write(out.encode('utf-8'))
    return 0
