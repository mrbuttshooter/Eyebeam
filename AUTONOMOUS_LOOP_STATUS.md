# Autonomous Loop Status

## Bug 1: retry storm cap — FIXED in `python-app/src/noc_beam/sip/registration_retry.py`

Field log showed an account at 503 racking up 1180+ retries at 30 s intervals
over 9 hours. Added:

- `MAX_FAST_RETRIES = 60` (≈30 min at the 30 s cap)
- `LONG_SLEEP_INTERVAL_MS = 15 * 60 * 1000`
- After `MAX_FAST_RETRIES`, interval switches to long-sleep, indefinitely.
- One-shot WARNING log on the transition.
- New tests in `tests/test_registration_retry.py`.

## Bug 2: "Active supplier changed" spam — TRACED, fix is OUT OF LANE

The retry path is NOT emitting the supplier signal itself. The chain is
legitimate but the UI is over-reacting to every retry tick:

```
registration_retry._do_retry  (registration_retry.py:104)
  └─> acc.setRegistration(True)
        └─> PJSIP fires registration_changed (still 5xx)
              └─> phone_shell._on_registration_changed   (phone_shell.py:1536)
                    └─> if account_id == self._active_account_id:
                          _set_active_account(account_id, label)   (phone_shell.py:864)
                                └─> _refresh_supplier_picker()      (phone_shell.py:885)
                                      └─> if kind == "teles" and combo idx >= 0:
                                            QTimer.singleShot(0, lambda: _on_supplier_changed(...))
                                                                          (phone_shell.py:940)
                                                  └─> log.info "Active supplier changed -> id=..."
                                                                          (phone_shell.py:1100)
```

### Root cause
`phone_shell._set_active_account` is invoked on **every** `registration_changed`
event for the currently-selected account. It then unconditionally calls
`_refresh_supplier_picker`, which (for `teles` switch type) schedules
`_on_supplier_changed` via `QTimer.singleShot(0, ...)`. That handler
unconditionally logs `"Active supplier changed -> id=..."`. With a 503-pinned
account this fires every 30 s for hours.

### Suggested fix (in `phone_shell.py`, NOT registration_retry)
Two reasonable options:

1. **Cheapest**: in `_on_registration_changed`, only call `_set_active_account`
   when the **health** bucket (ok / danger / muted) actually changes — track
   the last-rendered health per account_id and skip the chip rebuild if
   unchanged. The supplier picker only needs to refresh when the active
   account changes, not on every failed-registration tick.

2. **More targeted**: split `_set_active_account` into
   `_render_chip(account_id, label, code)` (cheap, idempotent) and a real
   `_set_active_account` (only called on actual account-selection changes).
   `_on_registration_changed` should call the chip renderer, not the full
   account-switch path.

The retry path itself is correct — fixing it in `registration_retry.py` would
mask the real bug (any source of repeated registration_changed events would
cause the same spam, e.g. carrier flapping between 200 and 503).

A comment trail describing this chain was added in `registration_retry._do_retry`.
