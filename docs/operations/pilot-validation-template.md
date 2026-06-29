# Debug Agent Pilot Validation Record

## Run Metadata

- Date:
- Operator:
- Environment:
- Backend URL:
- Lark spreadsheet:
- Batch IDs compared:
- Model configuration summary:
- `model_runner` locked: yes/no

## Required Evidence

- Production readiness JSON:
- Pilot gate JSON:
- Batch comparison CSV:
- Operations support bundle:
- Database backup location:
- Artifact retention dry-run output:
- Artifact cleanup execution, if any:

## Gate Thresholds

- Minimum completed samples:
- Minimum success rate:
- Maximum P95 latency:
- Maximum estimated cost units:
- Maximum model call errors:
- Maximum writeback failures:
- Maximum Lark operation failures:

## Results

- Completed samples:
- Best batch:
- Best batch success rate:
- Best batch P95 latency:
- Best batch estimated cost:
- Model call errors:
- Writeback failures:
- Lark operation failures:
- Artifact retention candidates:

## Decision

- Decision: pass / conditional pass / fail
- Rationale:
- Required follow-up:
- Approver:
- Approval time:

## Notes

- Do not approve pilot rollout from a single small successful batch.
- Do not compare meta agent configurations unless `model_runner` remains locked for source replay, baseline, targeted, and verification stages.
- Store database backups only in approved secure storage; the operations support bundle is redacted, but database backups are not.
