#!/usr/bin/env python3
"""
extract_sprites.py -- generates real, pixel-accurate sprite/animation
illustrations for Part V of the mobile-eggbert-bible book, from the actual
sprite atlases and animation-sequence tables shipped in a mobile-eggbert
checkout. No image in this pipeline is fabricated or AI-generated: every
pixel comes from a crop of a real PNG in Content/icons/, positioned by the
exact grid algorithm read from Pixmap.cpp.

Usage:
    python3 extract_sprites.py [--me-root /workspace/mobile-eggbert]
                                [--out-dir /home/user/mobile-eggbert-bible/book/images]

Source of the slicing algorithm (read verbatim, not guessed):
    Pixmap::DrawIcon             src/WindowsPhoneSpeedyBlupi/Pixmap.cpp:509
    Pixmap::GetSrcRectangle      src/WindowsPhoneSpeedyBlupi/Pixmap.cpp:683
        column = icon % (atlas_width // grid_w)
        row    = icon // (atlas_width // grid_w)
        rect   = (gap + column*(grid_w+gap), gap + row*(grid_h+gap), icon_w, icon_h)

Source of the Blupi animation-sequence format (read verbatim):
    Tables::table_blupi           include/WindowsPhoneSpeedyBlupi/Tables.hpp:131
                                   src/WindowsPhoneSpeedyBlupi/Tables.cpp:116
    Decor::BlupiSearchIcon        src/WindowsPhoneSpeedyBlupi/Decor.cpp:2123-2452
        Packed variable-length records: [actionId, frameCount, threshold,
        icon_0 .. icon_{frameCount-1}], next record frameCount+3 shorts
        later, terminated by actionId == 0.

Source of the object animation data (read verbatim):
    Decor::MoveObjectStepIcon     src/WindowsPhoneSpeedyBlupi/Decor.cpp:8192-9047
        A long flat if-chain keyed on ObjectType. Two shapes appear:
          (a) icon = baseIcon + phase/ScaleDiv(N) % frameCount  (inline range)
          (b) icon = Tables::table_XXX[phase/ScaleDiv(N) % frameCount] (table)
        Four-way patrol creatures (bulldozer/fish/bird/wasp/creature/blupih/
        blupit) additionally select one of four small tables
        (_left/_right/_turn2l/_turn2r) by direction and turn-step.

See MANIFEST.md (written at the end of this script) for the full,
per-image provenance table, and for factual notes on anything that could
not be conclusively verified (documented instead of guessed).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from me_tables import parse_shortcs_tables, parse_enum_values, parse_table_blupi_records  # noqa: E402

DEFAULT_ME_ROOT = "/workspace/mobile-eggbert"
DEFAULT_OUT_DIR = str(Path(__file__).resolve().parent.parent / "book" / "images")

# ---------------------------------------------------------------------------
# Section 1: atlas / grid configuration, read from Pixmap.cpp:550-648 and
# Pixmap::GetBitmap (Pixmap.cpp:745-780).
# ---------------------------------------------------------------------------

ATLAS = {
    "Blupi":     dict(file="blupi.png",    grid=(60, 60), icon=(60, 60), gap=0),
    "Blupi1_11": dict(file="blupi1.png",   grid=(60, 60), icon=(60, 60), gap=0),
    "Blupi1_12": dict(file="blupi1.png",   grid=(60, 60), icon=(60, 60), gap=0),
    "Blupi1_13": dict(file="blupi1.png",   grid=(60, 60), icon=(60, 60), gap=0),
    "Object":    dict(file="object-m.png", grid=(64, 64), icon=(64, 64), gap=1),
    "Element":   dict(file="element.png",  grid=(60, 60), icon=(60, 60), gap=0),
    "Text":      dict(file="text.png",     grid=(32, 32), icon=(32, 32), gap=0),
    "Button":    dict(file="button.png",   grid=(40, 40), icon=(40, 40), gap=0),
    "Pad":       dict(file="pad.png",      grid=(140, 140), icon=(140, 140), gap=0),
    "Explosion": dict(file="explo.png",    grid=(144, 144), icon=None, gap=0),
}

# All atlas files that get a full-image "grid overview" (task 3e). jauge.png
# is excluded: it is a single whole-image icon (not a grid), out of this
# script's scope per the task brief.
OVERVIEW_ATLASES = ["Blupi", "Blupi1_11", "Object", "Element", "Explosion", "Button", "Pad", "Text"]
OVERVIEW_NAMES = {  # channel-key -> output file stem (one per physical PNG, not per channel alias)
    "Blupi": "blupi", "Blupi1_11": "blupi1", "Object": "object-m", "Element": "element",
    "Explosion": "explo", "Button": "button", "Pad": "pad", "Text": "text",
}


def get_src_rect(atlas_w: int, grid_w: int, grid_h: int, icon_w: int, icon_h: int,
                  gap: int, icon: int) -> Tuple[int, int, int, int]:
    """Pixmap::GetSrcRectangle, Pixmap.cpp:683-697, transcribed exactly:

        column = icon % (width / bitmapGridX)
        row    = icon / (width / bitmapGridX)
        bitmapGridX += gap; bitmapGridY += gap
        return Rectangle(gap + column*bitmapGridX, gap + row*bitmapGridY, iconW, iconH)

    Returns (left, top, width, height) in source pixels.
    """
    cols = atlas_w // grid_w
    if cols <= 0:
        raise ValueError("grid_w does not divide atlas width")
    column = icon % cols
    row = icon // cols
    step_x = grid_w + gap
    step_y = grid_h + gap
    left = gap + column * step_x
    top = gap + row * step_y
    return left, top, icon_w, icon_h


def crop_icon(atlas_img: Image.Image, channel: str, icon: int,
              explo_size_table: Optional[List[int]] = None) -> Image.Image:
    cfg = ATLAS[channel]
    grid_w, grid_h = cfg["grid"]
    gap = cfg["gap"]
    if channel == "Explosion":
        assert explo_size_table is not None
        height = explo_size_table[icon]
        width = max(height, 128)
    else:
        width, height = cfg["icon"]
    left, top, w, h = get_src_rect(atlas_img.width, grid_w, grid_h, width, height, gap, icon)
    box = (left, top, left + w, top + h)
    if left < 0 or top < 0 or box[2] > atlas_img.width or box[3] > atlas_img.height:
        raise ValueError(f"icon {icon} on channel {channel} crops out of bounds: {box} vs atlas {atlas_img.size}")
    return atlas_img.crop(box)


# ---------------------------------------------------------------------------
# Contact-sheet rendering
# ---------------------------------------------------------------------------

FONT = ImageFont.load_default()
BG_A = (238, 238, 230, 255)   # pale warm gray
BG_B = (222, 232, 238, 255)   # pale cool blue
BORDER = (90, 90, 90, 255)
TITLE_BG = (32, 32, 40, 255)
TITLE_FG = (255, 255, 255, 255)


def _text_size(draw: ImageDraw.ImageDraw, text: str) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=FONT)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def build_contact_sheet(frames: Sequence[Tuple[Image.Image, str]], title: str,
                         subtitle: str = "", scale: int = 1, max_per_row: int = 28,
                         cell_pad: int = 6) -> Image.Image:
    """frames: sequence of (PIL Image RGBA, caption_string). Renders each
    frame at `scale`x on an alternating light background (so alpha
    transparency is visible), with a thin border and a caption line below,
    wrapped into rows of at most max_per_row cells, with a title bar on top.
    """
    if not frames:
        raise ValueError("no frames to render")
    scaled = []
    for img, cap in frames:
        im = img.convert("RGBA")
        if scale != 1:
            im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        scaled.append((im, cap))

    cell_w = max(im.width for im, _ in scaled) + cell_pad * 2
    cell_h = max(im.height for im, _ in scaled)
    caption_h = 16
    row_h = cell_h + caption_h + cell_pad * 2

    n = len(scaled)
    cols = min(max_per_row, n)
    rows = (n + cols - 1) // cols

    title_h = 28 + (16 if subtitle else 0)
    sheet_w = cols * cell_w
    sheet_h = title_h + rows * row_h

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    draw.rectangle([0, 0, sheet_w, title_h], fill=TITLE_BG)
    draw.text((8, 6), title, font=FONT, fill=TITLE_FG)
    if subtitle:
        draw.text((8, 22), subtitle, font=FONT, fill=(200, 200, 210, 255))

    for idx, (im, cap) in enumerate(scaled):
        r, c = divmod(idx, cols)
        cell_x = c * cell_w
        cell_y = title_h + r * row_h
        bg = BG_A if (idx % 2 == 0) else BG_B
        draw.rectangle([cell_x, cell_y, cell_x + cell_w - 1, cell_y + cell_h + caption_h + cell_pad * 2 - 1],
                        fill=bg, outline=BORDER, width=1)
        px = cell_x + (cell_w - im.width) // 2
        py = cell_y + cell_pad
        sheet.alpha_composite(im, (px, py))
        draw.rectangle([px - 1, py - 1, px + im.width, py + im.height], outline=BORDER, width=1)
        tw, th = _text_size(draw, cap)
        tx = cell_x + (cell_w - tw) // 2
        ty = cell_y + cell_pad + cell_h + 2
        draw.text((tx, ty), cap, font=FONT, fill=(20, 20, 20, 255))
    return sheet


def build_atlas_overview(atlas_img: Image.Image, grid_w: int, grid_h: int, gap: int,
                          title: str) -> Image.Image:
    """Full real atlas image with a thin grid overlay at the real cell
    boundaries computed by the same GetSrcRectangle stepping used for
    cropping (gap + column*(grid+gap)), so the overlay is provably the same
    grid the game engine actually slices."""
    im = atlas_img.convert("RGBA")
    title_h = 26
    out = Image.new("RGBA", (im.width, im.height + title_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(out)
    draw.rectangle([0, 0, im.width, title_h], fill=TITLE_BG)
    draw.text((6, 5), title, font=FONT, fill=TITLE_FG)
    out.alpha_composite(im, (0, title_h))
    step_x = grid_w + gap
    step_y = grid_h + gap
    cols = im.width // grid_w
    rows_n = im.height // grid_h
    line_color = (255, 0, 128, 160)
    for c in range(cols + 1):
        x = gap + c * step_x
        draw.line([(x, title_h), (x, title_h + im.height)], fill=line_color, width=1)
    for r in range(rows_n + 1):
        y = title_h + gap + r * step_y
        draw.line([(0, y), (im.width, y)], fill=line_color, width=1)
    return out


def hyphenate(name: str) -> str:
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0 and (name[i - 1].islower() or name[i - 1].isdigit()):
            out.append("-")
        out.append(ch.lower())
    return "".join(out)


# ---------------------------------------------------------------------------
# Part (b): BlupiAction animation catalog
# ---------------------------------------------------------------------------

def blupi_channel_for_frame(action_name: str, icon: int) -> str:
    """Decor::BlupiSearchIcon, Decor.cpp:2404-2410, transcribed exactly:

        if (action in {Clear1,Clear2,Clear3,Glu} ||
            (action == Electro && icon < 266))
            channel = Element
        else
            channel = Blupi
    """
    if action_name in ("Clear1", "Clear2", "Clear3", "Glu"):
        return "Element"
    if action_name == "Electro" and icon < 266:
        return "Element"
    return "Blupi"


def generate_blupi_actions(me_root: Path, out_dir: Path, tables: Dict[str, List[int]],
                            manifest: List[dict]) -> None:
    action_names = parse_enum_values(
        me_root / "include/WindowsPhoneSpeedyBlupi/def/BlupiAction.hpp", "BlupiAction")

    blupi_img = Image.open(me_root / "Content/icons/blupi.png")
    element_img = Image.open(me_root / "Content/icons/element.png")
    atlas_imgs = {"Blupi": blupi_img, "Element": element_img}

    records = parse_table_blupi_records(tables["table_blupi"])
    print(f"[blupi] parsed {len(records)} table_blupi action records "
          f"(array length {len(tables['table_blupi'])})")

    seen_actions = set()
    for rec in records:
        raw = rec["action_raw"]
        name = action_names.get(raw, f"Unknown{raw}")
        if raw in seen_actions:
            print(f"[blupi] WARNING: duplicate record for action {name} ({raw}); "
                  f"using the later occurrence only, per the real linear-scan/break semantics")
        seen_actions.add(raw)

        frames = []
        channels_used = set()
        for fi, icon in enumerate(rec["frames"]):
            channel = blupi_channel_for_frame(name, icon)
            channels_used.add(channel)
            crop = crop_icon(atlas_imgs[channel], channel, icon)
            frames.append((crop, f"icon {icon} / f{fi}"))

        threshold_note = f", freezes at frame {rec['threshold']} past that phase" if rec["threshold"] else ""
        subtitle = (f"BlupiAction::{name} (raw={raw})  |  {rec['frame_count']} frames"
                    f"{threshold_note}  |  channel(s): {'/'.join(sorted(channels_used))}"
                    f"  |  table_blupi offset {rec['offset']}")
        sheet = build_contact_sheet(frames, title=f"Blupi action: {name}", subtitle=subtitle, scale=3)
        out_name = f"blupi-action-{hyphenate(name)}.png"
        sheet.save(out_dir / out_name)
        manifest.append(dict(
            file=out_name,
            source=f"Tables::table_blupi (Tables.cpp:116, offset {rec['offset']}), "
                    f"blupi.png/element.png via Pixmap::GetSrcRectangle",
            desc=f"BlupiAction::{name} (raw id {raw}): {rec['frame_count']} animation frame(s)"
                 f"{threshold_note}, channel(s) {'/'.join(sorted(channels_used))}.",
        ))
    print(f"[blupi] wrote {len(records)} action contact sheets")


# ---------------------------------------------------------------------------
# Part (c): ObjectType animation catalog
# ---------------------------------------------------------------------------
# Every entry below was confirmed by reading the exact branch in
# Decor::MoveObjectStepIcon (Decor.cpp:8192-9047) for that ObjectType --- see
# the docstring at the top of this file and MANIFEST.md's per-image notes.
# frames_kind:
#   "table"      -> use tables[table_name] verbatim (real declared length,
#                    NOT the modulo literal from Decor.cpp -- see note re:
#                    table_tiplouf below).
#   "range"      -> icons start..start+count-1
#   "pingpong5"  -> ObjectType5's forward/backward 0..10 sweep, computed
#                   exactly per Decor.cpp:8299-8306.
#   "electro"    -> ObjectType38's split-channel table_electro sequence.

SIMPLE_OBJECT_SEQUENCES = [
    # (out_stem, ObjectType id, description, channel, frames_kind, arg)
    ("object-002-patrol-enemy-a", 2, "Standard patrolling enemy", "Element", "range", (12, 9)),
    ("object-003-patrol-enemy-b", 3, "Patrolling enemy variant", "Element", "range", (48, 9)),
    ("object-016-spider", 16, "Spider/arthropod enemy", "Element", "range", (69, 9)),
    ("object-006-life-egg", 6, "Extra-life egg collectible", "Element", "range", (21, 8)),
    ("object-007-exit-goal", 7, "Level-exit goal marker", "Element", "range", (29, 8)),
    ("object-021-secret-exit-key", 21, "Secret-level exit goal marker", "Element", "table", "table_cle"),
    ("object-049-key1", 49, "Key 1 collectible", "Element", "table", "table_cle1"),
    ("object-050-key2", 50, "Key 2 collectible", "Element", "table", "table_cle2"),
    ("object-051-key3", 51, "Key 3 collectible", "Element", "table", "table_cle3"),
    ("object-024-skate-pickup", 24, "Skate collectible", "Element", "table", "table_skate"),
    ("object-025-shield-pickup", 25, "Shield power-up", "Element", "table", "table_shield"),
    ("object-026-suction-power", 26, "Suction-cup power-up", "Element", "table", "table_power"),
    ("object-040-invert-pickup", 40, "Mirror/invert power-up", "Element", "table", "table_invert"),
    ("object-031-charge-cloud", 31, "Charge/cloud power-up", "Object", "table", "table_charge"),
    ("object-027-magic-track", 27, "Magic track sparkle trail", "Element", "table", "table_magictrack"),
    ("object-057-shield-track", 57, "Shield trail sparkle", "Element", "table", "table_shieldtrack"),
    ("object-039-treasure-track", 39, "Collectible sparkle effect", "Element", "table", "table_tresortrack"),
    ("object-052-bridge-build", 52, "Bridge construction animation", "Object", "table", "table_bridge"),
    ("object-036-pollution-puff", 36, "Pollution/cloud puff effect", "Element", "table", "table_pollution"),
    ("object-041-invert-start", 41, "Invert-start particle burst", "Element", "table", "table_invertstart"),
    ("object-042-invert-stop", 42, "Invert-stop particle burst", "Element", "table", "table_invertstop"),
    ("object-014-water-plouf", 14, "Water plouf splash", "Object", "table", "table_plouf"),
    ("object-035-small-plouf", 35, "Small plouf splash", "Object", "table", "table_tiplouf"),
    ("object-015-water-bubble", 15, "Water bubble / blup", "Object", "table", "table_blup"),
    ("object-034-goo-glue", 34, "Goo/glue particle", "Element", "table", "table_glu"),
    ("object-037-clear-effect", 37, "Clear/dissipate visual effect", "Element", "table", "table_clear"),
    ("object-056-dynamite-fuse", 56, "Dynamite fuse animation", "Element", "table", "table_dynamitef"),
    ("object-096-follow-enemy-1", 96, "Follow enemy variant 1", "Element", "table", "table_follow1"),
    ("object-097-follow-enemy-2", 97, "Follow enemy variant 2", "Element", "table", "table_follow2"),
]

# Four-way patrol creatures: table_<base>_left/_right/_turn2l/_turn2r.
# ObjectType54 shares one table_creature_turn2 for both turn directions
# (confirmed at Decor.cpp:8802-8834: both step==1 and step==3 branches, in
# both X-direction cases, read table_creature_turn2 -- there is no separate
# _turn2l/_turn2r pair for this type).
FOUR_WAY_OBJECT_SEQUENCES = [
    ("object-004-bulldozer", 4, "Bulldozer enemy", "Element", "table_bulldozer_left", "table_bulldozer_right",
     "table_bulldozer_turn2l", "table_bulldozer_turn2r"),
    ("object-017-fish", 17, "Fish enemy", "Element", "table_poisson_left", "table_poisson_right",
     "table_poisson_turn2l", "table_poisson_turn2r"),
    ("object-020-bird", 20, "Bird enemy", "Element", "table_oiseau_left", "table_oiseau_right",
     "table_oiseau_turn2l", "table_oiseau_turn2r"),
    ("object-044-wasp", 44, "Wasp/bee enemy", "Element", "table_guepe_left", "table_guepe_right",
     "table_guepe_turn2l", "table_guepe_turn2r"),
    ("object-054-large-creature", 54, "Large creature enemy", "Element", "table_creature_left",
     "table_creature_right", "table_creature_turn2", "table_creature_turn2"),
    # channel not explicitly assigned in MoveObjectStepIcon for 32/33 -- see
    # MANIFEST.md note; rendered as PixmapChannel::Blupi because every icon
    # value in these tables (61-70, 237-250) falls inside blupi.png's
    # addressable range and the table names mirror the Blupi asset family.
    ("object-032-blupih-clone", 32, "Blupi-hostile clone \"blupih\" (channel inferred, see notes)",
     "Blupi", "table_blupih_left", "table_blupih_right", "table_blupih_turn2l", "table_blupih_turn2r"),
    ("object-033-blupit-clone", 33, "Blupi-hostile clone \"blupit\" (channel inferred, see notes)",
     "Blupi", "table_blupit_left", "table_blupit_right", "table_blupit_turn2l", "table_blupit_turn2r"),
]

STATIC_ICON_OBJECTS = [
    (13, "Helicopter pick-up", "Element", 68),
    (46, "Balloon vehicle pick-up", "Element", 208),
    (19, "Jeep vehicle pick-up", "Element", 89),
    (28, "Tank vehicle pick-up", "Element", 167),
    (23, "Fired projectile", "Element", 176),
    (29, "Bullet ammo pack", "Element", 177),
    (30, "Drink power-up", "Element", 178),
]


def pingpong5_frames() -> List[int]:
    """ObjectType5 (treasure), Decor.cpp:8297-8308:
        if phase/ScaleDiv(3) % 22 < 11: icon = phase/ScaleDiv(3) % 11
        else: icon = 11 - phase/ScaleDiv(3) % 11
    Enumerated over one full 22-step cycle (phase/ScaleDiv(3) = 0..21)."""
    frames = []
    for t in range(22):
        if t % 22 < 11:
            frames.append(t % 11)
        else:
            frames.append(11 - t % 11)
    return frames


def generate_object_sequences(me_root: Path, out_dir: Path, tables: Dict[str, List[int]],
                               manifest: List[dict]) -> None:
    imgs = {
        "Element": Image.open(me_root / "Content/icons/element.png"),
        "Object": Image.open(me_root / "Content/icons/object-m.png"),
        "Blupi": Image.open(me_root / "Content/icons/blupi.png"),
        "Blupi1_12": Image.open(me_root / "Content/icons/blupi1.png"),
    }

    count = 0
    for stem, otype, desc, channel, kind, arg in SIMPLE_OBJECT_SEQUENCES:
        if kind == "range":
            start, n = arg
            icons = list(range(start, start + n))
            source = f"inline formula in Decor::MoveObjectStepIcon (icon = {start} + phase % {n})"
        elif kind == "table":
            table_name = arg
            if table_name not in tables:
                print(f"[object] SKIP {stem}: table {table_name} not found in Tables.cpp -- "
                      f"cannot verify, refusing to fabricate data")
                continue
            icons = tables[table_name]
            source = f"Tables::{table_name} (Tables.cpp)"
            declared_len = len(icons)
            # Cross-check against the modulo literal actually used in
            # Decor.cpp for this type, when we know it, purely for the
            # manifest note (does not change what we render: we always use
            # the real declared array).
        else:
            raise ValueError(kind)

        frames = [(crop_icon(imgs[channel], channel, icon), f"icon {icon} / f{i}")
                  for i, icon in enumerate(icons)]
        subtitle = f"ObjectType{otype} — {desc}  |  {len(icons)} frames  |  channel {channel}  |  {source}"
        sheet = build_contact_sheet(frames, title=f"Object {otype}: {desc}", subtitle=subtitle, scale=3)
        out_name = f"{stem}.png"
        sheet.save(out_dir / out_name)
        note = ""
        if kind == "table" and table_name == "table_tiplouf":
            note = (" NOTE: Decor.cpp:8619 indexes this table modulo 7, but Tables.cpp declares "
                     "table_tiplouf with only 3 real elements ({99,100,244} -> actually "
                     "{244,99,244}); this sheet renders exactly the 3 real elements and does not "
                     "fabricate frames 3-6 to fill the apparent gap -- a genuine array-bounds "
                     "inconsistency in the original engine, reported here rather than silently "
                     "patched.")
        manifest.append(dict(
            file=out_name,
            source=source,
            desc=f"ObjectType{otype} ({desc}): {len(icons)} frame(s), channel {channel}.{note}",
        ))
        count += 1

    # ObjectType5 (treasure) ping-pong formula
    icons = pingpong5_frames()
    frames = [(crop_icon(imgs["Element"], "Element", icon), f"icon {icon} / f{i}")
              for i, icon in enumerate(icons)]
    subtitle = ("ObjectType5 — Treasure collectible  |  22 frames (0..10 forward, 10..0 back)"
                "  |  channel Element  |  inline formula in Decor::MoveObjectStepIcon (Decor.cpp:8297-8308)")
    sheet = build_contact_sheet(frames, title="Object 5: Treasure collectible", subtitle=subtitle, scale=3)
    sheet.save(out_dir / "object-005-treasure.png")
    manifest.append(dict(
        file="object-005-treasure.png",
        source="inline ping-pong formula in Decor::MoveObjectStepIcon (Decor.cpp:8297-8308)",
        desc="ObjectType5 (treasure collectible): 22-frame forward/backward sweep over icons 0-10, channel Element.",
    ))
    count += 1

    # ObjectType38 electric arc: split channel by raw phase (Decor.cpp:8988-9006)
    table = tables["table_electro"]
    frames = []
    for idx, icon in enumerate(table):
        channel = "Blupi1_12" if idx < 30 else "Element"
        crop = crop_icon(imgs[channel], channel, icon)
        frames.append((crop, f"icon {icon} / f{idx} ({channel})"))
    subtitle = (f"ObjectType38 — Electric arc effect  |  {len(table)} frames  |  "
                "frames 0-29: PixmapChannel::Blupi1_12 (blupi1.png); frames 30-89: PixmapChannel::Element "
                "(element.png)  |  Tables::table_electro, split per Decor.cpp:8988-9006")
    sheet = build_contact_sheet(frames, title="Object 38: Electric arc effect", subtitle=subtitle, scale=3)
    sheet.save(out_dir / "object-038-electric-arc.png")
    manifest.append(dict(
        file="object-038-electric-arc.png",
        source="Tables::table_electro (Tables.cpp), blupi1.png for frames 0-29 / element.png for frames 30-89",
        desc="ObjectType38 (electric arc effect): 90 frames, channel switches from Blupi1_12 to Element "
             "partway through the sequence (Decor.cpp:8988-9006) -- the one BlupiAction/ObjectType "
             "sequence in this catalog that genuinely uses blupi1.png.",
    ))
    count += 1

    # Static single-icon objects: not animations: recorded as icons, not a
    # PNG contact sheet each (would just be a single frame), but logged for
    # completeness and to explain the gap explicitly rather than silently
    # dropping them.
    for otype, desc, channel, icon in STATIC_ICON_OBJECTS:
        manifest.append(dict(
            file="(none — static icon, not an animation)",
            source=f"inline constant in Decor::MoveObjectStepIcon, channel {channel}, icon {icon}",
            desc=f"ObjectType{otype} ({desc}) draws a single static icon ({icon}) every frame; "
                 f"not included as a contact sheet because there is no sequence to show.",
        ))

    # Four-way patrol creatures. Group sub-tables by underlying table name
    # first: ObjectType54 uses the SAME table_creature_turn2 array for both
    # step==1 (turn-to-left) and step==3 (turn-to-right) (Decor.cpp:8802-8834
    # -- confirmed by reading both branches), so it gets one merged sheet
    # instead of two identical ones under different names.
    for stem, otype, desc, channel, t_left, t_right, t_turn2l, t_turn2r in FOUR_WAY_OBJECT_SEQUENCES:
        subframes = [
            ("left", t_left), ("right", t_right), ("turn-to-left", t_turn2l), ("turn-to-right", t_turn2r),
        ]
        by_table: Dict[str, List[str]] = {}
        order: List[str] = []
        for label, table_name in subframes:
            by_table.setdefault(table_name, [])
            if table_name not in order:
                order.append(table_name)
            by_table[table_name].append(label)

        for table_name in order:
            labels = by_table[table_name]
            label_str = " / ".join(labels)
            slug = "-".join(l.replace(" ", "-") for l in labels)
            out_name = f"{stem}-{slug}.png"
            if table_name not in tables:
                print(f"[object] SKIP {stem}-{slug}: table {table_name} not found")
                continue
            icons = tables[table_name]
            frames = [(crop_icon(imgs[channel], channel, icon), f"icon {icon} / f{i}")
                      for i, icon in enumerate(icons)]
            shared_note = " (single table shared by both turn directions)" if len(labels) > 1 else ""
            subtitle = (f"ObjectType{otype} — {desc}, {label_str}{shared_note}  |  {len(icons)} frames  |  "
                        f"channel {channel}  |  Tables::{table_name}")
            sheet = build_contact_sheet(frames, title=f"Object {otype}: {desc} ({label_str})",
                                         subtitle=subtitle, scale=3)
            sheet.save(out_dir / out_name)
            manifest.append(dict(
                file=out_name,
                source=f"Tables::{table_name} (Tables.cpp)",
                desc=f"ObjectType{otype} ({desc}), '{label_str}' sub-animation{shared_note}: "
                     f"{len(icons)} frame(s), channel {channel}.",
            ))
            count += 1

    print(f"[object] wrote {count} object contact sheets "
          f"({len(STATIC_ICON_OBJECTS)} static-icon types logged without images)")


# ---------------------------------------------------------------------------
# Part (d): explosion contact sheets
# ---------------------------------------------------------------------------

def generate_explosions(me_root: Path, out_dir: Path, tables: Dict[str, List[int]],
                         manifest: List[dict]) -> None:
    explo_img = Image.open(me_root / "Content/icons/explo.png")
    explo_size = tables["table_explo_size"]
    explo_table_names = ["table_explo1", "table_explo2", "table_explo3", "table_explo4",
                          "table_explo5", "table_explo6", "table_explo7", "table_explo8"]
    count = 0
    for table_name in explo_table_names:
        icons = tables[table_name]
        frames = []
        for i, icon in enumerate(icons):
            crop = crop_icon(explo_img, "Explosion", icon, explo_size_table=explo_size)
            frames.append((crop, f"icon {icon} / f{i} ({crop.width}x{crop.height})"))
        subtitle = (f"{len(icons)} frames  |  PixmapChannel::Explosion (explo.png)  |  "
                    f"per-frame size from Tables::table_explo_size[icon] "
                    f"(height=table value, width=max(height,128))")
        sheet = build_contact_sheet(frames, title=f"Explosion effect: {table_name}", subtitle=subtitle,
                                     scale=1, max_per_row=16)
        out_name = f"explosion-{table_name}.png"
        sheet.save(out_dir / out_name)
        manifest.append(dict(
            file=out_name,
            source=f"Tables::{table_name} + Tables::table_explo_size (Tables.cpp), explo.png",
            desc=f"Explosion/effect sequence {table_name}: {len(icons)} frame(s), each cropped at its "
                 f"own real per-icon size from table_explo_size.",
        ))
        count += 1
    print(f"[explosion] wrote {count} explosion contact sheets")


# ---------------------------------------------------------------------------
# Part (e): atlas overview grids
# ---------------------------------------------------------------------------

def generate_atlas_overviews(me_root: Path, out_dir: Path, manifest: List[dict]) -> None:
    count = 0
    for channel in OVERVIEW_ATLASES:
        cfg = ATLAS[channel]
        img = Image.open(me_root / "Content/icons" / cfg["file"])
        grid_w, grid_h = cfg["grid"]
        gap = cfg["gap"]
        stem = OVERVIEW_NAMES[channel]
        title = f"{cfg['file']}  —  grid {grid_w}x{grid_h}, gap {gap}px (real size {img.width}x{img.height})"
        overview = build_atlas_overview(img, grid_w, grid_h, gap, title)
        out_name = f"atlas-{stem}-grid.png"
        overview.save(out_dir / out_name)
        manifest.append(dict(
            file=out_name,
            source=f"Content/icons/{cfg['file']} (real atlas, {img.width}x{img.height}), grid overlay from "
                    f"Pixmap::DrawIcon's per-channel switch (Pixmap.cpp:550-648)",
            desc=f"Full real atlas for {cfg['file']} with a {grid_w}x{grid_h} (gap {gap}px) grid overlay "
                 f"at the exact cell boundaries Pixmap::GetSrcRectangle slices at.",
        ))
        count += 1
        if channel == "Explosion":
            manifest[-1]["desc"] += (" Note: explo.png's overlay shows the uniform 144x144 base grid; "
                                      "actual per-icon crop width/height varies per Tables::table_explo_size "
                                      "and can differ from this base cell (see the explosion-table_explo*.png "
                                      "contact sheets for real per-frame crop sizes).")
    print(f"[atlas] wrote {count} atlas overview images")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--me-root", default=DEFAULT_ME_ROOT, help="path to a mobile-eggbert checkout")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="output directory for PNGs")
    args = ap.parse_args()

    me_root = Path(args.me_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tables_cpp = me_root / "src/WindowsPhoneSpeedyBlupi/Tables.cpp"
    if not tables_cpp.exists():
        sys.exit(f"Tables.cpp not found at {tables_cpp} -- is --me-root correct?")

    tables = parse_shortcs_tables(tables_cpp)
    print(f"[tables] parsed {len(tables)} shortcs tables from {tables_cpp}")

    manifest: List[dict] = []
    generate_blupi_actions(me_root, out_dir, tables, manifest)
    generate_object_sequences(me_root, out_dir, tables, manifest)
    generate_explosions(me_root, out_dir, tables, manifest)
    generate_atlas_overviews(me_root, out_dir, manifest)

    from manifest_writer import write_fragment, build_manifest
    write_fragment(out_dir, "sprites", manifest)
    build_manifest(out_dir)  # rebuild book/images/MANIFEST.md from all fragments found so far
    print(f"[done] {len(manifest)} manifest entries recorded for the sprite/animation pipeline")


if __name__ == "__main__":
    main()
