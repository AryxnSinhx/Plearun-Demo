# Robustness run: BASELINE (commit 4f6834d, unchanged code)

Generated held-out cases: 269, labelled claims: 1445. Ground truth comes from the generator world model.

| metric | value |
|---|---|
| exact-correct | 1228 (85.0%) |
| safe-but-weak (not_settled/not_checkable where more was possible) | 182 (12.6%) |
| FALSE CONFLICTS | 35 |
| wrong matches | 0 |
| labelled claims with no finding emitted | 0 |
| conflict/match findings on unlabelled text | 0 |
| crashes (non-zero exit) | 0 |
| invalid JSON | 0 |
| schema violations | 0 |
| quotes not found in cited file | 0 |
| cites where the cited row/line does not contain the quote (CSV, VTT) | 0 |
| total wall time | 11.0 s (max 0.06 s per case) |

**Illustrative point estimate only (my proxy for the stated weights, not the grader):** correct-findings 34.0/40, no-false-assertions 15.2/20 (proxy: 10% bad rate = 0). Clock, robustness and README points are not estimated here.


## By family

| family | claims | exact | safe | missing | false conflict | wrong match |
|---|---|---|---|---|---|---|
| clocks | 378 | 314 | 58 | 0 | 6 | 0 |
| counts | 15 | 15 | 0 | 0 | 0 | 0 |
| formats | 432 | 368 | 64 | 0 | 0 | 0 |
| json | 108 | 108 | 0 | 0 | 0 | 0 |
| misleading | 68 | 28 | 12 | 0 | 28 | 0 |
| phrasing | 57 | 45 | 12 | 0 | 0 | 0 |
| timestamps | 327 | 290 | 36 | 0 | 1 | 0 |
| vtt | 60 | 60 | 0 | 0 | 0 | 0 |

## Variants with any false conflict or wrong match

| family / variant | claims | false conflict | wrong match | exact |
|---|---|---|---|---|
| clocks / big_unaligned | 54 | 6 | 0 | 32 |
| misleading / all_z_zone_ambiguity | 8 | 4 | 0 | 0 |
| misleading / called_for_backup | 4 | 4 | 0 | 0 |
| misleading / instruction_plus_evidence | 4 | 4 | 0 | 0 |
| misleading / limit_as_speed | 4 | 4 | 0 | 0 |
| misleading / naive_utc_dispatch | 8 | 4 | 0 | 0 |
| misleading / prev_day_same_time | 4 | 4 | 0 | 0 |
| misleading / witness_saw | 4 | 4 | 0 | 0 |
| timestamps / camera_iso_z | 27 | 1 | 0 | 23 |

## Lowest exact-rate variants (yield problems)

| family / variant | claims | exact | safe | missing |
|---|---|---|---|---|
| misleading / all_z_zone_ambiguity | 8 | 0 | 4 | 0 |
| misleading / called_for_backup | 4 | 0 | 0 | 0 |
| misleading / instruction_plus_evidence | 4 | 0 | 0 | 0 |
| misleading / limit_as_speed | 4 | 0 | 0 | 0 |
| misleading / naive_utc_dispatch | 8 | 0 | 4 | 0 |
| misleading / prev_day_same_time | 4 | 0 | 0 | 0 |
| misleading / witness_saw | 4 | 0 | 0 | 0 |
| phrasing / hrs_format | 3 | 0 | 3 | 0 |
| phrasing / range | 3 | 0 | 3 | 0 |
| phrasing / time_first | 3 | 0 | 3 | 0 |
| phrasing / wrong_time_first | 3 | 0 | 3 | 0 |
| misleading / near_duplicate | 8 | 4 | 4 | 0 |

## Every false conflict / wrong match (first 40)

