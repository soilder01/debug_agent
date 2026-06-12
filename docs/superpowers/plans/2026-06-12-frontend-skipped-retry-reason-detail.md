# Frontend Skipped Retry Reason Detail

## Goal

Use the backend skipped audit error message as the retry reason so operators see the concrete missing prerequisite.

## Scope

- For skipped audits, render `error_message` as the retry reason when present.
- Keep the fallback `missing prerequisites` when skipped audits have no error message.
- Preserve failed and succeeded retry reason behavior.

## TDD Steps

1. RED: Update skipped audit retry reason test to expect the concrete backend error.
2. GREEN: Pass audit error message into the retry reason helper.
3. VERIFY: Run focused frontend test, full verification, diagnostics, whitespace check, and secret scan.
