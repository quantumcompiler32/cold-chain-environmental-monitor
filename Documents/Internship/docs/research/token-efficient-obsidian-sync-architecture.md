# Token-Efficient Automation Architecture for a Local Obsidian Vault Sync System

## Primary-source facts

- OpenAI responses and chat completions expose `usage.input_tokens`, `usage.output_tokens`, `usage.total_tokens`, and `usage.input_tokens_details.cached_tokens`, so token accounting can be tracked directly from API responses and usage endpoints. Source: [OpenAI Responses API reference](https://platform.openai.com/docs/api-reference/responses-streaming/response/refusal/delta?lang=curl), [OpenAI Usage API reference](https://platform.openai.com/docs/api-reference/usage/audio_transcriptions_object).
- The Responses API supports `prompt_cache_key`, which is “used by OpenAI to cache responses for similar requests to optimize your cache hit rates,” and `prompt_cache_retention: "24h"` for extended prompt caching. Source: [OpenAI Responses API reference](https://platform.openai.com/docs/api-reference/responses-streaming/response/refusal/delta?lang=curl).
- OpenAI says `user` is deprecated in favor of `prompt_cache_key` for caching optimizations. Source: [OpenAI Responses API reference](https://platform.openai.com/docs/api-reference/responses-streaming/response/refusal/delta?lang=curl).
- Batch API requests are asynchronous, accept JSONL input, currently support a `24h` completion window, and return completions within 24 hours. Source: [OpenAI Batch API reference](https://platform.openai.com/docs/api-reference/batch/object?api-mode=responses), [OpenAI Files API reference](https://platform.openai.com/docs/api-reference/files?lang=ruby).
- OpenAI’s usage docs note that the Usage API provides granular usage data and a separate Costs endpoint, while batch usage is tracked in the API usage objects. Source: [OpenAI Usage API reference](https://platform.openai.com/docs/api-reference/usage/audio_transcriptions_object).
- OpenAI states that API data is not used to train or improve models unless explicitly opted in. It also states that abuse-monitoring logs are retained up to 30 days by default, and that extended prompt caching is not Zero Data Retention eligible. Source: [OpenAI data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint).
- Obsidian Vaults are folders on disk, and the Vault API exposes `getMarkdownFiles()`, `cachedRead()`, `read()`, `process()`, and file-modification events such as `create`, `delete`, `modify`, and `rename`. Source: [Obsidian Vault developer docs](https://docs.obsidian.md/Plugins/Vault), [Obsidian Events developer docs](https://docs.obsidian.md/Plugins/Events).
- Obsidian recommends `Vault.process()` over manual `read()`/`modify()` to avoid stale-write data loss, and for async workflows it recommends reading, doing async work, then using `process()` with a content equality check. Source: [Obsidian Vault developer docs](https://docs.obsidian.md/Plugins/Vault).

## Design rules for a token-efficient vault sync system

1. Deterministic local preprocessing first: normalize whitespace, sort metadata keys, strip noise, chunk by stable rules, and generate a stable diff before any model call. This keeps repeated requests structurally identical, which should improve cache reuse.
2. Send only incremental deltas. Use Obsidian file events (`create`, `modify`, `rename`, `delete`) to compute affected notes, then compare previous vs. current note state locally before deciding whether a model call is needed.
3. Keep the prompt prefix stable. Put invariant instructions, schema, and rubric in a fixed system/prompt block; inject only the changed note diff and a small amount of contextual metadata. Use a stable `prompt_cache_key` derived from the normalized vault state or job class.
4. Bound context aggressively. Prefer note-level or section-level slices over whole-vault dumps, and cap the number of linked neighbors included per request. The goal is to keep prompts small enough that cached prefixes are reused often.
5. Require structured outputs. Ask for JSON with explicit fields such as `action`, `target_path`, `confidence`, `reason`, and `evidence_spans`, so downstream automation can route or reject results without extra parsing calls.
6. Use confidence thresholds and staged fallback. High-confidence outputs can be applied automatically; medium-confidence outputs should queue for review; low-confidence outputs should be discarded or re-run with more context.
7. Enforce model-call budgets. Track tokens and request counts per run; cap daily automatic runs; and route overflow work to a slower on-demand or batch path.
8. Use batch processing for backlogs, not interactive sync. Batch is the right fit for nightly reconciliation or large re-indexing jobs, while small change sets should stay synchronous so freshness is preserved.
9. Prefer daily runs for predictable maintenance and on-demand runs for user-triggered edits. Daily runs should summarize drift, rebuild indexes, and refresh embeddings or annotations; on-demand runs should process only the current edit window.
10. Preserve auditability. Store the local diff, the model input hash, the `prompt_cache_key`, the response ID, token usage, and the final applied patch in an append-only log so you can reconstruct every automated change.

## Inferences

- The combination of stable diffs, fixed prompt prefixes, and `prompt_cache_key` should materially improve cache hit rate because the cache key can bucket semantically similar jobs while the visible prompt stays mostly constant.
- Incremental event-driven processing is likely cheaper than vault-wide scanning because Obsidian exposes file-level events and the Vault API can read only the files that changed.
- A two-lane design is likely best: a fast lane for single-note deltas and a batch lane for backlog reconciliation. This follows directly from Batch API’s asynchronous, 24-hour processing model and the need to preserve responsiveness for interactive edits.
- Daily automation is likely enough for low-risk indexing and housekeeping, while user-triggered jobs should handle urgent changes. This is an operational policy choice rather than a documented API requirement.
- Structured outputs plus confidence thresholds reduce downstream token use because they let the system decide locally whether another model pass is necessary instead of always re-asking the model to explain itself.

## Practical architecture sketch

1. Watch the vault for file events.
2. Normalize the changed note locally and compute a minimal diff.
3. Decide whether the change is small enough for the interactive lane.
4. Build a cache-stable request with:
   - fixed instructions,
   - the normalized diff,
   - a compact, deterministic context slice,
   - a stable `prompt_cache_key`,
   - a strict JSON output schema.
5. Accept, queue for review, or reject based on confidence.
6. Log token usage and the exact input/output pair for audit.
7. Reconcile remaining drift in a nightly batch job.

## Source links

- OpenAI Responses API reference: https://platform.openai.com/docs/api-reference/responses-streaming/response/refusal/delta?lang=curl
- OpenAI Usage API reference: https://platform.openai.com/docs/api-reference/usage/audio_transcriptions_object
- OpenAI Batch API reference: https://platform.openai.com/docs/api-reference/batch/object?api-mode=responses
- OpenAI Files API reference: https://platform.openai.com/docs/api-reference/files?lang=ruby
- OpenAI data controls: https://platform.openai.com/docs/models/default-usage-policies-by-endpoint
- Obsidian Vault developer docs: https://docs.obsidian.md/Plugins/Vault
- Obsidian Events developer docs: https://docs.obsidian.md/Plugins/Events
