"""
me_tables.py -- shared helpers for the mobile-eggbert-bible image pipeline.

Parses the REAL numeric data out of a fresh `mobile-eggbert` checkout:

  - Tables.cpp: every `static const shortcs Tables::table_XXX[N] = { ... };`
    array literal (flat, comma-separated int lists; no nested braces are used
    anywhere in the shortcs tables, confirmed by reading Tables.cpp).
  - BlupiAction.hpp / ObjectType.hpp: `Name = number,` enum entries, via a
    small regex enum-body parser (not hand-transcribed).

Nothing here invents numbers: every table/enum value returned is read
verbatim from the given `mobile-eggbert` checkout at run time, so re-running
this against a fresh checkout reproduces the same data (or fails loudly if
the upstream source changed shape).

Used by both tools/extract_sprites.py and tools/render_level_map.py.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List


def strip_c_comments(text: str) -> str:
    """Remove // and /* */ comments (no string literals contain // or /* in
    these particular data files, so a simple regex is safe here)."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def parse_shortcs_tables(tables_cpp_path: Path) -> Dict[str, List[int]]:
    """Parse every `const shortcs Tables::NAME[...] = { ... };` array literal
    in Tables.cpp into {name: [int, ...]}.

    Verified by inspection of Tables.cpp that none of the `shortcs` (16-bit)
    tables use nested braces (e.g. table_blupi, table_mirror, table_explo*,
    table_decor_quart, world_terminal are all flat int lists), so a
    non-nested `{...}` capture up to the first `};` is correct and safe.
    """
    raw = tables_cpp_path.read_text(encoding="utf-8")
    raw = strip_c_comments(raw)
    pattern = re.compile(
        r"const\s+shortcs\s+Tables::(\w+)\s*\[[^\]]*\]\s*=\s*\{(.*?)\}\s*;",
        re.DOTALL,
    )
    tables: Dict[str, List[int]] = {}
    for name, body in pattern.findall(raw):
        values = []
        for tok in body.split(","):
            tok = tok.strip()
            if not tok:
                continue
            values.append(int(tok))
        tables[name] = values
    return tables


def parse_enum_values(header_path: Path, enum_name: str) -> Dict[int, str]:
    """Parse `Name = number,` entries inside `enum class <enum_name> ... { ... };`
    into {raw_value: Name}. Handles entries without an explicit `= number`
    by incrementing from the previous value (not currently needed by
    BlupiAction/ObjectType, which give every value explicitly, but kept for
    robustness)."""
    raw = header_path.read_text(encoding="utf-8")
    raw = strip_c_comments(raw)
    m = re.search(
        rf"enum\s+class\s+{re.escape(enum_name)}\b[^{{]*\{{(.*?)\}}\s*;",
        raw,
        re.DOTALL,
    )
    if not m:
        raise ValueError(f"enum class {enum_name} not found in {header_path}")
    body = m.group(1)
    values: Dict[int, str] = {}
    next_value = 0
    # Split on commas that separate enumerators (fine here: no nested braces
    # or commas-in-expressions inside these two enums).
    for entry in body.split(","):
        entry = entry.strip()
        if not entry:
            continue
        em = re.match(r"(\w+)\s*(?:=\s*(-?\w+))?$", entry)
        if not em:
            continue
        name, val = em.group(1), em.group(2)
        if val is not None:
            next_value = int(val, 0)
        values[next_value] = name
        next_value += 1
    return values


def parse_table_blupi_records(flat: List[int]):
    """Walk Tables::table_blupi's packed variable-length record format,
    exactly per Decor::BlupiSearchIcon's loop (Decor.cpp:2393):

        for (i = 0; table_blupi[i] != 0; i += table_blupi[i+1] + 3)
            actionId = table_blupi[i]
            frameCount = table_blupi[i+1]
            threshold = table_blupi[i+2]
            frames = table_blupi[i+3 : i+3+frameCount]

    Returns a list of dicts: {action_raw, frame_count, threshold, frames,
    offset}. Terminates at the first actionId == 0 (BlupiAction::None),
    matching the real loop condition -- does not require reaching the end of
    the physical array.
    """
    # Note (discovered by running this parser against the real Tables.cpp
    # data, not anticipated from reading the algorithm alone): the array
    # contains short stretches of degenerate (-1, -1, -1) filler entries
    # between some real records (e.g. between the records for raw action 76
    # and raw action 77). shortcs is signed, BlupiAction's raw type is an
    # unsigned byte (0-87), so -1 can never equal a real ToRaw(action) value
    # at runtime -- Decor::BlupiSearchIcon's real linear scan walks straight
    # through this filler without ever matching it, advancing by
    # table_blupi[i+1]+3 = -1+3 = 2 each step, exactly like this parser does
    # below. This is real, harmless padding in the shipped data, not a
    # parser bug; degenerate records (frame_count <= 0, so no real frames)
    # are still returned here so callers can see and report them, but they
    # never correspond to a playable BlupiAction and are filtered out by
    # generate_blupi_actions() before rendering.
    records = []
    i = 0
    n = len(flat)
    while i < n and flat[i] != 0:
        action_raw = flat[i]
        frame_count = flat[i + 1]
        threshold = flat[i + 2]
        if frame_count > 0:
            frames = flat[i + 3: i + 3 + frame_count]
            if len(frames) != frame_count:
                raise ValueError(
                    f"table_blupi record at offset {i} claims {frame_count} frames "
                    f"but only {len(frames)} remain in the array"
                )
        else:
            frames = []
        records.append(dict(
            action_raw=action_raw,
            frame_count=frame_count,
            threshold=threshold,
            frames=frames,
            offset=i,
        ))
        next_i = i + frame_count + 3
        if next_i <= i:
            raise ValueError(f"table_blupi record at offset {i} would not advance (frame_count={frame_count})")
        i = next_i
    return records
