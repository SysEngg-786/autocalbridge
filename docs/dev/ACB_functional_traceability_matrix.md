# File: docs/dev/ACB_functional_traceability_matrix.md
# Path: /d/Projects/autocalbridge/docs/dev/ACB_functional_traceability_matrix.md
# Purpose: Master development register and functional traceability matrix for AutoCalBridge.
# Date: 2026-08-28
# Status: Active

---

## 1. Purpose and single-source-of-truth statement

1.1. This document is the single master development register for AutoCalBridge.

1.2. It consolidates:
- functional traceability matrix
- known defects and architectural shortcomings
- phased build plan
- verification gates and evidence
- deferred decisions
- completed phase status

1.3. Detailed decision records remain linked, not duplicated.

1.4. All progress is tracked here. No defect is considered closed until its acceptance criterion is proven by the specified test method and recorded in the verification record.

1.5. Physical R&S RTC1002 remains a mandatory verification gate for all end-to-end changes.

---

## 2. Related decision documents

2.1. `ACB_instrument_registry.md` — registry and CLI module design.

2.2. `ACB_logging_session_architecture_decision.md` — session context and logging architecture decision.

2.3. `ACB_decisions_log.md` — chronological decision log.

---

## 3. Functional traceability matrix

| # | Function | Defect ID | Existing files/modules | Files to create/modify | Structural gap | Current state | Target phase | Acceptance criterion | Test method |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Connect physical instrument | D-01 | `config/instruments_registry.yaml`, `scripts/register_instrument.py`, `src/cli/registry_commands.py`, `src/gui/panels/setup_panel.py` | GUI network setup panel, ping action, resource string builder | GUI network workflow partial | Partial | Phase 7 | User can add/update connection without terminal or YAML editing | GUI manual + virtual |
| 2 | Discover VISA resources | D-02 | `src/core/visa_manager.py`, `PyVisaEndpoint` | Discovery service, GUI list refresh | Discovery abstraction missing | Missing | Deferred | User can refresh available instruments from GUI | GUI manual |
| 3 | Add new instrument type/profile | D-03 | `config/instruments/*.yaml`, `security/policy_loader.py`, `src/core/yaml_instrument.py` | Profile creation wizard, validation checklist | Guided workflow missing | Partial | Phase 7 | New profile can be added and verified without core code changes | Unit + physical RTC1002 |
| 4 | Register instrument instance | D-04 | `config/instruments_registry.yaml`, `src/utils/registry_validator.py`, `scripts/register_instrument.py` | GUI registration panel | Locking, metadata expansion | Partial | Phase 7 | Registry entry can be created/deleted from GUI | GUI manual + unit |
| 5 | Assign role for session | D-05 | `src/core/session_config.py`, `src/core/session_resolver.py`, `config/sessions/` | None | Runtime role layer implemented | Complete | Phase 1 | Session config assigns source/DUT roles and resolves registry IDs | Unit + virtual + physical |
| 6 | Load safety limits | D-06 | `src/core/session_runner.py`, `src/core/test_engine.py`, `security/policy_loader.py` | Safety limits schema and validator | Safety enforcement implemented | Complete | Phase 4 | Commands violating safety limits rejected at boundary | Unit + virtual + physical |
| 7 | Create calibration procedure | D-07 | `src/core/procedure_config.py`, `src/core/procedure_validator.py`, `config/procedures/` | None | Minimal procedure abstraction implemented | Complete | Phase 3 | Procedure defines points, commands, tolerances without core code changes | Unit + virtual + physical |
| 8 | Run calibration session | D-08 | `src/core/session_runner.py`, `src/core/test_engine.py`, `scripts/demo.py` | None | Registry/session/procedure integrated | Complete | Phase 3 | Demo runs from registry + session + procedure, no hardcoded endpoints | Virtual + physical RTC1002 |
| 9 | Check instrument health | None | `src/cli/instrument_commands.py`, `src/gui/panels/command_panel.py` | None | Already modular | Complete | None | test/basic-check/write-check/diagnostics pass | Already verified |
| 10 | Generate calibration report | D-10 | `src/core/report_generator.py`, `src/models/test_result.py`, `Reports/` | PDF exporter later | CSV traceability implemented; PDF seam open | Partial | Phase 6 | CSV report contains session ID, operator, supervisor, instrument IDs, procedure, results | Unit + virtual + physical |
| 11 | View logs and audit trail | D-11 | `src/utils/structured_logger.py`, `security/logger.py`, `logs/` | GUI log viewer improvements | Structured logs implemented; GUI log capture partial | Partial | Phase 5/7 | Audit log contains full traceability fields in JSON Lines | Unit + virtual + physical |
| 12 | Manage users and access | D-12 | None | Access control module, locked registry | Security layer missing | Missing | Deferred | Admin can lock registry; normal user cannot modify | Unit + GUI manual |
| 13 | GUI instrument control | D-13 | `src/gui/main_window.py`, `src/gui/panels/command_panel.py`, `src/gui/panels/setup_panel.py` | Fix command response capture to log panel | GUI response capture bug | Partial | Phase 7 | GUI can send single command/query and display response | GUI manual + physical |
| 14 | Batch command execution | D-14 | `src/cli/instrument_commands.py` built-in checks | Generic batch script/profile | Command set data not external | Partial | Phase 7 | User can define and run a command batch without code changes | Unit + physical |
| 15 | Profile verification | D-15 | `src/cli/instrument_commands.py` | Profile verification report | Verification report missing | Partial | Phase 7 | Per-command PASS/FAIL verification report generated | Unit + physical |

