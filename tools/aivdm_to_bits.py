from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ais_scenario_toolkit.aivdm_decode import AivdmFragmentAssembler


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert AIVDM/AIVDO sentences to AIS payload bit strings.")
    parser.add_argument("sentences", nargs="*", help="AIVDM/AIVDO sentences. Reads stdin if omitted.")
    parser.add_argument("--ignore-checksum", action="store_true")
    args = parser.parse_args()

    lines = args.sentences or [line.strip() for line in sys.stdin if line.strip()]
    assembler = AivdmFragmentAssembler(ignore_checksum=args.ignore_checksum)
    for line in lines:
        bits = assembler.add(line)
        if bits is not None:
            print(bits)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