| case | claim | truth | tool said | cited |
|---|---|---|---|---|
| clocks_big_unaligned_0 | Officer Nguyen first observed the blue sedan at about 21:36 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_1 | Officer Brandt first observed the blue sedan at about 21:33 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_2 | Officer Brandt first observed the blue sedan at about 21:53 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_3 | Officer Patel first observed the blue sedan at about 21:57 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_4 | Officer Okafor first observed the blue sedan at about 20:44 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_5 | Officer Brandt first observed the blue sedan at about 20:33 | match | conflict | notes.csv r2 |
| mis_all_z_0 | A unit arrived on scene at 20:25 | match | conflict | dispatch.json r3 |
| mis_all_z_1 | A unit arrived on scene at 22:38 | match | conflict | dispatch.json r3 |
| mis_all_z_2 | A unit arrived on scene at 22:29 | match | conflict | dispatch.json r3 |
| mis_all_z_3 | A unit arrived on scene at 22:19 | match | conflict | dispatch.json r3 |
| mis_called_backup_0 | A 911 call reporting the incident was logged at 20:51 | not_settled | conflict | notes.csv r2 |
| mis_called_backup_1 | A 911 call reporting the incident was logged at 21:28 | not_settled | conflict | notes.csv r2 |
| mis_called_backup_2 | A 911 call reporting the incident was logged at 21:15 | not_settled | conflict | notes.csv r2 |
| mis_called_backup_3 | A 911 call reporting the incident was logged at 20:21 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_0 | The driver stopped at 20:25 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_1 | The driver stopped at 20:15 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_2 | The driver stopped at 21:02 | not_settled | conflict | notes.csv r2 |
| mis_injection_evidence_3 | The driver stopped at 21:33 | not_settled | conflict | notes.csv r2 |
| mis_limit_as_speed_0 | Officer Kowalski clocked the vehicle at 48 mph | match | conflict | bodycam.vtt r1 |
| mis_limit_as_speed_1 | Officer Kowalski clocked the vehicle at 61 mph | match | conflict | bodycam.vtt r1 |
| mis_limit_as_speed_2 | Officer Nguyen clocked the vehicle at 66 mph | match | conflict | bodycam.vtt r1 |
| mis_limit_as_speed_3 | Officer Brandt clocked the vehicle at 68 mph | match | conflict | bodycam.vtt r1 |
| mis_naive_utc_0 | A unit arrived on scene at 21:37 | match | conflict | dispatch.json r3 |
| mis_naive_utc_1 | A unit arrived on scene at 22:16 | match | conflict | dispatch.json r3 |
| mis_naive_utc_2 | A unit arrived on scene at 22:18 | match | conflict | dispatch.json r3 |
| mis_naive_utc_3 | A unit arrived on scene at 20:54 | match | conflict | dispatch.json r3 |
| mis_prev_day_0 | A 911 call reporting the incident was logged at 22:00 | not_settled | conflict | dispatch.json r1 |
| mis_prev_day_1 | A 911 call reporting the incident was logged at 20:59 | not_settled | conflict | dispatch.json r1 |
| mis_prev_day_2 | A 911 call reporting the incident was logged at 21:51 | not_settled | conflict | dispatch.json r1 |
| mis_prev_day_3 | A 911 call reporting the incident was logged at 21:46 | not_settled | conflict | dispatch.json r1 |
| mis_witness_saw_0 | Officer Kowalski first observed the blue sedan at about 21:57 | not_settled | conflict | notes.csv r2 |
| mis_witness_saw_1 | Officer Okafor first observed the blue sedan at about 20:13 | not_settled | conflict | notes.csv r2 |
| mis_witness_saw_2 | Officer Nguyen first observed the blue sedan at about 21:55 | not_settled | conflict | notes.csv r2 |
| mis_witness_saw_3 | Officer Lee first observed the blue sedan at about 20:52 | not_settled | conflict | notes.csv r2 |
| ts_camera_iso_z_0 | A unit was dispatched at 22:07 | match | conflict | dispatch.json r2 |
