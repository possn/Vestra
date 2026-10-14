#!/usr/bin/env python3
"""Render matching Vestra 2.0 mobile assets from the canonical SVG mark."""
from pathlib import Path
import cairosvg

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"vestra-icon-2026.svg"
ICONS={
 "apple-touch-icon.png":180,
 "apple-touch-icon-120.png":120,
 "apple-touch-icon-152.png":152,
 "apple-touch-icon-167.png":167,
 "icon192.png":192,
 "icon512.png":512,
 "icon192-maskable.png":192,
 "icon512-maskable.png":512,
}
def main():
    for name,size in ICONS.items():
        cairosvg.svg2png(url=str(SOURCE),write_to=str(ROOT/name),output_width=size,output_height=size)
        print(f"{name}: {size}x{size}")
if __name__=="__main__":
    main()
