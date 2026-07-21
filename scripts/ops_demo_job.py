#!/usr/bin/env python3
"""Tiny monitored job used only to validate the operations loop."""
from __future__ import annotations

import argparse
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--sleep", type=float, default=2.0)
    args = parser.parse_args()
    for index in range(1, args.steps + 1):
        time.sleep(args.sleep)
        print(f"PROGRESS {index}/{args.steps}", flush=True)
        print(f"METRIC demo_fraction={index / args.steps:.6f}", flush=True)


if __name__ == "__main__":
    main()
