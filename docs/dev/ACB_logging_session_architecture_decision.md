Save the following file as `docs/dev/ACB_logging_session_architecture_decision.md`.

```markdown
# File: docs/dev/ACB_logging_session_architecture_decision.md
# Path: /d/Projects/autocalbridge/docs/dev/ACB_logging_session_architecture_decision.md
# Purpose: Decision record for AutoCalBridge session context and logging architecture.
# Date: 2026-08-26
# Status: Approved decision rationale

---

## 1. Context

1.1. Calibration traceability requires every action to be attributable to a session, operator, and supervisor.

1.2. Existing logging is fragmented between `security/logger.py` and `src/utils/logger.py`.

1.3. No session identity, structured audit trail, or clear separation between operational and audit logs exists.

1.4. Decision needed before building session configuration and calibration execution.

---

## 2. Evaluated options

### 2.1. Session context propagation

2.1.1. Option A — explicit `SessionContext` object passed into functions.

2.1.1.1. Pros: clear data flow, easy testing, no hidden state.

2.1.1.2. Cons: many signature changes, boilerplate, risk of omission.

2.1.2. Option B — Python `contextvars.ContextVar`.

2.1.2.1. Pros: no signature changes, automatic propagation, clean.

2.1.2.2. Cons: implicit, requires reset, less obvious in isolated functions.

2.1.3. Option C — logging adapter only.

2.1.3.1. Pros: minimal change, solves logging only.

2.1.3.2. Cons: does not support future audit/enforcement, may duplicate session data.

### 2.2. Log output format

2.2.1. Option A — JSON Lines.

2.2.1.1. Pros: machine-readable, structured, future-proof.

2.2.1.2. Cons: harder to read in terminal, needs parser.

2.2.2. Option B — structured plain text key=value.

2.2.2.1. Pros: human-readable, grep-friendly.

2.2.2.2. Cons: less robust for nested data, less standardized.

2.2.3. Option C — dual output: JSON for audit/security, plain for operational.

2.2.3.1. Pros: best of both, supports compliance and operator use.

2.2.3.2. Cons: two formatters, more setup.

### 2.3. Log storage layout

2.3.1. Option A — single `logs/` with filename prefixes.

2.3.1.1. Pros: simplest, preserves existing structure.

2.3.1.2. Cons: mixes log types, harder retention/permissions.

2.3.2. Option B — separate directories:

```text
logs/operational/
logs/audit/
logs/security/
```

2.3.2.1. Pros: clear ownership, different retention/permissions possible.

2.3.2.2. Cons: more handlers, setup overhead.

### 2.4. Audit integrity

2.4.1. Option A — plain append-only file.

2.4.1.1. Pros: simple, adequate for now.

2.4.1.2. Cons: not cryptographically tamper-evident.

2.4.2. Option B — hash-chained audit log.

2.4.2.1. Pros: stronger traceability.

2.4.2.2. Cons: more design/code, over-engineering today.

2.4.3. Option C — plain append-only now, hash seam later.

2.4.3.1. Pros: build for today, design for tomorrow.

2.4.3.2. Cons: later migration still needs versioning.

---

## 3. Final decision

3.1. Session context: Option B — `contextvars.ContextVar`.

3.2. Output format: Option C — JSON Lines for audit/security, plain key=value for operational.

3.3. Log storage layout: Option B — separate directories.

3.4. Audit integrity: Option C — plain append-only now, hash seam later.

---

## 4. Rationale

4.1. `contextvars` scales from CLI to GUI/CICD with least invasive changes.

4.2. Dual output supports both operator readability and automated audit ingestion.

4.3. Separate directories allow distinct retention and permissions per log type.

4.4. Plain append-only audit avoids premature complexity while preserving a seam for future hash chaining.

4.5. Combined approach respects simplicity, modularity, reusability, flexibility, scalability, and consistency.

---

## 5. Recorded by

5.1. Decision made collaboratively during AutoCalBridge development session.

5.2. Date: 2026-08-26.

---

*This document is the authoritative decision record. Future changes must be conscious, named, and reasoned.*
```