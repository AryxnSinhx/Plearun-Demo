# Verified Findings: claim checker

    python3 plearun_cli.py REPORT RECORDS_DIR > findings.json     # stdlib only, offline
    make test                                                      # 80 tests, ~2 s

## How it works
1. **Load** (`loaders.py`): CSV (BOM, marker line, cp1252 fallback, quoted multi-line fields), JSON (a small
   parser that keeps each record's raw text), WebVTT (overlapping cues). Every row keeps its raw text.
2. **Parse the report** (`claims.py`): split into atomic claims (time, speed, zone, "N minutes after", count,
   everything else = `not_checkable`). Each `claim` is a verbatim slice of the report.
3. **Evidence** (`events.py`): rows become events (`call`, `dispatch`, `on_scene`, `stop`, `observed`) via one
   shared vocabulary used on both report and records. Duplicates, other-date rows and negated notes
   ("did not stop") are dropped. All timestamp formats become UTC intervals; `HH:MM` is a 59 s interval.
4. **Clocks** (`clocks.py`): offsets are estimated only from event kinds seen once in two sources.
5. **Judge** (`judge.py`), then **verify** (`pipeline.finalize`): a match/conflict is written only if its quote
   is a substring of the cited row's raw text; otherwise it becomes `not_settled`.

## Three hardest decisions
- **Asymmetric thresholds.** Match needs agreement under the tightest reading (tolerance 60 s, 120 s if hedged).
  Conflict needs disagreement under the loosest (tolerance + 180 s assumed skew + 120 s margin) *and* every
  source holding that event kind must hold exactly one and be far off. If two sources disagree: `not_settled`.
- **The camera log cannot refute a vehicle-specific speed** (no plate, it logs all traffic). So "58 mph" stays
  `not_settled` even though the nearest reading is 62; the officer's bodycam "58 in a 45" is the same person who
  wrote the report, so it is not independent. Camera speeds can match/conflict only if the report attributes
  the speed to the camera and exactly one reading falls in the window.
- **Alignment is strict:** at least 2 anchor kinds, consistent, offset known to within 30 s. On the sample
  nothing qualifies (one anchor per pair, minute-resolution notes), so no clock is shifted.

## What it gets wrong / assumptions to challenge
- Row numbering is a guess: CSV = physical line (marker and header count), JSON = 1-based object index, VTT = cue order.
- Zone-less times (notes, naive ISO, the report) are assumed local, in the most common explicit offset (-05:00).
- "First observed ~21:14" matches a note at 21:15 (inside the 120 s hedge); "first" is not verified.
- Regex claim parsing is English-only and misses unusual phrasing (it then yields `not_checkable`).
- Not built: the optional LLM path. I tried two small local models (see below) but did not integrate either, so the tool is fully deterministic and never calls an LLM.

## What breaks first on real records
Event vocabulary (a note that says "contact made" is invisible), naive timestamps that are really UTC, cameras
that log several vehicles per second, zone names/DST (only fixed offsets), and large CSVs held fully in memory
(200k rows: about 1 s).

## Robustness
Held-out evaluation on a synthetic generator (baseline 35 false conflicts, now 0; method, limits and numbers in
`docs/ROBUSTNESS.md`; rerun with `python3 eval/run.py`). Synthetic data from one author, not a guarantee.

## AI tools used
- **Claude (claude.ai chat), coding assistant.** I wrote the skeleton code myself; Claude then helped build on it: the robustness work (held-out evaluation harness in `eval/`, the fixes it drove, regression tests) and the finer handling of edge cases in the loaders, clocks and claim parsing.
- **ChatGPT, generalisation and architecture review.** Used to generalise the repo and to assess the architecture by throwing different edge cases at it. Those cases fed into the robustness work above.
- **Local LLMs, experiments only (not integrated).** I tested LLM integration myself with two small models, Llama 3.2 3B and Qwen 2.5 4B, to check that a local, no-internet setup is feasible. I did not integrate either into the tool; `mock_llm.py` is the unchanged stub from the starter pack.
