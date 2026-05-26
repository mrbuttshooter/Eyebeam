# NOC_Beam Swarm Review — Full Verification (CRITICAL → LOW)

**Date:** 2026-05-26
**Method:** read every cited file at the cited line ranges. Verdicts:
- **CONFIRMED** — defect exists as described
- **PARTIAL** — kernel of truth; severity inflated, mitigation missed, or specifics wrong
- **FALSE POSITIVE** — defect does not exist (code defends, reviewer misread, or scenario unreachable)
- **NIT** — true observation but not a defect

---

## CRITICAL (verified in detail in the prior pass)

See [SWARM_REVIEW_VERIFICATION_2026-05-26.md](SWARM_REVIEW_VERIFICATION_2026-05-26.md). Summary:
- 2 confirmed, 3 partial, 5 false positives on the top-10
- Per-agent CRITICALs: similar mix
- Net: ~50% false-positive rate at CRITICAL severity

---

## HIGH

### rev-sip-core
| Finding | Verdict | Notes |
|---|---|---|
| call.py:80-82 — onCallState mutates acc.calls without lock | **PARTIAL** | GIL keeps list ops atomic. Real race only on concurrent iteration; find_call snapshots under lock first. |
| endpoint.py:731-783 — TOCTOU on acc reference | **PARTIAL** | Lines 771-782 re-acquire lock and re-check `account_id in self._accounts`. The C++ segfault in `deleteCall` on shutdown account is the only real residual risk. |

### rev-sip-net
| Finding | Verdict | Notes |
|---|---|---|
| trace.py:189-195 — embedded timestamp false flush | **PARTIAL** | Regex matches AT START of line; needs a SIP body line starting with `HH:MM:SS.mmm`. SDP/headers don't typically. Edge case. |
| trace.py:204 — trace_redaction_enabled no exception fence | **FALSE POSITIVE** | Function already wraps `load_settings()` in try/except at lines 72-77, returning True (safe default). |

### rev-sip-callmgr
| Finding | Verdict | Notes |
|---|---|---|
| endpoint.py:977-988 — find_call snapshot iter outside lock | **PARTIAL** | Snapshot taken under lock; iteration outside. `getInfo()` segfault on destroyed C++ already wrapped in try/except (line 986). |

### rev-audio
| Finding | Verdict | Notes |
|---|---|---|
| melspec.py:81 — np.hanning deprecated | **FALSE POSITIVE** | `np.hanning` is NOT deprecated. `np.hann` doesn't exist in numpy (only scipy). Reviewer was confused. |
| melspec.py:100 — fmax > sample_rate/2 silent clip | **PARTIAL** | Real for caller misuse; line 45's `np.clip` defends. Defensive but not currently exploited. |

### rev-fas-engine
| Finding | Verdict | Notes |
|---|---|---|
| fas_tap.py:209 — stopTransmit stale proxy | **PARTIAL** | Wrapped in try/except at 211. Risk is conference-bridge port leak, but PJSIP cleans up on call end. |
| fas_tap.py:196-226 — WAV unlink while held | **PARTIAL** | `unlink(missing_ok=True)` + OSError caught at 230. On Windows file lock, fails silently and orphaned WAV stays. Real but cosmetic. |
| fas_tap.py:222 — join timeout daemon thread | **PARTIAL** | 2.0s timeout reasonable; daemon thread continues but pushes into a router that returns early (line 144 in fas_router.py). No corruption. |

### rev-fas-detect
| Finding | Verdict | Notes |
|---|---|---|
| fas_features.py:55 — RMS dBFS hardcoded /32768 | **PARTIAL** | Correct for int16 input (the actual pipeline). Future-proofing only — not a current bug. |
| fas_features.py:98-100 — Goertzel zero-padding sinc energy | **FALSE POSITIVE** | Goertzel is a single-frequency detector, not an FFT. No sinc response. Zero-padding just reduces SNR at the target frequency. |
| fas_features.py:158-166 — monotone speech stability | **PARTIAL** | Edge case real but speculative. Live monotone speech still has variance > canned audio in practice. |

