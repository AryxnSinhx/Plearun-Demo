import os
import unittest
from helpers import ROOT, analyse


class SampleSnapshot(unittest.TestCase):
    """The shipped sample must keep producing these decisions; each one is argued in the README."""

    @classmethod
    def setUpClass(cls):
        res, cls.notes = analyse(os.path.join(ROOT, 'reports/report_fictional_02.txt'),
                                 os.path.join(ROOT, 'records'))
        cls.f = {x['claim']: x for x in res['findings']}

    def test_911_call_matches_dispatch_despite_naive_timestamp(self):
        f = self.f['A 911 call reporting the incident was logged at 21:11']
        self.assertEqual((f['finding'], f['cite']['file'], f['cite']['row']), ('match', 'dispatch.json', 1))

    def test_stop_matches_notes_row_4(self):
        f = self.f['stopped around 21:16']
        self.assertEqual((f['finding'], f['cite']['file'], f['cite']['row']), ('match', 'notes_cp1252.csv', 4))

    def test_speed_is_not_settled_because_camera_disagrees_with_the_officer(self):
        self.assertEqual(self.f['travelling 58 mph']['finding'], 'not_settled')

    def test_relative_time_not_settled_without_aligned_clocks(self):
        self.assertEqual(self.f['a unit on scene roughly 2 minutes after the stop']['finding'], 'not_settled')

    def test_unverifiable_statements(self):
        for c in ('near mile marker 4', 'The driver pulled into the Harbor Gas lot',
                  'Officer Lee states the vehicle was the only car in the lane'):
            self.assertEqual(self.f[c]['finding'], 'not_checkable', c)

    def test_no_conflicts_on_the_sample(self):
        self.assertNotIn('conflict', [x['finding'] for x in self.f.values()])

    def test_every_match_cite_quote_is_in_the_row(self):
        for x in self.f.values():
            self.assertEqual('cite' in x, x['finding'] in ('match', 'conflict'))
            self.assertEqual('quote' in x, x['finding'] in ('match', 'conflict'))


if __name__ == '__main__':
    unittest.main()
