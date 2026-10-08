"""E02: E01 with exact+events-tier play coverage and a wider sigma grid (experiments/protocols/E02-protocol.md).

    uv run python -m cfb.evaluation.e02
"""

from cfb.evaluation.e01 import main

if __name__ == "__main__":
    main("states-rating.parquet", (2.0, 3.0, 4.0, 6.0), "E02")