---

## 4. Architectural quality and known shortcomings

| Defect ID | Description | Impact | Target phase | Acceptance criterion | Status |
|---|---|---|---|---|---|
| D-16 | TestEngine god object | Hard to extend, mixes endpoint, sync, error, sequence logic | Phase 3 | TestEngine becomes thin procedure runner; responsibilities separated | Partially addressed |
| D-17 | Duplicate result representation | TestResult unused, dicts returned | Phase 6 | One canonical result model used everywhere | Passed |
| D-18 | Command policy asymmetry | Physical endpoint lacks policy | Phase 4 | Policy enforced on physical and simulator endpoints consistently | Passed |
| D-19 | demo.py hardcoded strings | Not registry/session-driven | Phase 2 | demo.py resolves endpoints from registry/session | Passed |
| D-20 | Instrument model disconnected | Not linked to registry/endpoint | Phase 2 | Instrument model aligned with registry entry | Open |
| D-21 | TestEngine standard logging | No structured audit | Phase 5 | TestEngine uses structured audit/operational loggers | Passed |
| D-22 | CLI session context not implemented | CLI audit lacks session fields | Deferred | Optional CLI session context design-only for now | Open |
| D-23 | Comment-preserving YAML writer missing | Registry comments lost on write | Deferred | Registry writer preserves comments or alternative safe update | Open |
| D-24 | Common command policy externalization pending | Policy data embedded in loader | Deferred | Common commands live in controlled data file | Open |
| D-25 | ESR used as fatal error trigger | Power-on bit caused false failure on physical RTC1002 | Phase 3 | Error queue is authoritative; ESR only diagnostic | Passed |
| D-26 | GUI command response not logged to GUI log panel | send_instrument prints to console, not GUI log | Phase 7 | CommandPanel logs query response directly to GUI log | Open |

---

## 5. Phased build plan with verification gates

| Phase | Target defects | Acceptance criterion | Verification gate | Status |
|---|---|---|---|---|
| Phase 1 | D-05, D-08 preparation | Session config loads, validates, resolves registry IDs and roles | 12 session tests + virtual resolution | Complete |
| Phase 2 | D-19, D-08 | demo.py uses session/registry, not hardcoded sim strings | Virtual demo run passed; physical RTC1002 session resolver passed | Complete |
| Phase 3 | D-07, D-16, D-25 | procedure defines source/DUT commands and tolerances; engine runs procedure | 28 tests OK; virtual procedure run passed; physical RTC1002 procedure run passed | Complete |
| Phase 4 | D-06, D-18 | safety limits enforced; policy active on physical endpoint | 35 tests OK; virtual demo passed; physical policy enforcement passed | Complete |
| Phase 5 | D-21, D-11 | audit logs contain session ID, operator, supervisor, instruments, commands, responses, results | 37 tests OK; physical RTC1002 audit log full fields | Complete |
| Phase 6 | D-10, D-17 | report uses canonical TestResult and includes session traceability | 37 tests OK; virtual demo + physical RTC1002 CSV header verified | Complete |
| Phase 7 | D-01, D-04, D-13, D-03 partial, D-14 partial, D-15 partial | GUI works for connection, registration, instrument control, profile verification | GUI shell functional; command/run/log/results panels wired; remaining polish and response capture | In progress |

