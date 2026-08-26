#!/usr/bin/env python3

import json
import sys

from worker import discover_all_printers


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: discover_printers.py <network-or-networks>",
            file=sys.stderr,
        )
        return 2

    discovery_networks = sys.argv[1].strip()

    if not discovery_networks:
        print(
            "Printer discovery network(s) are required.",
            file=sys.stderr,
        )
        return 2

    try:
        printers = discover_all_printers(
            discovery_networks
        )
    except Exception as exc:
        print(
            f"Printer discovery failed: {exc}",
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            printers,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
