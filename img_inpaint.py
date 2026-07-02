#!/usr/bin/env python3
"""Content-aware inpaint using OpenCV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from image_processor.core.image_engine import EngineError, export_image, inpaint_image


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove selected region from an image using OpenCV inpainting.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Mask must be a grayscale image where white pixels mark the region to erase.\n"
            "\n"
            "Example:\n"
            "  python img_inpaint.py -i images/photo.png -m images/mask.png -o output/photo.png\n"
            "  python img_inpaint.py -i images/photo.png -m images/mask.png -o output/photo.png --method TELEA -r 5"
        ),
    )
    parser.add_argument("-i", "--input", required=True, help="Input image path")
    parser.add_argument("-m", "--mask", required=True, help="Mask image path (grayscale)")
    parser.add_argument("-o", "--output", required=True, help="Output image path")
    parser.add_argument(
        "--method",
        choices=["NS", "TELEA"],
        default="NS",
        help="Inpainting method: NS (Navier-Stokes) or TELEA (Fast Marching, default: NS)",
    )
    parser.add_argument(
        "-r",
        "--radius",
        type=int,
        default=3,
        help="Inpainting radius (default: 3)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    mask_path = Path(args.mask).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if args.radius < 1:
        print("Error: radius must be >= 1", file=sys.stderr)
        return 1

    try:
        result = inpaint_image(input_path, mask_path, radius=args.radius, method=args.method)
        export_image(result, output_path)
        print(f"Inpainted: {output_path} ({result.width}x{result.height}, method={args.method}, radius={args.radius})")
        return 0
    except EngineError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
