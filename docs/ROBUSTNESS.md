# Robustness evaluation

Labels used: **[measured]** = produced by a run whose output is stored in `eval/results/`; **[reasoned]** = argued
from the code, not tested; **[assumption]** = a choice made without information.

## What this is, and what it is not
A held-out evaluation on **my own synthetic generator** (`eval/`). It is not a guarantee about Plearun's hidden
cases. The same assistant that wrote the tool also wrote the generator, so blind spots can be shared; the
mitigations were (1) the generator imports nothing from `plearun/`, (2) truth labels come from a world model (true
event times, clock offsets, who said what), never from tool output, (3) metamorphic tests that need no labels, and
(4) a second seed generated after the fixes were frozen.

## Method
- `python3 eval/gen.py` writes 269 cases (1,445 labelled claims): clock offsets 0-10 min with and without anchors,
  file formats (BOM, marker line, CRLF/LF/CR, cp1252 with non-ASCII, UTF-16, `;` and tab delimiters, headerless,
  shuffled rows), timestamp styles (epoch s/ms, ISO with offset, `Z`, naive, time-of-day, midnight crossing), JSON
  layouts, WebVTT variants, counts, claim phrasings, and misleading records (limit sign as speed, "called for
  backup", witness "saw", camera glitch values, previous-evening rows, instruction-like text, negation, naive-UTC and
  all-`Z` exports, near-duplicate rows).
- Truth classes: `match` (claim true), `conflict` (wrong by >= 15 min, more than any offset generated),
  `not_settled` (records cannot decide), `not_checkable`.
- `python3 eval/run.py` runs the real CLI per case, validates JSON and schema, checks every quote independently
  against the cited file (and the cited CSV line / VTT cue), and scores per claim: exact, safe-but-weak, false
  conflict, wrong match.
- `python3 eval/meta.py`: 346 transformed runs (CRLF/LF, shuffled rows, duplicated rows, unrelated noise rows,
  camera timestamp format) that must not change any finding.
- `python3 eval/perf.py`: time and peak memory for 10k / 100k / 1M rows per file kind.
- Baseline was recorded on the **unchanged** commit `4f6834d` before any code change
  (`docs/robustness_baseline.md`); each fix is its own commit with a regression test.

## Results [measured]
| | baseline | final |
|---|---|---|
| exact-correct (269 cases, 1,445 claims) | 85.0% | 87.9% |
| safe-but-weak | 12.6% | 12.1% |
| **false conflicts** | **35** | **0** |
| wrong matches | 0 | 0 |
| crashes / invalid JSON / schema violations / bad quotes | 0 | 0 |
| fresh seed 4242 (538 cases, 2,890 claims): false conflicts | 79 | 0 |
| fresh seed 4242: exact-correct | 84.8% | 87.8% |
| metamorphic invariance violations (346 runs) | 1 | 0 |
| unit tests | 44 | 80 |

The baseline's 35 false conflicts, by cause: limit number read as a speed (4), "called for backup" read as the 911
call (4), witness "saw" read as the officer's observation (4), instruction-like row used as evidence (4), previous
evening's row at the same time of day (4), naive-UTC dispatch export (4), all-`Z` export against local report times
(4), unaligned source 10 min off (6), camera file in `Z` timestamps (1). The 999 mph camera glitch gave the one
metamorphic violation. The hardened code has none of them on either seed.

**Read the table honestly:** the fixes removed false conflicts; they added little recall (+2.9 points, almost all
from the time-first phrasing fix). The remaining 12.1% safe-but-weak is mostly by design (below).

## What was changed (each with a regression test)
1. Numbers next to *limit / zone / posted* are never speeds; speeds outside (0, 200] and zones that are not
   multiples of 5 are ignored.
2. Loose wording ("called", "saw") is weak evidence and is never used for a conflict or a clock anchor; `observed`
   events must come from the named officer.
3. Rows whose text tries to instruct the tool are quarantined; same-unit near-duplicates (within seconds) merge.
4. Midnight: a claimed early-morning (or late-evening) time is also tried on the neighbouring day; a conflict must
   hold under every reading. Previous-evening rows no longer count as the incident's evidence.
5. A gap that is a whole number of hours (timezone or UTC-vs-local mix-up) is never a conflict; local zone is voted
   per file so a 1M-row camera export cannot outvote the dispatch export.
6. Unaligned sources get a skew allowance of at least 180 s, widened (to at most 900 s) when sources visibly
   disagree; an aligned group keeps 90 s for its own reference clock.
7. Loading: UTF-16 (with or without BOM), delimiter and headerless detection, streaming CSV, per-file
   "rows read / rows usable" notes on stderr.
8. Time-first sentences ("At 21:14, Officer Lee observed ...") are parsed as one claim. A first version of this fix
   judged the tail of a range ("between 21:00 **and 21:10** the driver was stopped") by its endpoint; the
   evaluation caught it (3 unlabelled findings), and the fix now requires a lead word such as "at". Regression tests
   cover both.

## Performance [measured, sandbox, not your laptop]
| rows | camera | notes | dispatch | vtt |
|---|---|---|---|---|
| 100k | 1.2 s / 119 MB | 2.4 s / 140 MB | 2.4 s / 183 MB | 2.5 s / 130 MB |
| 1M | 16 s / 977 MB | 24 s / 1.1 GB | 24 s / 1.6 GB | 29 s / 1.2 GB |

Memory grows about 1 KB per row (rows keep their raw text so quotes stay verifiable). 1M rows is workable but would
be tight on an 8 GB machine. The hardened loaders are slightly slower than the originals on some 1M-row files
(for example notes 17 s to 24 s). I did not optimise further.

## Known limits (not fixed, not hidden)
- **Single source with a large clock offset** [measured]: if only one record holds an event and nothing else can
  reveal its clock, a note 10 min from the claimed time still gives `conflict` (a 5 min gap gives `not_settled`;
  threshold is about tolerance + skew + margin = 6 min). That is indistinguishable from a wrong claim; the trade-off
  is the constant `MIN_SKEW`.
- **Camera zero-speed rows as stop anchors (planned P1) were not built** [assumption]: the camera has no vehicle id,
  so a zero reading may be another vehicle, and using it to shift a clock risks a confident wrong conflict.
- **Not handled:** `2116 hrs` times, "between X and Y" ranges (safe: not judged), non-ASCII officer names
  (the name regex is ASCII, so the officer constraint degrades to safe `not_settled`), several incidents on one
  night without an incident id, DST and named zones, event vocabulary the generator never used.
- **Row numbering** is my convention (CSV physical line, JSON 1-based object index, VTT cue number). The generator
  only verifies that the cited CSV line / VTT cue really contains the quote; whether the grader numbers rows the
  same way is untested.
- All numbers are on synthetic data from one author. The illustrative points proxy printed by `eval/run.py` is my
  own stand-in for the stated weights, not the grader.

## Reproduce
```
make test                                   # 80 tests, offline, ~2 s
python3 eval/gen.py && python3 eval/run.py  # held-out run (seed 7)
python3 eval/gen.py --seed 4242 --scale 2 --out /tmp/fresh && python3 eval/run.py --cases /tmp/fresh --out /tmp/r
python3 eval/meta.py; python3 eval/perf.py
```
