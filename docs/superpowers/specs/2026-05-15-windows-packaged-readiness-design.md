# Windows Packaged Readiness

## Context

The packaged executable now proves native PJSIP startup, transports, and codecs.
The next readiness gap is Windows product polish around that artifact and the
default shell accessibility experience. Manual workflow dispatch still defaults
to a UI-only build, the executable has no Windows version resource, and the
default `PhoneShell` saves accessibility settings without applying high contrast
live.

Approval: self-approved under the user's delegated instruction on 2026-05-15 to
continue product-hardening without waiting for another approval gate.

## Goals

- Make manual GitHub Actions dispatch default to the native/full build.
- Add Windows version metadata to `NOC_Beam.exe`.
- Emit a SHA-256 checksum next to the built executable and upload it with the
  artifact.
- Apply high contrast/theme settings immediately from the default `PhoneShell`
  settings dialog.
- Restore visible keyboard focus on the default bottom tabs and wide-shell rail.

## Non-Goals

- Code signing certificate integration.
- MSI/NSIS installer.
- Full accessibility audit of every custom row.
- Reworking the existing `phone_shell.py` style backlog.

## Design

### Release Defaults And Checksums

The workflow `workflow_dispatch` default becomes `full`, matching the current
release intent. The build script writes `dist/NOC_Beam.exe.sha256` after the
packaged smoke passes. CI uploads both the executable and checksum.

### Windows Version Resource

Add a PyInstaller version resource file under `python-app/build/` with
`FileDescription`, `ProductName`, `CompanyName`, `FileVersion`, and
`ProductVersion`. The spec points `version=` to that file. Version values match
the current package version `0.1.0`.

### Live Accessibility Settings

`PhoneShell._on_settings()` already mutates and saves settings. It will also
call a small helper that applies `theme.apply_theme()` to the current
`QApplication` using the updated appearance settings. If a wide dashboard window
is already open, its trace drawer reduced-motion setting is updated as well.

### Focus Visibility

QSS rules that hide focus on the default bottom tabs and wide-shell rail buttons
will be replaced with visible focus borders. High contrast uses the existing
yellow focus token.

## Testing

- Unit/Qt test `PhoneShell._on_settings()` calls `apply_theme()` with the
  updated high-contrast value.
- Text test verifies the PyInstaller spec references the version resource and
  the version file contains product metadata.
- Text test verifies the workflow default is `full`.
- Run focused tests, full pytest, rebuild, packaged SIP smoke, and GUI smoke.

## Self-Review

- No placeholders remain.
- The slice stays within Windows packaged readiness and default-shell
  accessibility.
- Signing/installer work is explicitly deferred.
