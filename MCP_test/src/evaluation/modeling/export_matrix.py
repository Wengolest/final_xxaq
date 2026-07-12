"""Export modeling wide table from eval CSV."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    df = pd.read_csv(args.csv, encoding="utf-8-sig")
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"Exported {len(df)} rows -> {args.out}")


if __name__ == "__main__":
    main()
