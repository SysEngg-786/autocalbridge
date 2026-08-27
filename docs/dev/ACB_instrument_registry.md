Save the following full file as `docs/dev/`, replacing existing content.

```markdown
# File: docs/dev/ACB_instrument_registry.md
# Path: /d/Projects/autocalbridge/docs/dev/ACB_instrument_registry.md
# Purpose: Internal development reference for the AutoCalBridge instrument registry module.
# Date: 2026-08-26
# Status: Active design + build log

---

## 1. Purpose

1.1. Define the instrument registry module for AutoCalBridge.

1.2. Record its development sequence, validation rules, and future build targets.

1.3. Keep module-level decisions separate from user-facing documentation.

---

## 2. Scope

2.1. The registry manages instrument instances, not instrument capability definitions.

2.2. Capability definitions remain in `config/instruments/*.yaml`.

2.3. Each registry entry links one deployable instrument to its capability profile.

2.4. Registry entries may be physical or virtual.

2.5. The registry is admin-managed and locked from normal user modification.

---

## 3. Current registry file

3.1. Path:

```text
config/instruments_registry.yaml
```

3.2. Format: YAML.

3.3. Top-level key: `instruments`.

3.4. Required fields per entry:

3.4.1. `id`

3.4.2. `profile`

3.4.3. `kind`

3.4.4. `display_name`

3.5. Optional or progressive fields:

3.5.1. `connection`

3.5.2. `role`

3.5.3. `safety_limits`

3.5.4. `metadata`

3.6. Current registry entries:

3.6.1. `rtc1002-lab1` — physical R&S RTC1002, `TCPIP0::10.0.0.10::INSTR`.

3.6.2. `rtc1002-sim` — virtual R&S RTC1002 using the same capability profile.

---

## 4. Validation rules

4.1. `id` must be unique.

4.2. `profile` must exist under `config/instruments/`.

4.3. `kind` must be `physical` or `virtual`.

4.4. Physical entries require a VISA resource string in `connection`.

4.5. Virtual entries require `connection` using:

```text
sim://<profile_name>
```

4.6. Unknown fields must be rejected, not silently ignored.

4.7. Validation failures must report the exact entry and field.

---

## 5. Module architecture

5.1. Implemented modules:

5.1.1. `src/utils/instrument_registry.py`

5.1.1.1. Loader and normalized entry/registry classes.

5.1.1.2. Delegates validation to `registry_validator`.

5.1.2. `src/utils/registry_validator.py`

5.1.2.1. Contains all validation rules.

5.1.2.2. Raises `RegistryValidationError` with collected errors.

5.2. CLI package:

5.2.1. `src/cli/__init__.py` — package marker.

5.2.2. `src/cli/common.py` — shared registry lookup and endpoint-open helpers.

5.2.3. `src/cli/registry_commands.py` — `list`, `register`, `unregister`.

5.2.4. `src/cli/instrument_commands.py` — `test`, `basic-check`, `write-check`, `diagnostics`, `send`.

5.3. Thin entrypoint scripts:

5.3.1. `scripts/register_instrument.py` — registry management commands only.

5.3.2. `scripts/instrument_control.py` — instrument interaction commands only.

---

## 6. CLI commands

6.1. Registry CLI:

```text
python -m scripts.register_instrument list
python -m scripts.register_instrument register --id <id> --profile <profile> --kind physical|virtual --display-name <name> --connection <visa|sim> [--role any|source|dut]
python -m scripts.register_instrument unregister <id>
```

6.2. Instrument control CLI:

```text
python -m scripts.instrument_control test <id>
python -m scripts.instrument_control basic-check <id>
python -m scripts.instrument_control write-check <id>
python -m scripts.instrument_control diagnostics <id>
python -m scripts.instrument_control send <id> "<SCPI command>"
```

6.3. `send` sanitization rules:

6.3.1. Must be a string.

6.3.2. Must not be empty or whitespace-only.

6.3.3. Must not exceed 1024 characters.

6.3.4. Printable ASCII only; control characters rejected.

6.3.5. Commands ending in `?` are sent as queries; others as writes.

---

## 7. Progressive build sequence

7.1. Registry schema + loader + validation — **complete**.

7.2. Register/unregister/list CLI — **complete**.

7.3. Connectivity test using existing endpoint path — **complete**.

7.4. Basic read-only check — **complete**.

7.5. Write-path verification — **complete**.

7.6. Diagnostics — **complete**.

7.7. Single-command CLI — **complete**.

7.8. Safety limits integration — not started.

7.9. Runtime role assignment layer — not started.

7.10. GUI registration panel — not started.

7.11. Locking and role-based access enforcement — not started.

---

## 8. Verification status

8.1. Physical R&S RTC1002:

8.1.1. `test` — passed.

8.1.2. `basic-check` — passed.

8.1.3. `write-check` — passed.

8.1.4. `diagnostics` — passed.

8.1.5. `send` query/write — passed.

8.2. Virtual RTC1002:

8.2.1. `test` — passed.

8.2.2. `basic-check` — passed.

8.2.3. `write-check` — passed.

8.2.4. `diagnostics` — passed.

8.2.5. `send` — passed.

8.3. Unit tests:

8.3.1. `tests/test_utils/test_instrument_registry.py` — 8 tests passed.

---

## 9. Safety and locking

9.1. Registry holds safety-relevant deployment data.

9.2. Normal users must not modify registry entries.

9.3. Safety limits start empty and are added later from capability profiles plus deployment constraints.

9.4. Overrides must be conscious, named, and reasoned.

9.5. CLI input is sanitized before use. Control characters are rejected.

9.6. Self-test and calibration commands are excluded until the full command pipeline is proven safe.

---

## 10. CI/CD plan

10.1. Registry YAML is validated in CI on every commit.

10.2. Loader unit tests run for valid, invalid, duplicate, and missing-profile cases.

10.3. Connectivity tests run only when physical test instruments are available.

10.4. Virtual registry entries must remain testable without hardware.

10.5. CLI command logic is importable and therefore testable without subprocess calls.

---

## 11. TBB log

11.1. Instrument registration module — structured add/delete, locked for normal user, holds identity/deployment/safety profile/metadata/role, CLI-first, GUI later. **Basic version complete; advanced locking pending.**

11.2. Runtime role assignment layer — session/test config decides source vs DUT, not instrument profile. **Not started.**

11.3. Safety limits integration into registry validation and endpoint enforcement. **Not started.**

11.4. Comment-preserving YAML writer for registry updates. **Not started; current safe_dump removes comments.**

11.5. Common command policy externalization — move allowed common queries/writes out of `security/policy_loader.py` into a single controlled command data file. **Not started.**

11.6. Generic single-command CLI as default; batch execution as later enhancement. **Single command complete; batch exists as built-in checks only.**

---

## 12. Open decisions

12.1. Final CLI location: `scripts/` or `src/`. **Currently thin scripts + `src/cli` package.**

12.2. Exact runtime role override format in session/test config. **Deferred until role assignment work begins.**

12.3. Whether to expose `SYST:TREE?` output in a controlled diagnostics variant. **Deferred; large output requires file-safe handling.**

---

*This document is the internal development reference for the instrument registry and CLI module.*
```