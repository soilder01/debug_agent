# Architecture

The system has five core modules:

- Case management: imports and normalizes badcase data.
- Comparison: identifies answer/prediction deltas.
- Experiments: plans and runs reproducible debug recipes.
- Reports: generates evidence-backed root-cause summaries.
- Review UI: lets humans inspect, approve, edit, and reject conclusions.

All model calls are routed through adapters. Tests use deterministic adapters and recorded fixtures. Live adapters are integration-only and are never required for unit tests.