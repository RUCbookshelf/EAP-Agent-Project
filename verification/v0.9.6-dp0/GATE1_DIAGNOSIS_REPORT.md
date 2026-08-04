# v0.9.6-DP0-A Gate-1 Diagnosis Report

**Stage:** DP0-A - root-cause diagnosis (diagnosis only; no production
behavior changed)
**Branch / HEAD:** master / `01f6f11963e1c76fc7e9369a435ee5e6e8db04d1`
**Date:** 2026-08-04

## D0 failure summary (source-authoritative baseline)

Two bounded production-path preflight submissions failed identically:

```text
Attempt 0: ProviderOutputError - Invalid JSON: EOF while parsing (truncated)
Attempt 1: TimeoutError at the 30-second transport timeout
Final:     fallback_success (LocalDemo)
```

## Exact current request settings (verified against source)

```text
model:            deepseek-v4-pro
base URL:         https://api.deepseek.com
response_format:  {"type": "json_object"}
thinking:         ABSENT (provider default applies)
reasoning_effort: absent
temperature:      0.2
max_tokens:       1800 initial / 3600 correction
timeout:          30.0 s (hardcoded constructor default)
messages:         2 initial / 3 correction
system prompt:    feedback-prompt-v0.7.1 (1,859 chars; explicit JSON instruction)
user payload:     ~52,587 chars incl. full StructuredFeedback JSON schema
```

## Official documentation check (retrieved 2026-08-04)

DeepSeek API docs (Chat Completions API, Models & Pricing, Thinking Mode,
JSON Output) confirm:

```text
- deepseek-v4-pro is a supported model (OpenAI-format base URL);
- thinking mode DEFAULT IS ENABLED; disable syntax: {"thinking": {"type": "disabled"}};
- response_format {"type":"json_object"} is valid JSON Output and the request
  must also instruct JSON in the prompt (this request does);
- finish_reason="length" means generation exceeded max_tokens and content may
  be partially cut off;
- usage exposes prompt/completion/total tokens and reasoning_tokens;
- deepseek-v4-pro context 1M; max output maximum 384K (1800 is a request-level
  budget artifact, not a model cap).
```

## Diagnostic probes (frozen D0-01 essay, real credentials, direct calls)

Probe A - current production request settings:

```text
HTTP 200, 27.05s
finish_reason = length
completion_tokens = 1800 (exactly the requested max_tokens)
reasoning_tokens = 1300 of 1800 (72% of the output budget)
reasoning content present (6,334 chars) - not stored
JSON parse success this run (D0 runs were cut mid-string)
```

Probe B - single factor change: `thinking={"type": "disabled"}`:

```text
HTTP 200, 10.85s
finish_reason = stop
completion_tokens = 764 (0 reasoning tokens)
complete JSON (3,581 chars), parse success
```

Probe C was not run: Probe B restored completion, so the preregistered
one-factor sequence stopped there.

Correction-prompt inventory (no provider call): the correction request is
~54,950 chars vs ~54,446 initial (+~1%); prompt size is not the timeout
cause.

## Root-cause classification

```text
thinking-mode default:        PROVEN_PRIMARY
output token budget (1800):   PROVEN_CONTRIBUTING (finish_reason=length at the limit)
transport timeout (30s):      PROVEN_CONTRIBUTING (27.05s initial under thinking; D0 correction timeouts)
JSON-mode request compliance: RULED_OUT (compliant)
correction-prompt size:       RULED_OUT (+1% size)
SDK compatibility:            RULED_OUT (stdlib urllib; HTTP 200)
provider service interruption: RULED_OUT (consistent 200s)
schema complexity:            NOT_ASSESSABLE as an independent factor (producible in 764 tokens)
application parser behavior:  RULED_OUT (correct rejection of truncated input)
```

Primary root cause: **DeepSeek thinking mode runs by default** (official
default enabled) and the production request never disables it. Reasoning
tokens consume 72% of the 1800-token output budget, so the JSON truncates
(finish_reason=length) and fails StructuredFeedback validation; thinking-mode
latency then pushes the correction attempt past the 30-second timeout,
producing the LocalDemo fallback.

## Proposed DP0-B change set (exact, minimal)

```text
1. app/llm/deepseek.py:     add thinking={"type": "disabled"} to the request
2. app/llm/deepseek.py:     capture response id/model/finish_reason/usage/content
                            length; classify finish_reason=length as
                            provider_output_truncated; sanitized structured logs
3. app/config/settings.py:  deepseek_timeout = 60.0 (env DEEPSEEK_TIMEOUT)
4. app/services/factory.py: pass settings.deepseek_timeout to DeepSeekProvider
```

Unchanged: model `deepseek-v4-pro`; max_tokens 1800 (135% headroom on Probe B;
DP0-B records per-case headroom); prompt `feedback-prompt-v0.7.1`;
configuration version `config-v0.9.0`; StructuredFeedback schema; Diagnostic
Gate; router retry policy; fallback; 180s client timeout; no migration.

Bounds: per-call timeout 60s (30-90 policy); two-attempt budget <=120s (<150);
client boundary 180s; max_tokens unchanged and <=4096.

## Verification

```text
DP0-A diagnostic harness tests: 10 passed, exit 0
Existing provider/config/gate/validation suites: 84 passed, exit 0
Combined targeted run: 94 passed, 0 failed, 0 errors, exit 0
Full core and launcher: not run in DP0-A (per protocol)
Production source: no changes under app/ or migrations/; tests/contracts/ untouched
Development database: unchanged (62615C6C..., 14,352,384 B, mtime 12:54:07)
Research exports: 776 files / 388 dirs, zero delta
Provider call budget: 2 of 3 direct diagnostic calls used (Probe C not needed);
0 production submissions
```

## Gate

This report ends the diagnosis stage. No provider repair has been
implemented.

```text
DP0-A diagnosis is complete.

STOP: Do not implement the provider repair until the owner explicitly accepts
the proposed DP0-B change set.
```
