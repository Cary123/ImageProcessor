#!/usr/bin/env python3
"""Remove image background and export transparent PNG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from image_processor.core.image_engine import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    EngineError,
    export_image,
    remove_background,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove image background and keep the subject with transparency.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python img_matting.py -i images/image.png -o output/image.png\n"
            "  python img_matting.py -i images/icon.png -o output/icon.png -m u2netp --trim\n"
            "  python img_matting.py -i images/person.png -o output/person.png "
            "-m u2net_human_seg --alpha-matting\n"
            "\n"
            f"Available models include: {', '.join(AVAILABLE_MODELS[:8])}, ..."
        ),
    )
    parser.add_argument("-i", "--input", required=True, help="Input image path")
    parser.add_argument("-o", "--output", required=True, help="Output PNG path")
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        choices=AVAILABLE_MODELS,
        help=f"Background removal model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--alpha-matting",
        action="store_true",
        help="Enable alpha matting for smoother edges (slower)",
    )
    parser.add_argument(
        "--alpha-matting-foreground-threshold",
        type=int,
        default=240,
        help="Alpha matting foreground threshold (default: 240)",
    )
    parser.add_argument(
        "--alpha-matting-background-threshold",
        type=int,
        default=10,
        help="Alpha matting background threshold (default: 10)",
    )
    parser.add_argument(
        "--alpha-matting-erode-size",
        type=int,
        default=10,
        help="Alpha matting erode size (default: 10)",
    )
    parser.add_argument(
        "--post-process-mask",
        action="store_true",
        help="Post-process the mask for cleaner edges",
    )
    parser.add_argument(
        "--only-mask",
        action="store_true",
        help="Output only the alpha mask as grayscale PNG",
    )
    parser.add_argument(
        "--trim",
        action="store_true",
        help="Crop transparent borders after matting",
    )
    parser.add_argument(
        "--trim-padding",
        type=int,
        default=0,
        help="Extra pixels to keep around subject when using --trim (default: 0)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.trim_padding < 0:
        print("Error: --trim-padding must be >= 0", file=sys.stderr)
        return 1

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    try:
        image = remove_background(
            input_path,
            model=args.model,
            alpha_matting=args.alpha_matting,
            alpha_matting_foreground_threshold=args.alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=args.alpha_matting_background_threshold,
            alpha_matting_erode_size=args.alpha_matting_erode_size,
            post_process_mask=args.post_process_mask,
            only_mask=args.only_mask,
            trim=args.trim,
            trim_padding=args.trim_padding,
            progress_callback=lambda p: print(f"Progress: {p * 100:.0f}%", end="\r", flush=True),
        )
        export_image(image, output_path, format="PNG")
        print(f"\nSaved: {output_path} ({image.width}x{image.height}, model={args.model})")
        return 0
    except EngineError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
