# Local LLM Experiments for Plearun — Summary

## Purpose
We evaluated two local small language models to assess whether they could reliably interpret evidence and classify report claims. This was exploratory benchmarking, not part of the candidate's required deterministic implementation.

## Models and setup
- Llama 3.2 3B via Ollama
- Qwen 2.5 3B via Ollama
- Local Windows PC: Intel Core i5-8250U, 8 GB RAM
- Same four synthetic benchmark cases and benchmark harness/prompt structure
- Total: 19 claims

## Metrics
- Verdict accuracy: correct expected labels / all claims
- Per-case accuracy: correct / claims per case
- End-to-end latency: seconds per case and average
- Generation throughput: Ollama output token count divided by generation time
- Qualitative failure analysis: contradiction detection, identity inference, clock/source handling, missing evidence, overclaiming, and instruction/report influence

## Aggregate results

| Metric | Llama 3.2 3B | Qwen 2.5 3B |
|---|---:|---:|
| Correct claims | 13/19 | 14/19 |
| Accuracy | 68.4% | 73.7% |
| Average case latency | 78.47 s | 119.01 s |
| Mean generation throughput | ~6.45 tokens/s | ~6.45 tokens/s |

Qwen gained one correct claim (5.3 percentage points) but average case latency was about 51.6% higher.

## Per-case results

| Case | Claims | Llama | Qwen |
|---|---:|---:|---:|
| court_case_01 — identity/missing theft evidence | 5 | 3/5 (60%) | 4/5 (80%) |
| court_case_02 — clock offset, identity, witness, embedded instruction | 5 | 3/5 (60%) | 3/5 (60%) |
| contradiction_01 — direct conflict/source separation | 4 | 3/4 (75%) | 4/4 (100%) |
| missing_01 — missing evidence/overclaiming | 5 | 4/5 (80%) | 3/5 (60%) |

## Main observations

1. **Qwen was marginally more accurate on this small test.** It classified 14/19 correctly versus Llama's 13/19. Four cases are too small to claim general superiority.
2. **Qwen was slower.** Mean case time rose from 78.5 seconds to 119.0 seconds—about 52% slower.
3. **Absence of identity evidence was repeatedly misclassified as contradiction.** Both models sometimes treated “not independently identified” as evidence that the identity claim was false, instead of inconclusive.
4. **Clock reasoning was unreliable.** Models mishandled offsets, recorded vs. corrected times, or transferred a clock correction between sources. Clock math and offset application should remain deterministic.
5. **Evidence-source conflation occurred.** Evidence from different cameras, buildings, or logs could be treated as establishing the same event or identity.
6. **Administrative status was over-interpreted.** A “Delivered” status was sometimes treated as proof of physical receipt; badge use could be conflated with the badge owner being present.
7. **Direct contradiction detection was a relative strength for Qwen.** Qwen correctly identified the warehouse CCTV entry contradicting “no one entered after 18:00,” which Llama missed.
8. **Readable explanations did not guarantee correct reasoning.** The models could sound confident while making unsupported inferences or conflating evidence.

## Case observations

### court_case_01
Both models handled the basic entry, bag, and missing-inventory claims reasonably. Both incorrectly classified lack of independent identity evidence as contradiction.

### court_case_02
Both had issues linking identity, location, and time. Llama mishandled clock correction. Qwen performed some clock arithmetic but conflated buildings/times and accepted report assertions as conclusive.

### contradiction_01
Llama missed the explicit contradiction that CCTV showed entry after 18:00 and had source/clock attribution problems. Qwen correctly found the contradiction and correctly treated badge-owner identity as inconclusive, but its explanation incorrectly applied the access-control clock correction to CCTV.

### missing_01
Llama was overly cautious about the system's “Delivered” status. Qwen recognized the status but over-inferred personal receipt/physical taking from weak evidence. Both struggled to distinguish missing evidence from contradiction consistently.

## Conclusion / decision
The experiments suggest that small local LLMs can assist with natural-language interpretation and produce readable summaries, but are not dependable as Plearun's final evidence judge. Qwen's small accuracy gain does not offset its slower latency and persistent reasoning errors for the core workflow.

**Decision:** stop LLM integration work for the candidate submission and preserve these experiments as research notes. Prioritize the deterministic engine—conservative verdict logic, clock alignment, evidence-source separation, robust parsing, and avoiding false matches. If LLM use is reconsidered, keep it strictly optional and bounded by the evaluation rules (for example, selecting among candidate row IDs), with deterministic validation and a no-LLM fallback.

## Limitations
- Only four synthetic cases and 19 claims were tested; results are indicative, not statistically robust.
- Benchmark labels reflect the constructed cases and expected verdicts.
- Latency depends on prompt size, model loading, machine state, and Ollama settings.
- This benchmark evaluated end-to-end claim verdicting, not a dedicated extraction-only workflow.

## Raw files
- Llama results: `20261121_211648_llama3.2_3b.json` and `.csv`
- Qwen results: `20261122_000542_qwen2.5_3b.json` and `.csv`
- Benchmark harness: `ollama_llm_benchmark.zip`
