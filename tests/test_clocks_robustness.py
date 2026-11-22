import json
import os
import subprocess
import sys
import time
import unittest
from helpers import run, verdicts, make_case, HEADER, ROOT, DISPATCH
from plearun.pipeline import finalize
from plearun.claims import Claim
from plearun.judge import Verdict
from plearun.loaders import Row


def dispatch(offset_s):
    """911 call at 21:10:00 and unit on scene at 21:20:00, in a clock running offset_s ahead."""
    def t(h, m, s):
        total = h * 3600 + m * 60 + s + offset_s
        return '2026-03-02T%02d:%02d:%02d-05:00' % (total // 3600, total % 3600 // 60, total % 60)
    return json.dumps({'events': [{'id': 1, 'type': '911_call', 'logged': t(21, 10, 0)},
                                  {'id': 2, 'type': 'unit_on_scene', 'logged': t(21, 20, 0), 'unit': 'L'},
                                  {'id': 3, 'type': 'unit_dispatched', 'logged': t(21, 12, 0), 'unit': 'L'}]})


class ClockAlignment(unittest.TestCase):
    def notes(self, rows):
        return 'ID,Author,Note,Time\r\n' + ''.join('%s\r\n' % r for r in rows)

    def test_two_consistent_anchors_align_the_clocks(self):
        # notes use exact HH:MM:SS and run 40 s behind dispatch on both shared events
        n = self.notes(['N1,Dispatch,Unit dispatched to location,21:11:20', 'N2,Lee,Unit arrived on scene,21:19:20',
                        'N3,Lee,Stopped at lot,21:16:00'])
        report = HEADER + 'The driver stopped at 21:16. A unit on scene roughly 3 minutes after the stop.'
        f, notes = run(report, {'d.json': dispatch(0), 'n.csv': n})
        self.assertFalse([x for x in notes if 'unaligned' in x])
        # on-scene 21:20:00 vs stop 21:16:00 (notes clock 21:16:00 -> 21:16:40 on dispatch) = 3:20 -> within the 45 s tolerance of 'roughly 3 minutes'
        self.assertEqual(f[1]['finding'], 'match')

    def test_inconsistent_anchors_leave_clocks_unaligned(self):
        n = self.notes(['N1,Dispatch,Unit dispatched to location,21:11:00', 'N2,Lee,Unit arrived on scene,21:25:00'])
        _, notes = run(HEADER + 'A 911 call was logged at 21:10.', {'d.json': dispatch(0), 'n.csv': n})
        self.assertTrue(any('disagree' in x for x in notes))

    def test_minute_resolution_notes_cannot_align_a_clock(self):
        n = self.notes(['N1,Dispatch,Unit dispatched to location,21:12', 'N2,Lee,Unit arrived on scene,21:20'])
        _, notes = run(HEADER + 'A 911 call was logged at 21:10.', {'d.json': dispatch(0), 'n.csv': n})
        self.assertTrue(any('within' in x for x in notes))


class QuoteVerification(unittest.TestCase):
    def test_quote_not_in_row_is_downgraded_and_stripped(self):
        row = Row('f.csv', 2, 'a,b,c', 'notes', 'notes:f.csv', None, 'x', {})

        class V(Verdict):
            pass
        import plearun.pipeline as pl
        original = pl.make_quote
        pl.make_quote = lambda r, n=None: 'text that is not in the row'
        try:
            out = finalize(Claim('c', 0, 1, 'time'), Verdict('match', row))
        finally:
            pl.make_quote = original
        self.assertEqual(out, {'claim': 'c', 'finding': 'not_settled'})


class Robustness(unittest.TestCase):
    def test_empty_inputs(self):
        self.assertEqual(run('', {})[0], [])
        self.assertEqual(verdicts(run(HEADER + 'A 911 call was logged at 21:11.', {})[0]), ['not_settled'])

    def test_large_camera_log_is_fast(self):
        lines = ['#M', 'timestamp,device,speed_mph,zone_mph']
        for i in range(200000):
            lines.append('%d,CAM-%d,%d,45' % (1772500000000 + i * 1000, i % 5, 30 + i % 40))
        t = time.time()
        f, _ = run(HEADER + 'The camera recorded 55 mph at 21:14. A 911 call was logged at 21:11.',
                   {'c.csv': '\r\n'.join(lines) + '\r\n', 'd.json': DISPATCH})
        self.assertLess(time.time() - t, 15)
        self.assertEqual(len(f), 2)

    def test_cli_prints_only_json_on_stdout(self):
        rp, rd = make_case(HEADER + 'A 911 call was logged at 21:40.', {'d.json': DISPATCH})
        p = subprocess.run([sys.executable, os.path.join(ROOT, 'plearun_cli.py'), rp, rd],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)['findings'][0]['finding'], 'conflict')

    def test_cli_usage_error(self):
        p = subprocess.run([sys.executable, os.path.join(ROOT, 'plearun_cli.py')], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)


if __name__ == '__main__':
    unittest.main()
