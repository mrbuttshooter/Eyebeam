# Packaged EXE SIP Smoke Diagnostic

## Context

NOC_Beam can now build a native Windows `NOC_Beam.exe` with the bundled
custom `pjsua2` extension, but the release artifact still needs an explicit
machine-checkable proof that it is not a UI-only executable. The existing
source-level import check proves the development environment can import
PJSIP. It does not prove the uploaded PyInstaller artifact contains the
native binding, prefers it over a public wheel, and can create/destroy a
PJSIP endpoint without launching the GUI.

The next release-blocking upgrade is a non-GUI packaged executable smoke mode.

Approval: self-approved under the user's delegated instruction on
2026-05-15 to keep upgrading without waiting for another approval gate.

## Goals

- Add a CLI diagnostic path that works in the packaged `NOC_Beam.exe`.
- Prove the executable loaded the bundled custom native `pjsua2`, not the
  fallback public wheel and not the UI-only stub.
- Prove PJSIP can create and destroy an `Endpoint` inside the packaged app.
- Emit structured JSON that CI and the local build script can validate.
- Keep the check offline: no SIP registration, no DNS dependency, no carrier
  credentials, and no media device requirement.

## Non-Goals

- Real account registration or call placement.
- Installer creation, signing, or Windows product metadata.
- Codec negotiation with a remote SIP server.
- Replacing the user-facing Diagnostics page.

## Approaches Considered

### Recommended: CLI flag in the main executable

Add `NOC_Beam.exe --sip-smoke --sip-smoke-output <path>`. The flag runs before
Qt starts, writes a JSON report, and exits with `0` on success or non-zero on
failure.

This is the strongest release gate because it exercises the exact executable
we ship. The output file is necessary because the PyInstaller target is a
windowed executable, so stdout is not reliable in CI.

### Separate console helper executable

Build a second PyInstaller console binary such as `NOC_Beam_Smoke.exe`.
This gives convenient terminal output, but it tests a different artifact and
adds release packaging surface.

### Source-only Python smoke

Run `python -m noc_beam --sip-smoke` after installing the package. This is
useful for developers but insufficient as a release gate because it bypasses
PyInstaller packaging.

## Design

### Loader source reporting

`noc_beam.sip._pjsua2_loader` will continue exporting `pj` and
`PJSUA2_AVAILABLE`. It will also expose:

- `PJSUA2_SOURCE`: one of `native`, `wheel`, or `stub`.
- `PJSUA2_LOAD_ERROR`: the final import error string for diagnostics.

Existing callers keep working unchanged. The new smoke check uses the source
field to fail hard unless the packaged executable loaded `native`.

### Smoke runner

Add `noc_beam.sip.smoke.run_sip_smoke(require_native=True)`.

The function returns `(exit_code, payload)` where `payload` is JSON-serializable
and includes:

- `ok`
- `source`
- `available`
- `native_required`
- `endpoint_created`
- `endpoint_destroyed`
- `pjsip_version`
- `errors`

The check imports the loader, verifies native source when required, constructs
`pj.Endpoint()`, calls `libCreate()`, reads `libVersion().full` when available,
and calls `libDestroy()` in a best-effort cleanup path.

### CLI entry point

`noc_beam.__main__.main()` will parse only the smoke flags first:

- `--sip-smoke`
- `--sip-smoke-output <path>`

When `--sip-smoke` is present, it does not import or start the Qt app. It writes
the report to the requested path, or stdout for source-level developer use, then
returns the smoke exit code. Normal GUI startup remains unchanged.

### Build and CI gates

The local Windows build script will run the packaged smoke after PyInstaller
for full native builds unless explicitly skipped with `-SkipPackagedSmoke`.
The GitHub Actions Windows workflow will run the same check in `full` mode after
building `dist\NOC_Beam.exe` and before uploading the artifact.

Both gates validate at least:

- process exit code is `0`
- JSON file exists
- `ok` is `true`
- `source` is `native`
- `endpoint_created` is `true`
- `endpoint_destroyed` is `true`
- `pjsip_version` is non-empty

## Error Handling

Smoke failures are explicit and structured. Import failures, wrong source,
endpoint construction failures, `libCreate()` failures, version lookup failures,
and cleanup failures are captured in `errors`. Cleanup failures fail the smoke
because an endpoint that cannot shut down cleanly is not release-ready.

The local build script prints the smoke JSON before throwing. CI uploads normal
build logs on failure through the existing failure artifact path.

## Testing

Unit tests will cover:

- Native source required but loader source is `stub` fails.
- Native source with a fake endpoint succeeds and records version/cleanup.
- Endpoint creation failure returns non-zero and records the error.
- JSON report writing produces UTF-8 JSON.
- CLI smoke mode routes to the smoke runner without importing the GUI app.

Verification will include:

- Focused pytest for smoke tests.
- Full pytest suite.
- Full local Windows build.
- Running the packaged `dist\NOC_Beam.exe --sip-smoke --sip-smoke-output ...`
  against the rebuilt executable.

## Self-Review

- No placeholders remain.
- The scope is one release gate: prove packaged native SIP initialization.
- The design does not require network, SIP credentials, or audio devices.
- The JSON output file handles the windowed PyInstaller executable correctly.
- Normal GUI startup remains unchanged unless `--sip-smoke` is passed.
