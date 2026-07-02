#!/usr/bin/env python3
"""Generate a sprite sheet from a folder of images."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from image_processor.core.image_engine import EngineError, export_image, create_sprite_sheet
from image_processor.utils.helpers import collect_images


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a sprite sheet from a folder of images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "All supported images in the input directory are arranged into a grid.\n"
            "\n"
            "Example:\n"
            "  python img_sprite.py -i ./images -o ./output/sprite.png -s 10 -c 4\n"
            "  python img_sprite.py -i ./images -o ./output/sprite.png --json output/sprite.json"
        ),
    )
    parser.add_argument("-i", "--input", required=True, help="Input image directory")
    parser.add_argument("-o", "--output", required=True, help="Output sprite PNG path")
    parser.add_argument(
        "-s",
        "--spacing",
        type=int,
        default=0,
        help="Spacing between images in pixels (default: 0)",
    )
    parser.add_argument(
        "-p",
        "--padding",
        type=int,
        default=0,
        help="Padding around each image in pixels (default: 0)",
    )
    parser.add_argument(
        "-c",
        "--cols",
        type=int,
        default=None,
        help="Number of columns (default: auto-calculate best grid)",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="Optional path to write TexturePacker-compatible JSON metadata",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.spacing < 0 or args.padding < 0:
        print("Error: spacing and padding must be >= 0", file=sys.stderr)
        return 1

    input_dir = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    try:
        paths = collect_images(input_dir)
        if not paths:
            raise EngineError(f"No supported image files found in: {input_dir}")

        sprite, frames = create_sprite_sheet(
            paths, cols=args.cols, spacing=args.spacing, padding=args.padding, sort_by="name"
        )
        export_image(sprite, output_path, format="PNG")

        if args.json_path:
            json_path = Path(args.json_path).expanduser().resolve()
            json_path.parent.mkdir(parents=True, exist_ok=True)
            metadata = {
                "frames": frames,
                "meta": {
                    "version": "1.0",
                    "size": {"w": sprite.width, "h": sprite.height},
                    "image": output_path.name,
                },
            }
            json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            print(f"Metadata saved: {json_path}")

        print(
            f"Sprite saved: {output_path} "
            f"({sprite.width}x{sprite.height}, {len(paths)} images, "
            f"spacing={args.spacing}px, padding={args.padding}px)"
        )
        return 0
    except EngineError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