Deferred: D-02, D-12, D-20, D-22, D-23, D-24

---

## 6. Verification record

| Item | Phase | Test method | Date | Result | Evidence |
|---|---|---|---|---|---|
| Registry validation | Pre-phase | Unit tests | 2026-08-26 | Passed | 8 tests OK |
| Logging architecture | Pre-phase | Direct endpoint test | 2026-08-26 | Passed | audit log JSON Lines verified |
| Session loader/validator/resolver | Phase 1 | Unit tests | 2026-08-27 | Passed | 12 session tests OK |
| Procedure loader/validator | Phase 3 | Unit tests | 2026-08-27 | Passed | 8 procedure tests OK |
| Full regression after Phase 3 | Phase 3 | Unit test discovery | 2026-08-27 | Passed | 28 tests OK |
| Virtual session+procedure run | Phase 3 | Virtual run | 2026-08-27 | Passed | 4/4 PASS |
| Physical RTC1002 session+procedure run | Phase 3 | Physical query path | 2026-08-27 | Passed | CHAN1:SCAL? returned 5.00E-03, PASS |
| Error queue authoritative check | Phase 3 | Physical RTC1002 | 2026-08-27 | Passed | ESR=128 no longer false failure |
| Safety limit merge/enforcement | Phase 4 | Unit tests | 2026-08-27 | Passed | 7 safety tests OK |
| Physical policy enforcement | Phase 4 | Physical RTC1002 | 2026-08-27 | Passed | CHAN1:SCAL? allowed; *TST? rejected |
| Full regression after Phase 4 | Phase 4 | Unit test discovery | 2026-08-27 | Passed | 35 tests OK |
| Structured logging in TestEngine | Phase 5 | Unit tests + log inspection | 2026-08-27 | Passed | 37 tests OK, point_result fields complete |
| Physical RTC1002 audit traceability | Phase 5 | Physical run + audit log | 2026-08-27 | Passed | session_id, operator, supervisor, instrument_roles present |
| Canonical TestResult report | Phase 6 | Virtual + physical run + CSV inspection | 2026-08-27 | Passed | Header contains SessionID, Operator, Supervisor, Procedure, SourceID, DUTID |
| Full regression after Phase 6 | Phase 6 | Unit test discovery | 2026-08-27 | Passed | 37 tests OK |
| GUI shell smoke test | Phase 7 | GUI launch + auto-close | 2026-08-28 | Passed | Window opened and closed successfully |
| GUI run selected session path | Phase 7 | Headless GUI functional test | 2026-08-28 | Passed | run_selected_session executed |
| GUI command panel send path | Phase 7 | Headless GUI functional test | 2026-08-28 | Passed | Command sent, console response captured; GUI log capture pending |

---

## 7. Open decisions and deferred items

| Item | Decision |
|---|---|
| GUI command response logging | Fix CommandPanel to log response directly to GUI log panel |
| GUI layout refinement | Adjust visual layout after functional fixes |
| Network Setup panel | Placeholder button created; full panel TBD |
| Clear Log button and context menu | Planned for log panel update |
| Prominent instrument/status display | Planned for top status area update |
| Session dropdown display | Show friendly label instead of raw filename later |
| Semi-automatic/manual DUT mode | TBD after Phase 7 core GUI |
| Session file lifecycle retention | Keep original session file for repeatability/ALCOA+; archive later |
| Session reuse | Clone/template workflow later; `label` optional field added |
| CLI session context | Deferred, design-only |
| Resource discovery | Deferred |
| User access control | Deferred |
| Hash-chained audit | Deferred, plain append-only now |
| Comment-preserving YAML writer | Deferred |
| `src/models/instrument.py` realignment or retirement | Deferred to later refactor |
| UI/UX guideline document for future projects | TBD after GUI stabilization |

---

*This document is the single master development register. All progress, defects, and verification evidence must be recorded here.*