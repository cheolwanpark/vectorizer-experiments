#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def fail(message: str) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(1)


def sanitize_ir_text(text: str, triple: str | None, datalayout: str | None) -> str:
    if triple:
        text, count = re.subn(
            r'^target triple = "[^"]*"$',
            f'target triple = "{triple}"',
            text,
            count=1,
            flags=re.M,
        )
        if count == 0:
            fail("could not find target triple in IR")

    if datalayout:
        text, count = re.subn(
            r'^target datalayout = "[^"]*"$',
            f'target datalayout = "{datalayout}"',
            text,
            count=1,
            flags=re.M,
        )
        if count == 0:
            fail("could not find target datalayout in IR")

    text = re.sub(r'\s+"target-cpu"="[^"]*"', "", text)
    text = re.sub(r'\s+"target-features"="[^"]*"', "", text)
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--triple")
    parser.add_argument("--datalayout")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    text = input_path.read_text(encoding="utf-8")
    text = sanitize_ir_text(text, args.triple, args.datalayout)
    output_path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
