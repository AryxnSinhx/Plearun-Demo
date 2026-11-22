import unittest
from helpers import run, verdicts, HEADER
from plearun.claims import parse_report


class ConservativeContextInheritance(unittest.TestCase):
    CAMERA = (
        "timestamp,device,speed_mph,zone_mph\n"
        "2026-03-02T19:42:10-05:00,CAM-21,48,50\n"
    )
    NOTES = (
        "ID,Author,Note,Time\n"
        "N-1,Officer Morgan,Radar unit R-5 measured plate JXK-482 at 72 mph,19:42:12\n"
    )

    def test_speed_claim_inherits_immediately_preceding_observation_time_for_same_vehicle(self):
        report = (
            HEADER +
            "At 19:42, Officer Morgan observed a blue sedan bearing plate JXK-482.\n"
            "The sedan was travelling 72 mph.\n"
        )
        claims, _ = parse_report(report)
        speed = next(c for c in claims if c.kind == "speed")
        self.assertIsNotNone(speed.params["ctx"])
        self.assertEqual(speed.params["ctx"]["secs"], 19 * 3600 + 42 * 60)

        findings, _ = run(report, {"camera.csv": self.CAMERA, "notes.csv": self.NOTES})
        self.assertEqual(verdicts(findings)[1], "not_settled")

    def test_time_first_observation_with_date_suffix_is_recognized_and_inherited(self):
        report = (
            HEADER +
            "At 19:42 on March 2, 2026, Officer Morgan observed a blue sedan bearing plate JXK-482.\n"
            "The sedan was travelling 72 mph.\n"
        )
        claims, _ = parse_report(report)
        observed = next(c for c in claims if c.kind == "time")
        speed = next(c for c in claims if c.kind == "speed")
        self.assertEqual(observed.params.get("event"), "observed")
        self.assertIsNotNone(speed.params["ctx"])

    def test_no_inheritance_across_blank_paragraph(self):
        report = (
            HEADER +
            "At 19:42, Officer Morgan observed a blue sedan bearing plate JXK-482.\n\n"
            "The sedan was travelling 72 mph.\n"
        )
        claims, _ = parse_report(report)
        speed = next(c for c in claims if c.kind == "speed")
        self.assertIsNone(speed.params["ctx"])

    def test_no_inheritance_to_different_vehicle_class(self):
        report = (
            HEADER +
            "At 19:42, Officer Morgan observed a blue sedan bearing plate JXK-482.\n"
            "The truck was travelling 72 mph.\n"
        )
        claims, _ = parse_report(report)
        speed = next(c for c in claims if c.kind == "speed")
        self.assertIsNone(speed.params["ctx"])


if __name__ == "__main__":
    unittest.main()
