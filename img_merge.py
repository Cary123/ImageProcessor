#!/usr/bin/env python3
"""Merge multiple layer images into one transparent PNG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from image_processor.core.image_engine import EngineError, export_image, merge_layers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge multiple layer images into one PNG with transparency.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Layers are merged in order: the first image is the bottom layer,\n"
            "the last image is the top layer. All images must have the same size.\n"
            "\n"
            "Example:\n"
            "  python img_merge.py images/1.png images/2.png images/3.png -o output/merged.png"
        ),
    )
    parser.add_argument(
        "images",
        nargs="+",
        help="Layer image paths, from bottom to top",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="merged.png",
        help="Output PNG path (default: merged.png)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_paths = [Path(path).expanduser().resolve() for path in args.images]
    output_path = Path(args.output).expanduser().resolve()

    try:
        merged = merge_layers(input_paths)
        export_image(merged, output_path, format="PNG")
        print(
            f"Merged {len(input_paths)} layers -> {output_path} "
            f"({merged.width}x{merged.height})"
        )
        return 0
    except EngineError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
