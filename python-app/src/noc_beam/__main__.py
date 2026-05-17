"""NOC_Beam entry point."""
from __future__ import annotations

import argparse
import json
import sys


def _parse_smoke_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--sip-smoke", action="store_true")
    parser.add_argument("--sip-smoke-output")
    parser.add_argument("--fas-smoke", action="store_true")
    parser.add_argument("--fas-smoke-output")
    parser.add_argument("--fas-demo", action="store_true",
                        help="Score 7 synthetic FAS scenarios using bundled models")
    args, _remaining = parser.parse_known_args(argv[1:])
    return args


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    smoke_args = _parse_smoke_args(argv)
    if smoke_args.sip_smoke:
        from noc_beam.sip.smoke import run_sip_smoke, write_smoke_report

        exit_code, report = run_sip_smoke(require_native=True)
        if smoke_args.sip_smoke_output:
            write_smoke_report(smoke_args.sip_smoke_output, report)
        else:
            print(json.dumps(report, indent=2, sort_keys=True))
        return exit_code

    if smoke_args.fas_smoke:
        from noc_beam.audio.fas_smoke import run_fas_smoke, write_smoke_report

        exit_code, report = run_fas_smoke()
        if smoke_args.fas_smoke_output:
            write_smoke_report(smoke_args.fas_smoke_output, report)
        else:
            print(json.dumps(report, indent=2, sort_keys=True))
        return exit_code

    if smoke_args.fas_demo:
        from noc_beam.audio.fas_demo import run_fas_demo

        return run_fas_demo()

    from noc_beam.app import run

    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
