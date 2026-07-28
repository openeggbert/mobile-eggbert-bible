#!/usr/bin/env python3
"""
render_level_map.py -- renders a real worlds/*.txt level's numeric Decor
grid as a color-coded collision/gameplay-classification diagram, built
entirely from real level data and the real `Is*()` predicate bodies in
Decor.cpp. This is explicitly a DATA RECONSTRUCTION, not a screenshot of
rendered game graphics (the visible background art comes from a separate
pre-rendered image via Pixmap::BackgroundCache, not from these icon
numbers -- see Decor.cpp:250 and PLAN.md's "important finding").

Level file format (read from worlds/world001.txt and confirmed against
Worlds.cpp):
    DescFile: posDecor=X;Y dimDecor=W;H world=.. music=.. region=.. blupiPos=X;Y blupiDir=..
    Decor:
    <W comma-separated icon values, one line per row, H rows>
    An empty comma slot means icon == -1 (no tile) -- Worlds.cpp:33
    ("Decor parsing treats an empty comma slot as -1 (no tile).").

Classification (read from the real `bool Decor::Is*()` predicate bodies,
Decor.cpp:7195-7540ish -- each predicate below is a single-icon or
icon-range equality test on `m_decor[x][y].icon`, transcribed verbatim):

    IsLave        icon == 68                          lava
    IsPiege       icon == 373                         trap
    IsGoutte      icon == 404 or icon == 410           drip/leak
    IsScie        icon == 378                          saw blade
    IsSwitch      icon == 384 or icon == 385            switch
    IsEcraseur    icon == 317                          crusher
    IsBlitz       icon == 305                          electric hazard ("blitz")
    IsRessort     icon == 211                          spring
    IsTemp        icon == 324                          blinking/temporary floor
    IsBridge      icon == 364                          bridge
    IsDoor        334 <= icon <= 336                    door
    IsTeleporte   330 <= icon <= 333                    teleporter
    IsSurfWater / icon == 91                            surf-depth water
    IsDeepWater   icon == 92                            deep water
    IsPassIcon /  icon in [0, MAXQUART=441): all 16      generic solid ground / wall
    IsBlocIcon    table_decor_quart[icon*16+i] entries   ("blocking" if any
                  are nonzero, else "passable decoration")
    (icon == -1)                                         empty / no tile
    (icon >= MAXQUART, no other match)                   outside table_decor_quart's
                                                          range -- IsPassIcon's default
                                                          branch always returns true for
                                                          these, IsBlocIcon always false,
                                                          so they behave as passable but
                                                          are flagged distinctly here since
                                                          their gameplay meaning (if any) is
                                                          not covered by table_decor_quart.

The hazard-specific categories above are checked first (matching how the
game itself asks "is this lava / is this a switch" as an independent,
higher-priority question), then the generic solid-ground/passable split
is applied to whatever remains. This priority order is a presentation
choice made for this diagram, not a single verbatim Decor.cpp function --
documented here explicitly.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from me_tables import parse_shortcs_tables  # noqa: E402

DEFAULT_ME_ROOT = "/workspace/mobile-eggbert"
DEFAULT_OUT_DIR = str(Path(__file__).resolve().parent.parent / "book" / "images")
DEFAULT_WORLDS = ["world001", "world055", "world120"]

MAXQUART = 441
FONT = ImageFont.load_default()

# (category_key, test_fn(icon) -> bool, label, RGB color)
# Order matters: first match wins.
SPECIAL_CATEGORIES: List[Tuple[str, "callable", str, Tuple[int, int, int]]] = [
    ("empty",      lambda ic: ic == -1,                 "empty (no tile)",             (255, 255, 255)),
    ("lava",       lambda ic: ic == 68,                  "lava (IsLave)",               (220, 40, 20)),
    ("trap",       lambda ic: ic == 373,                 "trap (IsPiege)",              (200, 120, 0)),
    ("drip",       lambda ic: ic in (404, 410),          "drip/leak (IsGoutte)",        (0, 170, 170)),
    ("saw",        lambda ic: ic == 378,                 "saw blade (IsScie)",          (70, 70, 70)),
    ("switch",     lambda ic: ic in (384, 385),          "switch (IsSwitch)",           (240, 220, 0)),
    ("crusher",    lambda ic: ic == 317,                 "crusher (IsEcraseur)",        (140, 0, 160)),
    ("blitz",      lambda ic: ic == 305,                 "electric hazard (IsBlitz)",   (60, 140, 255)),
    ("spring",     lambda ic: ic == 211,                 "spring (IsRessort)",          (40, 200, 90)),
    ("temp",       lambda ic: ic == 324,                 "blinking floor (IsTemp)",     (230, 0, 200)),
    ("bridge",     lambda ic: ic == 364,                 "bridge (IsBridge)",           (150, 100, 40)),
    ("door",       lambda ic: 334 <= ic <= 336,          "door (IsDoor)",               (255, 200, 40)),
    ("teleporter", lambda ic: 330 <= ic <= 333,          "teleporter (IsTeleporte)",    (170, 60, 220)),
    ("surfwater",  lambda ic: ic == 91,                  "surf-depth water (IsSurfWater)", (110, 190, 240)),
    ("deepwater",  lambda ic: ic == 92,                  "deep water (IsDeepWater)",    (20, 60, 160)),
]

BLOCKING_COLOR = (120, 120, 120)     # generic solid ground / wall (IsBlocIcon)
PASSABLE_COLOR = (222, 238, 210)     # generic passable decoration (IsPassIcon, in-range)
UNCLASSIFIED_COLOR = (255, 105, 180)  # icon >= MAXQUART, not otherwise special-cased


def classify_icon(icon: int, decor_quart: List[int]) -> Tuple[str, str, Tuple[int, int, int]]:
    for key, test, label, color in SPECIAL_CATEGORIES:
        if test(icon):
            return key, label, color
    if 0 <= icon < MAXQUART:
        base = icon * 16
        blocking = any(decor_quart[base + i] != 0 for i in range(16))
        if blocking:
            return "blocking", "solid ground/wall (IsBlocIcon)", BLOCKING_COLOR
        return "passable", "passable decoration (IsPassIcon)", PASSABLE_COLOR
    return "unclassified", f"icon >= {MAXQUART} (outside table_decor_quart range)", UNCLASSIFIED_COLOR


def parse_world_file(path: Path) -> Tuple[dict, List[List[int]]]:
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    header = {}
    if lines and lines[0].startswith("DescFile:"):
        for key, val in re.findall(r"(\w+)=([^\s]+)", lines[0]):
            header[key] = val
    try:
        decor_idx = next(i for i, l in enumerate(lines) if l.strip() == "Decor:")
    except StopIteration:
        raise ValueError(f"{path}: no 'Decor:' section found")
    dim_w, dim_h = (int(x) for x in header.get("dimDecor", "100;100").split(";"))
    grid: List[List[int]] = []
    for line in lines[decor_idx + 1: decor_idx + 1 + dim_h]:
        cells = line.split(",")
        row = [(-1 if c.strip() == "" else int(c)) for c in cells if c != "" or True]
        # Real files emit a trailing empty token after the final comma; trim
        # it if the row is exactly one cell longer than dim_w.
        if len(row) == dim_w + 1 and row[-1] == -1:
            row = row[:-1]
        grid.append(row)
    if len(grid) != dim_h:
        raise ValueError(f"{path}: expected {dim_h} Decor rows, found {len(grid)}")
    for r in grid:
        if len(r) != dim_w:
            raise ValueError(f"{path}: expected {dim_w} columns, found {len(r)} in a row")
    return header, grid


def render_level_map(header: dict, grid: List[List[int]], decor_quart: List[int],
                      title: str) -> Image.Image:
    h = len(grid)
    w = len(grid[0])
    cell = 6
    margin_top = 56
    legend_w = 260
    img_w = w * cell + legend_w
    img_h = max(h * cell, 20) + margin_top
    img = Image.new("RGB", (img_w, img_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, img_w, margin_top], fill=(25, 25, 30))
    draw.text((8, 4), title, font=FONT, fill=(255, 255, 255))
    draw.text((8, 18), "RECONSTRUCTED from real level data (worlds/*.txt) and Decor.cpp Is*() "
                        "collision predicates.", font=FONT, fill=(255, 210, 90))
    draw.text((8, 30), "NOT a screenshot of rendered game graphics -- visible background art comes "
                        "from a separate pre-rendered image (Pixmap::BackgroundCache).",
              font=FONT, fill=(255, 210, 90))
    meta = " ".join(f"{k}={v}" for k, v in header.items())
    draw.text((8, 42), meta[:200], font=FONT, fill=(160, 160, 170))

    used_categories: Dict[str, Tuple[str, Tuple[int, int, int]]] = {}
    for y, row in enumerate(grid):
        for x, icon in enumerate(row):
            key, label, color = classify_icon(icon, decor_quart)
            used_categories[key] = (label, color)
            if key == "empty":
                continue  # leave background white, no need to paint
            px = x * cell
            py = margin_top + y * cell
            draw.rectangle([px, py, px + cell - 1, py + cell - 1], fill=color)

    grid_area_right = w * cell
    draw.line([(grid_area_right, 0), (grid_area_right, img_h)], fill=(0, 0, 0), width=1)
    lx = grid_area_right + 12
    ly = margin_top
    draw.text((lx, ly), "Legend", font=FONT, fill=(0, 0, 0))
    ly += 16
    all_cats = SPECIAL_CATEGORIES + [
        ("blocking", None, "solid ground/wall (IsBlocIcon)", BLOCKING_COLOR),
        ("passable", None, "passable decoration (IsPassIcon)", PASSABLE_COLOR),
        ("unclassified", None, f"icon >= {MAXQUART} (unclassified)", UNCLASSIFIED_COLOR),
    ]
    for key, _test, label, color in all_cats:
        if key not in used_categories:
            continue
        draw.rectangle([lx, ly, lx + 12, ly + 12], fill=color, outline=(0, 0, 0))
        draw.text((lx + 18, ly + 1), label, font=FONT, fill=(0, 0, 0))
        ly += 16
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--me-root", default=DEFAULT_ME_ROOT)
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--worlds", nargs="*", default=DEFAULT_WORLDS,
                     help="world file stems (without .txt) under <me-root>/worlds/")
    args = ap.parse_args()

    me_root = Path(args.me_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tables_cpp = me_root / "src/WindowsPhoneSpeedyBlupi/Tables.cpp"
    tables = parse_shortcs_tables(tables_cpp)
    decor_quart = tables["table_decor_quart"]
    assert len(decor_quart) == 7056, f"table_decor_quart: expected 7056 entries, got {len(decor_quart)}"

    manifest: List[dict] = []
    for stem in args.worlds:
        world_path = me_root / "worlds" / f"{stem}.txt"
        if not world_path.exists():
            print(f"[levelmap] SKIP {stem}: {world_path} not found")
            continue
        header, grid = parse_world_file(world_path)
        title = f"{stem}.txt — {header.get('dimDecor', '?')} tile grid, world={header.get('world', '?')}"
        img = render_level_map(header, grid, decor_quart, title)
        out_name = f"level-map-{stem}.png"
        img.save(out_dir / out_name)
        unique_icons = sorted({ic for row in grid for ic in row})
        manifest.append(dict(
            file=out_name,
            source=f"worlds/{stem}.txt (real level data) + Decor::Is*() predicates + "
                    f"Tables::table_decor_quart (Tables.cpp)",
            desc=f"Reconstructed collision/classification map of {stem}.txt's 100x100 Decor grid "
                 f"({len(unique_icons)} distinct icon values present, range "
                 f"{min(unique_icons)}..{max(unique_icons)}). Not a screenshot.",
        ))
        print(f"[levelmap] wrote {out_name} ({len(unique_icons)} distinct icons)")

    from manifest_writer import write_fragment, build_manifest
    write_fragment(out_dir, "levelmap", manifest)
    build_manifest(out_dir)
    print(f"[done] {len(manifest)} level-map images recorded")


if __name__ == "__main__":
    main()
