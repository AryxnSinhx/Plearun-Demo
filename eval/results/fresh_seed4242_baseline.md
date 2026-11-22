# Robustness run: FRESH seed 4242 x2: original code

Generated held-out cases: 538, labelled claims: 2890. Ground truth comes from the generator world model.

| metric | value |
|---|---|
| exact-correct | 2450 (84.8%) |
| safe-but-weak (not_settled/not_checkable where more was possible) | 361 (12.5%) |
| FALSE CONFLICTS | 79 |
| wrong matches | 0 |
| labelled claims with no finding emitted | 0 |
| conflict/match findings on unlabelled text | 0 |
| crashes (non-zero exit) | 0 |
| invalid JSON | 0 |
| schema violations | 0 |
| quotes not found in cited file | 0 |
| cites where the cited row/line does not contain the quote (CSV, VTT) | 0 |
| total wall time | 20.6 s (max 0.06 s per case) |

**Illustrative point estimate only (my proxy for the stated weights, not the grader):** correct-findings 33.9/40, no-false-assertions 14.5/20 (proxy: 10% bad rate = 0). Clock, robustness and README points are not estimated here.


## By family

| family | claims | exact | safe | missing | false conflict | wrong match |
|---|---|---|---|---|---|---|
| clocks | 756 | 631 | 113 | 0 | 12 | 0 |
| counts | 30 | 30 | 0 | 0 | 0 | 0 |
| formats | 864 | 736 | 128 | 0 | 0 | 0 |
| json | 216 | 216 | 0 | 0 | 0 | 0 |
| misleading | 136 | 56 | 24 | 0 | 56 | 0 |
| phrasing | 114 | 90 | 24 | 0 | 0 | 0 |
| timestamps | 654 | 571 | 72 | 0 | 11 | 0 |
| vtt | 120 | 120 | 0 | 0 | 0 | 0 |

## Variants with any false conflict or wrong match

| family / variant | claims | false conflict | wrong match | exact |
|---|---|---|---|---|
| clocks / big_unaligned | 108 | 12 | 0 | 70 |
| misleading / all_z_zone_ambiguity | 16 | 8 | 0 | 0 |
| misleading / called_for_backup | 8 | 8 | 0 | 0 |
| misleading / instruction_plus_evidence | 8 | 8 | 0 | 0 |
| misleading / limit_as_speed | 8 | 8 | 0 | 0 |
| misleading / naive_utc_dispatch | 16 | 8 | 0 | 0 |
| misleading / prev_day_same_time | 8 | 8 | 0 | 0 |
| misleading / witness_saw | 8 | 8 | 0 | 0 |
| timestamps / camera_iso_z | 54 | 11 | 0 | 37 |

## Lowest exact-rate variants (yield problems)

| family / variant | claims | exact | safe | missing |
|---|---|---|---|---|
| misleading / all_z_zone_ambiguity | 16 | 0 | 8 | 0 |
| misleading / called_for_backup | 8 | 0 | 0 | 0 |
| misleading / instruction_plus_evidence | 8 | 0 | 0 | 0 |
| misleading / limit_as_speed | 8 | 0 | 0 | 0 |
| misleading / naive_utc_dispatch | 16 | 0 | 8 | 0 |
| misleading / prev_day_same_time | 8 | 0 | 0 | 0 |
| misleading / witness_saw | 8 | 0 | 0 | 0 |
| phrasing / hrs_format | 6 | 0 | 6 | 0 |
| phrasing / range | 6 | 0 | 6 | 0 |
| phrasing / time_first | 6 | 0 | 6 | 0 |
| phrasing / wrong_time_first | 6 | 0 | 6 | 0 |
| misleading / near_duplicate | 16 | 8 | 8 | 0 |

## Every false conflict / wrong match (first 40)

| case | claim | truth | tool said | cited |
|---|---|---|---|---|
| clocks_big_unaligned_0 | Officer Patel first observed the blue sedan at about 20:53 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_1 | Officer Patel first observed the blue sedan at about 21:07 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_11 | Officer Lee first observed the blue sedan at about 20:53 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_3 | Officer Okafor first observed the blue sedan at about 20:17 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_4 | Officer Moreno first observed the blue sedan at about 20:05 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_5 | Officer Moreno first observed the blue sedan at about 22:20 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_5 | The driver stopped at 22:23 | match | conflict | notes.csv r3 |
| clocks_big_unaligned_6 | Officer Lee first observed the blue sedan at about 21:18 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_6 | The driver stopped at 21:20 | match | conflict | notes.csv r3 |
| clocks_big_unaligned_7 | Officer Nguyen first observed the blue sedan at about 20:47 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_8 | Officer Kowalski first observed the blue sedan at about 21:28 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_9 | Officer Nguyen first observed the blue sedan at about 22:23 | match | conflict | notes.csv r2 |
| mis_all_z_0 | A unit arrived on scene at 21:53 | match | conflict | dispatch.json r3 |
| mis_all_z_1 | A unit arrived on scene at 21:21 | match | conflict | dispatch.json r3 |
| mis_all_z_2 | A unit arrived on scene at 20:15 | match | conflict | dispatch.json r3 |
| mis_all_z_3 | A unit arrived on scene at 22:36 | match | conflict | dispatch.json r3 |
| mis_all_z_4 | A unit arrived on scene at 20:39 | match | conflict | dispatch.json r3 |
| mis_all_z_5 | A unit arrived on scene at 22:32 | match | conflict | dispatch.json r3 |
| mis_all_z_6 | A unit arrived on scene at 22:24 | match | conflict | dispatch.json r3 |
| mis_all_z_7 | A unit arrived on scene at 20:23 | match | conflict | dispatch.json r3 |
| mis_called_backup_0 | A 911 call reporting the incident was logged at 21:00 | not_settled | conflict | notes.csv r2 |
| mis_called_backup_1 | A 911 call reporting the incident was logged at 20:04 | not_settled | conflict | notes.csv r2 |
| mis_called_backup_2 | A 911 call reporting the incident was logged at 20:25 | not_settled | conflict | notes.csv r2 |
| mis_called_backup_3 | A 911 call reporting the incident was logged at 21:41 | not_settled | conflict | notes.csv r2 |
| mis_called_backup_4 | A 911 call reporting the incident was logged at 22:25 | not_settled | conflict | notes.csv r2 |
| mis_called_backup_5 | A 911 call reporting the incident was logged at 20:55 | not_settled | conflict | notes.csv r2 |
| mis_called_backup_6 | A 911 call reporting the incident was logged at 22:08 | not_settled | conflict | notes.csv r2 |
| mis_called_backup_7 | A 911 call reporting the incident was logged at 20:32 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_0 | The driver stopped at 22:00 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_1 | The driver stopped at 21:39 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_2 | The driver stopped at 21:18 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_3 | The driver stopped at 22:29 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_4 | The driver stopped at 22:06 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_5 | The driver stopped at 20:15 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_6 | The driver stopped at 22:26 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_7 | The driver stopped at 22:36 | not_settled | conflict | notes.csv r2 |
| mis_limit_as_speed_0 | Officer Brandt clocked the vehicle at 55 mph | not_settled | conflict | bodycam.vtt r1 |
| mis_limit_as_speed_1 | Officer Nguyen clocked the vehicle at 78 mph | not_settled | conflict | bodycam.vtt r1 |
| mis_limit_as_speed_2 | Officer Patel clocked the vehicle at 63 mph | not_settled | conflict | bodycam.vtt r1 |
| mis_limit_as_speed_3 | Officer Brandt clocked the vehicle at 72 mph | not_settled | conflict | bodycam.vtt r1 |