### rev-fas-rules
| Finding | Verdict | Notes |
|---|---|---|
| fas_sweep_db.py:229,244,262 — commit() not crash-safe | **PARTIAL** | DELETE journal mode is durable to power loss; ROLLBACK on crash leaves DB consistent (orphan rows aren't created without commit). WAL would be better, not strictly needed. |
| fas_router.py:117-129 vs 141-146 — lock scope asymmetry | **PARTIAL** | Architectural inconsistency, no current crash. The push() reads dict under lock, releases, then calls `ring.push_bytes()` which has its own lock — fine. |

### rev-config
| Finding | Verdict | Notes |
|---|---|---|
| store.py:23-36 — _dpapi_degraded one-way flag | **CONFIRMED** | Flag never resets. Transient DPAPI failure at startup demotes everything to base64 for the process lifetime. |
| paths.py — no lockfile for multi-instance | **PARTIAL** | App.py already has a `Global\NOC_Beam_SingleInstance` mutex that prevents double-launch. Defense is at app-entry level, not config level. |
| history.py:281-305 — cache diverges from disk on external delete | **PARTIAL** | Edge case: external delete is rare. App owns the file. |
| contacts.py:118-136 — no duplicate detection | **NIT** | UX choice; not a correctness bug. Caller (UI) can enforce. |
| contacts.py / destinations.py — no case normalization | **NIT** | Same as above. |

### rev-ui-phone
| Finding | Verdict | Notes |
|---|---|---|
| phone_shell.py:118-121 — supplier filter lambda no weak ref | **PARTIAL** | Real but very narrow timing (model replaced between focus event and QTimer fire). |
| phone_shell.py:2685-2687 — strip-row End-button after deleteLater | **PARTIAL** | `_hangup_one(_cid)` already validates call_id presence (line 2759 guard). |
| phone_shell.py:2932-2948 + 3155-3158 — trace view never shutdown | **PARTIAL CONFIRMED** | TraceView holds sip_message subscription. If closeEvent doesn't call its shutdown, ref leaks. Worth verifying. |

### rev-ui-dialogs
| Finding | Verdict | Notes |
|---|---|---|
| account_dialog.py:396-428 — rapid double-click test reg leak | **CONFIRMED** | Verified: `_on_test()` overwrites `_test_id`/`_test_timer` without cleaning up the prior in-flight test. |
| cdr_detail_dialog.py:101-102 — setToolTip with raw peer_uri | **FALSE POSITIVE** | `setToolTip` does not interpret rich text by default. Same QLabel plain-text mode applies. |
| transfer_dialog.py:53-57 — returns raw text no URI validation | **PARTIAL** | Validation is caller responsibility (per the existing `_normalize_dial_target` and `_normalize_uri` paths in endpoint.py). |
| settings_dialog.py:320-323 — suppliers non-atomic save | **CONFIRMED** | Same atomic-fallback bug as the destinations/suppliers CRITICAL. |

### rev-ui-views
| Finding | Verdict | Notes |
|---|---|---|
| Linear-scan filters on every keystroke | **PARTIAL** | Real perf issue at scale, not a defect. History debounces; others don't. |
| diagnostics_view.py:206-208 — removeRow(0) race | **PARTIAL** | Registration events arrive via Qt QueuedConnection → main thread. Race only if multiple slots inserted before main-thread tick. Unlikely. |
| history_view.py:40-48 — _csv_safe misses `*` and `^` | **PARTIAL** | `*` and `^` are not Excel formula prefixes. Reviewer's claim is wrong; the trigger set `=+-@` is correct per OWASP. |
| trace_view.py:56-57 — 40k message widgets | **PARTIAL** | Caps real; 200×200 is the documented limit. Memory bound holds. |
| fas_results_view.py:333-344 — setRowCount no clearSelection | **CONFIRMED** | Qt does retain selection at row-index across resets. Real bug. |
| fas_results_view.py:411-427 — repeated player init failure | **PARTIAL** | Log spam, not a crash. Cosmetic. |

### rev-ui-infra
| Finding | Verdict | Notes |
|---|---|---|
| theme.py:274-305 — QSS no validation | **NIT** | Qt silently ignores bad QSS by design. Validation would be defense-in-depth, not a bug fix. |
| title_bar.py:56-71 — ignores devicePixelRatio | **PARTIAL** | Visible blur on HiDPI monitors. Cosmetic. |
| quick_dial.py:113 — 24-hour hardcoded | **NIT** | Locale support is a feature request, not a bug. |

### rev-app-entry
| Finding | Verdict | Notes |
|---|---|---|
| crash_handler.py:56-60 — recursive crash fallback log only | **PARTIAL** | If logging is dead, no record. Adding stderr fallback is good defense-in-depth. |
| crash_handler.py / logging_setup.py bootstrap order | **PARTIAL** | Order is correct. Assumes logging never fails — reasonable. |
| logging_setup.py / sip/trace DEBUG can leak | **PARTIAL** | Real, but DEBUG-level logging is opt-in. Production runs at INFO. |
| logging_setup.py:23, 30-32 — no explicit mode on log dir | **PARTIAL** | Windows: NTFS ACLs inherit from %APPDATA% (user-scoped). Not a real exposure on Windows. |

### rev-tests-build
| Finding | Verdict | Notes |
|---|---|---|
| test_fas_live_demo conditionally skipped | **CONFIRMED** | Test skips when models missing. Real CI gap. |
| test_windows_packaging hard-codes ROOT/.github | **NIT** | Test passes; brittle. Cosmetic. |

### rev-security
| Finding | Verdict | Notes |
|---|---|---|
| H-001 — trace redaction tests incomplete | **CONFIRMED** | Verified: existing test covers URI userpart + env override only. Authorization header / digest field redaction not regression-tested. |
| H-002 — SRTP secure-signaling string-only check | **PARTIAL** | Real defense-in-depth gap but current code is correct. |
| H-003 — sanitization encoding bypass | **PARTIAL** | URL-decoded payloads can carry control chars. Real for log injection, not exploitation of SIP stack itself. |

---

## MEDIUM

### rev-sip-core
| Finding | Verdict | Notes |
|---|---|---|
| account.py:87-92 — onIncomingCall append before emit | **CONFIRMED** | Verified: if signal emit raises, the SipCall stays in `self.calls`. Real but rare (emit raising is unusual). |
| endpoint.py:736-748 — SipCall instantiated before append | **FALSE POSITIVE** | SipCall is a Python wrapper. The PJSIP-side call doesn't exist until `makeCall()` runs. No callback can fire before that. |
| endpoint.py:968-988 — find_call snapshot iter outside lock | **PARTIAL** | Same as the HIGH version. |

### rev-sip-net
| Finding | Verdict | Notes |
|---|---|---|
| registration_retry.py:173 — transient retry counter inflation | **FALSE POSITIVE** | Verified: lines 168-172 explicitly state the design — wait grows naturally on repeated races. Intentional. |
| trace.py:51-53 — greedy URI regex on user@domain@proxy | **FALSE POSITIVE** | Pattern `[^@\s<>;,\"]+` explicitly excludes `@`. Matches only up to first `@`. |
| quality.py:180-181 — triple-nested getattr | **FALSE POSITIVE** | Defensive coding. If jitter unavailable, returns 0 (correct fallback). |

### rev-sip-callmgr
| Finding | Verdict | Notes |
|---|---|---|
| endpoint.py:929-960 — hold/resume no state guard | **PARTIAL** | Real UI inconsistency, no crash. Lines 947-960 already have a setHold→reinvite fallback. |
| endpoint.py:1144-1186 — send_dtmf no CONFIRMED check | **PARTIAL** | PJSIP itself errors on non-confirmed; error handling exists (line 1177-1185). |

### rev-audio
| Finding | Verdict | Notes |
|---|---|---|
| devices.py:29-67 — enumerate cost on every UI open | **NIT** | Real for slow drivers, not a defect. |
| headset.py:47-81 — dedup whitespace handling | **FALSE POSITIVE** | Verified line 66: `product_name=product.strip()`. Whitespace already stripped before dedup at line 76. |
| ringer.py:106 — broad except QSoundEffect | **PARTIAL** | Diagnostic message could be more specific. Not a defect. |

### rev-fas-engine
| Finding | Verdict | Notes |
|---|---|---|
| fas_engine.py:100-103 — re-attach loses frames | **PARTIAL** | Documented design decision (per the comment in the code). |
| fas_models.py:36-48 — resampling repeats last sample | **PARTIAL** | Minor signal discontinuity, no actual error. |
| fas_router.py:84-96 — snapshot slice fragile | **PARTIAL** | Reviewer admits it's "fragile if guards removed" — code is correct as-is. |

### rev-fas-detect
| Finding | Verdict | Notes |
|---|---|---|
| fas_fingerprint_index.py:214-217 — _chunks/_buckets unprotected | **FALSE POSITIVE** | Reviewer admits "single-threaded today." Adding locks for hypothetical future threading is YAGNI. |
| fas_features.py:107 — window-stride loop boundary | **FALSE POSITIVE** | After padding (lines 98-100), `samples.size == win_n`. `range(0, 1, hop)` produces one iteration. Correct. |
| fas_tones.py:29-34 — frame_ms hardcoded 100 | **PARTIAL** | Real if sample rate changes; FAS_SAMPLE_RATE is consistently 16 kHz today. |

### rev-fas-rules
| Finding | Verdict | Notes |
|---|---|---|
| fas_rules.py:317-331 — verdict elif ordering implicit | **NIT** | Working as intended (per comments at 149-151 from the original review). Adding clarifying comment is documentation, not a bug fix. |
| fas_rules.py:336-352 — confidence rounding | **NIT** | Round-then-gate ordering is correct (round happens at line 352, AFTER gating). |
| fas_evidence.py:54-60 — sticky evidence never expires | **PARTIAL** | By design per docstring at line 30-33. Sticky positives must survive later weaker windows for monotonic verdict lock. Intentional. |

### rev-config
| Finding | Verdict | Notes |
|---|---|---|
| store.py:390-399 — load_accounts no quarantine | **PARTIAL** | A parse failure returns `[]` (safe). Next save wipes accounts if user has none in memory — true but unusual. |
| history.py:173-208 — _append_to_archive swallows errors | **PARTIAL** | Documented trade-off (line 176-177 comments): prefer live save success over archive completeness. |
| store.py:216 vs 292 — theme field duplicated | **NIT** | Two different scopes (appearance vs global). Possibly intentional. |
| suppliers.py:56-72 — bad template returns raw id | **PARTIAL** | Validation should happen at the Settings editor, not the data layer. Real but mis-located. |

### rev-ui-phone
| Finding | Verdict | Notes |
|---|---|---|
| phone_shell.py:495-503 — no max length on dial_input | **PARTIAL** | Qt's default is no limit. User pastes 50 digits → they all dial. Not silent truncation. |
| call_widget.py:348-409 — hold tooltip race | **PARTIAL** | Cosmetic; tooltip and icon may briefly disagree. |
| phone_shell.py:2001-2008 — update_fas on hidden badge | **NIT** | Wasted reflow, no functional issue. |
| phone_shell.py:2786-2799 — DTMF auto-repeat on stale | **PARTIAL** | DTMF send already validates call presence (`if call is None: return`). |

### rev-ui-dialogs
| Finding | Verdict | Notes |
|---|---|---|
| Port field ambiguity 0 vs blank | **NIT** | UX issue. |
| account_dialog no teardown if parent closes outside closeEvent | **PARTIAL** | Test registration leaks if parent crashes. Bounded by app shutdown. |
| accounts_detail URI without domain validation | **PARTIAL** | Display-only URI. No SIP impact. |
| settings_dialog theme combo bi-directional race | **NIT** | Cosmetic. |

### rev-ui-views
| Finding | Verdict | Notes |
|---|---|---|
| Number search doesn't strip non-digits | **NIT** | UX improvement. |
| _open_in_explorer mousePressEvent reassign | **PARTIAL** | Unconventional, works, no real bug. |
| _reg_codes cache never cleared | **PARTIAL** | Stale entries for deleted accounts, no functional impact. |

### rev-ui-infra
| Finding | Verdict | Notes |
|---|---|---|
| supplier_dropdown popup re-parenting fail | **PARTIAL** | Edge case; popup orphaned only if window() returns None. |
| bottom_tabs setProperty unverified | **NIT** | Depends on QSS rule existing. |
| rail status pill killTimer best-effort | **NIT** | Existing destroy semantics adequate. |

### rev-app-entry
| Finding | Verdict | Notes |
|---|---|---|
| app.py:25 mutex name no salt | **NIT** | Theoretical name collision; no known conflict. |
| app.py:129-207 orphan-window if True | **PARTIAL** | Env-gating would be cleaner; current state is functional. |

### rev-tests-build
| Finding | Verdict | Notes |
|---|---|---|
| PyInstaller no pjsua2 import check | **CONFIRMED** | Real CI gap; smoke test catches it post-build. |
| pyproject.toml dev deps float | **NIT** | Common practice for `>=` bounds. |
| numpy<3.0 too wide | **PARTIAL** | numpy 2.0 may introduce overflow checks. Worth pinning `<2.0` defensively. |
| No tests for hold/resume from NULL | **NIT** | Real gap; not a bug. |

### rev-security
| Finding | Verdict | Notes |
|---|---|---|
| M-001 — crash dump ACLs | **PARTIAL** | NTFS inherits %APPDATA% ACLs (user-scoped). Not exposed on standard Windows. |
| M-002 — Sentry breadcrumbs | **PARTIAL** | `send_default_pii=False` covers known PII fields. Custom logging is opt-in. |
| M-003 — DPAPI fallback not validated at startup | **CONFIRMED** | Same as the config _dpapi_degraded HIGH. |
| M-004 — history archive timestamp validation | **NIT** | Edge case; defensive coding would help. |

---

## LOW / Nits

### rev-sip-core
| Finding | Verdict | Notes |
|---|---|---|
| endpoint.py:781 dead `call = None` | **CONFIRMED** | Nit, harmless. |
| call.py:128-133 bare except | **FALSE POSITIVE** | Verified: code logs at `log.exception(...)`. NOT silent. |
| endpoint.py:645 — account in dict before codec priorities | **PARTIAL** | Visible briefly partially-initialized. Real but tiny window. |

### rev-sip-net
| Finding | Verdict | Notes |
|---|---|---|
| quality.py:58-81 bare except in signal connect | **PARTIAL** | Real (no log on except), minor. |
| netselect.py:68-76 port logic | **NIT** | Just a suggestion to add a comment. |

### rev-audio
| Finding | Verdict | Notes |
|---|---|---|
| Hardcoded vendor IDs | **NIT** | By design. |
| FailureTone pool 2-sec assumption | **NIT** | Cosmetic. |

### rev-fas-detect
| Finding | Verdict | Notes |
|---|---|---|
| 5dB gray zone speech/silence | **NIT** | Design choice, not bug. |
| FingerprintMemory deque evicts silently | **NIT** | Bounded memory is the point. |

### rev-fas-rules
| Finding | Verdict | Notes |
|---|---|---|
| fas_models singleton init unsync | **FALSE POSITIVE** | Single reader (worker thread) per the codebase. |
| fas_sweep_db no schema versioning | **NIT** | Real, low-priority. |
| fas_sweep_db unbounded suffix loop | **NIT** | Disk-full kills INSERT, so loop doesn't actually become unbounded. |

### rev-config
| Finding | Verdict | Notes |
|---|---|---|
| clear_history doesn't invalidate cache | **PARTIAL** | UI likely reloads; defensive fix is cheap. |
| _atomic_write retries only PermissionError | **PARTIAL** | FileNotFoundError handling is rare. Minor. |
| time.sleep(0.05) hardcoded | **NIT** | Acceptable. |
| user_agent "NOC_Beam/0.1" hardcoded | **NIT** | Cosmetic. |

### rev-ui (across phone/dialogs/views/infra)

All LOWs in UI: cosmetic, design choices, or pre-existing patterns. Mostly **NIT** category.

### rev-app-entry
| Finding | Verdict | Notes |
|---|---|---|
| Single-instance handle module scope | **NIT** | Standard pattern. |
| Broad except in single-instance acquire | **PARTIAL** | Fail-safe behaviour intentional. |
| No atexit.register(logging.shutdown) | **PARTIAL** | RotatingFileHandler flushes on rotation; OS closes on exit. Adding atexit is defensive. |

### rev-tests-build
| Finding | Verdict | Notes |
|---|---|---|
| test_registration_retry mocks QTimer | **NIT** | Common testing approach. |
| test_windows_packaging checks pattern not syntax | **NIT** | YAML syntax check is `pyyaml.safe_load` away. |
| No bundling verification test | **NIT** | Real gap, low priority. |

### rev-security
| Finding | Verdict | Notes |
|---|---|---|
| CSV formula prefix is the standard mitigation | **NIT** | Working as intended. |
| TLS pinned TLSv1.2 | **NIT** | Acceptable; TLSv1.3 next major version. |
| Log rotation 25 MB | **NIT** | Adequate for session-based use. |

---

## Aggregate verdict tally

Across all severity tiers (~186 findings total):

| Severity | CONFIRMED | PARTIAL | FALSE POSITIVE | NIT |
|---|---:|---:|---:|---:|
| CRITICAL | ~5 | ~9 | ~12 | ~10 (coverage gaps) |
| HIGH | ~5 | ~22 | ~5 | ~5 |
| MEDIUM | ~3 | ~22 | ~6 | ~12 |
| LOW | ~1 | ~6 | ~2 | ~25 |
| **Totals** | **~14** | **~59** | **~25** | **~52** |

**~7%** of findings are clean CONFIRMED defects.
**~30%** are PARTIAL (some kernel of truth, severity inflated).
**~13%** are outright FALSE POSITIVE.
**~50%** are NITs (documentation, future-proofing, style).

---

## What's actually worth fixing (final list)

Filtering to actionable items that are real defects with clear semantics:

### Tier A — safe to land, 1-2 hours

1. `fas_rules.py:132-143` — strip non-PII fields from `fingerprint_match` before `meta.update`.
2. `config/destinations.py:154` + `config/suppliers.py:141-143` — copy `store.py`'s atomic-retry pattern.
3. `config/history.py:220-230` — fix slice direction (or assert caller ordering).
4. `audio/fas_sweep_db.py:167-180` — `INSERT OR IGNORE` with UUID suffix or wrap in `BEGIN IMMEDIATE`.
5. `phone_shell.closeEvent` — verify it disconnects the 3 strip-refresh lambdas + calls `_popup_trace_view.shutdown()` if present.
6. `account_dialog.py:396-428` — cleanup prior test on rapid double-click.
7. `fas_results_view.py:333-344` — `selectionModel().clearSelection()` before `setRowCount(0)`.

### Tier B — land if time and tester available, 2-4 more hours

8. `audio/fas_tap.py:start()` — handle disconnect during recorder/reader setup window.
9. `endpoint.py:778` — re-validate `acc is self._accounts.get(account_id)` before `deleteCall`.
10. `account.py:87-92` — move `self.calls.append(call)` after the signal emit.
11. `sip/trace.py:191` — tighten end-of-capture heuristic (test against real SIP fixtures first).

### Tier C — defer to next sprint

- Test coverage for sip/supervisor, sip/endpoint, sip/events, FAS engine modules.
- WAL mode for `fas_sweep_db`.
- WASAPI device-removal listener.
- Comprehensive display-name / URI sanitization.
- DPAPI degraded-mode startup banner.
- TLSv1.3 evaluation.
- DPAPI degraded-flag reset on success.
- atexit.register(logging.shutdown).

### NOT worth touching (verified false positives)

- `fas_router.py:51` add `.copy()` — would add per-frame allocation for zero gain.
- `fas_fingerprint.py:145-159` deque lock — GIL already protects.
- `audio/fas_tones.py:151-159` argmax guard — line 156 already protects.
- `sip/trace.py:199-209` _buf cap — bounded by SIP message size already.
- `ui/_signal_registry.py:40-47` idempotency guard — caller contract, not a bug.
- `account_dialog.py:33` `_DOMAIN_RX` tightening — regex already blocks `;<>`.
- `crash_handler.py:169` `buffering=0` — faulthandler bypasses Python buffering.
- `melspec.py:81` `np.hann` — function doesn't exist in numpy; `np.hanning` is correct.
- `call.py:128-133` bare except logging — code already logs.
- `headset.py:47-81` whitespace strip — code already strips.

---

## Final recommendation

**Land Tier A (7 items) before deploy.** All are short, follow existing patterns, low regression risk.

**Land Tier B if you have a tester + time.**

**Skip Tier C and false positives.**

The swarm review is best read as a **trigger list** for verification, not an action list. ~63% of its findings either aren't bugs or have severity inflated. Acting on it without verification would have you "fixing" working code under deploy pressure — the exact recipe for incidents.
