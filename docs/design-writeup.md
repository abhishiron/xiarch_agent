# Design write-up

## Problem

Research any company by name, using only live web data, and produce a structured,
sourced competitive-landscape brief — with visible planning, real tool use, and graceful
failure handling. No dataset is provided; everything is fetched at inference time.

## Architecture & tool orchestration

`Planner` (Groq) turns a company name into a 6-step plan, falling back to a deterministic
plan if the call fails or returns an invalid tool sequence. `Agent` runs that plan as a
bounded ReAct loop (max 10 iterations): per step it asks Groq for a brief "thought"
(narrative only — the tool actually called always follows the validated plan, not
free-form LLM output, trading flexibility for predictability), executes it via `Executor`,
and on failure calls `recover()`. Every tool shares one contract —
`BaseTool.execute(input) -> {success, data?, error?}` — so the executor validates any
tool's result the same way; `report_writer` is itself a tool, so the final write is
visible in the trace and testable without network credentials. Hand-rolled rather than
LangChain/CrewAI: a 6-step workflow doesn't need a framework between decisions and
effects, and owning the loop keeps failures traceable to one place.

## Failure / recovery strategy

Two layers. Tools retry transient errors up to 3x with backoff (`tools/base.py::retry`).
If a tool still fails, the agent logs it, asks Groq for retry/skip/alternative (falling
back to a deterministic "untried search-result URL" rule if *that* call is itself
rate-limited — this fired for real in `transcripts/run_2_stripe_failure_recovery.md`),
logs the decision and reasoning, retries, and logs the outcome. With no recovery
possible, the plan continues and the report states the evidence gap rather than
inventing content. `--simulate-failure` makes the scraper-failure path reproducible.

## Bugs found and fixed live during this session

- **Source-relevance filter.** `_first_source_url` had `"stripe.com" in url or url` —
  the trailing `or url` made it true for *any* URL, and was hardcoded to Stripe. With
  "official" in search queries, the agent scraped/cited a dictionary definition of
  "official" instead of the company's site. Fixed to require the result actually mention
  the company, prefer its own domain, and generalize — covered by `tests/test_agent.py`,
  verified live for Stripe and Adyen.
- **Windows console crash.** Rich's legacy renderer encodes via cp1252, which can't
  represent Unicode the LLM routinely outputs (non-breaking hyphens, curly quotes),
  crashing every such log line. Fixed via UTF-8 stdout/stderr reconfiguration.
- **Unbounded prompt growth.** `think()`/`recover()` serialized the entire run memory
  into every prompt uncapped, regularly exceeding Groq's 8,000 TPM limit (`413`, visible
  in every run). Fixed by truncating to 4,000 chars, matching the pattern already used
  for the analysis-evidence prompt.
- **Silent recovery.** The recovery decision was computed but never logged. Added
  explicit `Tool failure detected` / `Recovery decision` / `Retry succeeded` log lines.

## Limitations & what I'd improve with more time

The five analysis sub-tasks (summarize/products/competitors/developments/SWOT) are five
separate Groq calls each re-sending the full evidence blob — the biggest driver of the
token pressure above, and it burned through Groq's free daily quota during this
session's live testing (`transcripts/run_3_adyen_generalization.md`: every analysis call
failed for that reason, real and undisguised). I'd batch these into one call returning a
structured JSON object with all five keys (~5x fewer tokens). I'd also add evaluation
fixtures, parallel retrieval where order doesn't matter, and cached/vector memory — the
current design is deliberately sequential and single-run to keep the trace legible.
