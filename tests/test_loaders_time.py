import unittest
from helpers import make_case, HEADER  # noqa: F401  (sets sys.path)
from plearun.timeutil import parse_stamp
from plearun.loaders import load_csv, load_json, load_vtt, load_records
import os


class Timestamps(unittest.TestCase):
    def test_epoch_seconds_and_millis_agree(self):
        self.assertEqual(parse_stamp(1772504040000).secs, parse_stamp('1772504040').secs)

    def test_iso_with_offset_is_absolute(self):
        a, b = parse_stamp('2026-03-02T21:14:00-05:00'), parse_stamp(1772504040000)
        self.assertEqual((a.kind, a.secs), ('abs', b.secs))

    def test_naive_and_time_of_day_are_flagged_not_guessed(self):
        self.assertEqual(parse_stamp('2026-03-02 21:10:19').kind, 'naive')
        t = parse_stamp('21:15')
        self.assertEqual((t.kind, t.secs, t.span), ('tod', 21 * 3600 + 15 * 60, 59.0))

    def test_garbage_is_none(self):
        for v in ('', 'abc', '25:99', '2026-13-45 10:00', True, None, 12, '99999999999999999999'):
            self.assertIsNone(parse_stamp(v), v)


class Loaders(unittest.TestCase):
    def files(self, files):
        return make_case('x', files)[1]

    def test_csv_rows_count_physical_lines_including_marker_and_header(self):
        d = self.files({'cam.csv': '\ufeff#MARK\r\ntimestamp,device,speed_mph,zone_mph\r\n'
                                   '2026-03-02T21:00:00-05:00,A,40,45\r\n'})
        rows = load_csv(os.path.join(d, 'cam.csv'), 'cam.csv')
        self.assertEqual([(r.row, r.raw) for r in rows], [(3, '2026-03-02T21:00:00-05:00,A,40,45')])

    def test_cp1252_notes_decode_and_keep_non_ascii(self):
        raw = 'ID,Author,Note,Time\r\nN-1,Lee,Caf\u00e9 \u2019lot\u2019 stop,21:16\r\n'.encode('cp1252')
        d = self.files({'n.csv': raw})
        (r,) = load_csv(os.path.join(d, 'n.csv'), 'n.csv')
        self.assertIn('Caf\u00e9 \u2019lot\u2019', r.raw)

    def test_quoted_multiline_note_is_one_row_with_start_line(self):
        d = self.files({'n.csv': 'ID,Author,Note,Time\nN-1,Lee,"line one\nline two",21:16\nN-2,Lee,ok,21:17\n'})
        rows = load_csv(os.path.join(d, 'n.csv'), 'n.csv')
        self.assertEqual([r.row for r in rows], [2, 4])
        self.assertIn('line two', rows[0].raw)

    def test_json_raw_slice_is_the_object_text(self):
        d = self.files({'d.json': '{"a":{"events":[{"id":"X","logged":"2026-03-02 21:00:00"},{"id":"Y","logged":5}]}}'})
        rows = load_json(os.path.join(d, 'd.json'), 'd.json')
        self.assertEqual(rows[0].raw, '{"id":"X","logged":"2026-03-02 21:00:00"}')
        self.assertEqual(len(rows), 1)       # 5 is not a plausible timestamp

    def test_vtt_overlapping_cues_both_kept_in_order(self):
        d = self.files({'b.vtt': 'WEBVTT\n\nNOTE hi\n\n00:00:00.000 --> 00:00:04.000\nA: one\n\n'
                                 '00:00:03.500 --> 00:00:07.000\nB: two 21:16\n'})
        rows = load_vtt(os.path.join(d, 'b.vtt'), 'b.vtt')
        self.assertEqual([r.row for r in rows], [1, 2])
        self.assertIsNotNone(rows[1].stamp)

    def test_malformed_file_is_skipped_with_a_warning(self):
        d = self.files({'bad.json': '{"events": [ {"a": ', 'ok.csv': 'a,b\n1,2\n'})
        rows, warnings = load_records(d)
        self.assertTrue(any('bad.json' in w for w in warnings))


if __name__ == '__main__':
    unittest.main()
