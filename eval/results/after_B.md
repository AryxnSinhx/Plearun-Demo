# Robustness run: after group B

Generated held-out cases: 269, labelled claims: 1445. Ground truth comes from the generator world model.

| metric | value |
|---|---|
| exact-correct | 1247 (86.3%) |
| safe-but-weak (not_settled/not_checkable where more was possible) | 171 (11.8%) |
| FALSE CONFLICTS | 27 |
| wrong matches | 0 |
| labelled claims with no finding emitted | 0 |
| conflict/match findings on unlabelled text | 0 |
| crashes (non-zero exit) | 0 |
| invalid JSON | 0 |
| schema violations | 0 |
| quotes not found in cited file | 0 |
| cites where the cited row/line does not contain the quote (CSV, VTT) | 0 |
| total wall time | 11.0 s (max 0.07 s per case) |

**Illustrative point estimate only (my proxy for the stated weights, not the grader):** correct-findings 34.5/40, no-false-assertions 16.3/20 (proxy: 10% bad rate = 0). Clock, robustness and README points are not estimated here.


## By family

| family | claims | exact | safe | missing | false conflict | wrong match |
|---|---|---|---|---|---|---|
| clocks | 378 | 319 | 53 | 0 | 6 | 0 |
| counts | 15 | 15 | 0 | 0 | 0 | 0 |
| formats | 432 | 362 | 70 | 0 | 0 | 0 |
| json | 108 | 108 | 0 | 0 | 0 | 0 |
| misleading | 68 | 48 | 0 | 0 | 20 | 0 |
| phrasing | 57 | 45 | 12 | 0 | 0 | 0 |
| timestamps | 327 | 290 | 36 | 0 | 1 | 0 |
| vtt | 60 | 60 | 0 | 0 | 0 | 0 |

## Variants with any false conflict or wrong match

| family / variant | claims | false conflict | wrong match | exact |
|---|---|---|---|---|
| clocks / big_unaligned | 54 | 6 | 0 | 37 |
| misleading / all_z_zone_ambiguity | 8 | 8 | 0 | 0 |
| misleading / naive_utc_dispatch | 8 | 8 | 0 | 0 |
| misleading / prev_day_same_time | 4 | 4 | 0 | 0 |
| timestamps / camera_iso_z | 27 | 1 | 0 | 23 |

## Lowest exact-rate variants (yield problems)

| family / variant | claims | exact | safe | missing |
|---|---|---|---|---|
| misleading / all_z_zone_ambiguity | 8 | 0 | 0 | 0 |
| misleading / naive_utc_dispatch | 8 | 0 | 0 | 0 |
| misleading / prev_day_same_time | 4 | 0 | 0 | 0 |
| phrasing / hrs_format | 3 | 0 | 3 | 0 |
| phrasing / range | 3 | 0 | 3 | 0 |
| phrasing / time_first | 3 | 0 | 3 | 0 |
| phrasing / wrong_time_first | 3 | 0 | 3 | 0 |
| clocks / big_unaligned | 54 | 37 | 11 | 0 |
| formats / notes_cp1252_nonascii | 27 | 20 | 7 | 0 |
| clocks / mid_unaligned | 54 | 42 | 12 | 0 |
| formats / notes_headerless | 27 | 21 | 6 | 0 |
| formats / notes_semicolon | 27 | 21 | 6 | 0 |

## Every false conflict / wrong match (first 40)

| case | claim | truth | tool said | cited |
|---|---|---|---|---|
| clocks_big_unaligned_0 | Officer Nguyen first observed the blue sedan at about 21:36 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_1 | Officer Brandt first observed the blue sedan at about 21:33 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_2 | Officer Brandt first observed the blue sedan at about 21:53 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_3 | Officer Patel first observed the blue sedan at about 21:57 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_4 | Officer Okafor first observed the blue sedan at about 20:44 | match | conflict | notes.csv r2 |
| clocks_big_unaligned_5 | Officer Brandt first observed the blue sedan at about 20:33 | match | conflict | notes.csv r2 |
| mis_all_z_0 | A 911 call reporting the incident was logged at 20:16 | match | conflict | dispatch.json r1 |
| mis_all_z_0 | A unit arrived on scene at 20:25 | match | conflict | dispatch.json r3 |
| mis_all_z_1 | A 911 call reporting the incident was logged at 22:28 | match | conflict | dispatch.json r1 |
| mis_all_z_1 | A unit arrived on scene at 22:38 | match | conflict | dispatch.json r3 |
| mis_all_z_2 | A 911 call reporting the incident was logged at 22:20 | match | conflict | dispatch.json r1 |
| mis_all_z_2 | A unit arrived on scene at 22:29 | match | conflict | dispatch.json r3 |
| mis_all_z_3 | A 911 call reporting the incident was logged at 22:11 | match | conflict | dispatch.json r1 |
| mis_all_z_3 | A unit arrived on scene at 22:19 | match | conflict | dispatch.json r3 |
| mis_naive_utc_0 | A 911 call reporting the incident was logged at 21:27 | match | conflict | dispatch.json r1 |
| mis_naive_utc_0 | A unit arrived on scene at 21:37 | match | conflict | dispatch.json r3 |
| mis_naive_utc_1 | A 911 call reporting the incident was logged at 22:06 | match | conflict | dispatch.json r1 |
| mis_naive_utc_1 | A unit arrived on scene at 22:16 | match | conflict | dispatch.json r3 |
| mis_naive_utc_2 | A 911 call reporting the incident was logged at 22:08 | match | conflict | dispatch.json r1 |
| mis_naive_utc_2 | A unit arrived on scene at 22:18 | match | conflict | dispatch.json r3 |
| mis_naive_utc_3 | A 911 call reporting the incident was logged at 20:44 | match | conflict | dispatch.json r1 |
| mis_naive_utc_3 | A unit arrived on scene at 20:54 | match | conflict | dispatch.json r3 |
| mis_prev_day_0 | A 911 call reporting the incident was logged at 22:00 | not_settled | conflict | dispatch.json r1 |
| mis_prev_day_1 | A 911 call reporting the incident was logged at 20:59 | not_settled | conflict | dispatch.json r1 |
| mis_prev_day_2 | A 911 call reporting the incident was logged at 21:51 | not_settled | conflict | dispatch.json r1 |
| mis_prev_day_3 | A 911 call reporting the incident was logged at 21:46 | not_settled | conflict | dispatch.json r1 |
| ts_camera_iso_z_0 | A unit was dispatched at 22:07 | match | conflict | dispatch.json r2 |
