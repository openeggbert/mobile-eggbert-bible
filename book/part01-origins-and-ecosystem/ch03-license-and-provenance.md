# Chapter 3: License and Provenance

## Two license files, not one

A reader who clones `mobile-eggbert` and goes looking for "the license" will find two separate
`LICENSE` files, in two different license families, at two different levels of the tree:

- `LICENSE` at the repository root — the **MIT License**.
- `src/WindowsPhoneSpeedyBlupi/LICENSE` — the full text of the **GNU General Public License,
  version 3** (GPLv3).

This chapter documents both files as written, and is honest about what is — and is not — resolved
by the repository about how the two interact. No attempt is made here to adjudicate the legal
question; that is a matter for the project's copyright holders, not for this book. What follows is
an accurate description of what each file actually says.

## The root `LICENSE`: MIT

The project root's `LICENSE` file is short enough to quote in full:

*From `LICENSE:1-22`:*

```text
MIT License

Copyright (c) 2013 Daniel Roux
Copyright (c) 2024-2026 Robert Vokac

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Two copyright lines are stacked here, and they map directly onto the migration history covered in
[Chapter 1](ch01-what-is-mobile-eggbert.md):

- **Daniel Roux, 2013** — the original author of Speedy Blupi, credited in the same role by
  `Decor.hpp`'s file header ("Original XNA/C# game by Epsitec SA"; see below).
- **Robert Vokac, 2024–2026** — the porting work: the ILSpy decompilation, the MonoGame and C++
  migrations, and the ongoing CNA-based port that this book documents.

The MIT License is a short, permissive license: it grants essentially unrestricted rights to use,
copy, modify, merge, publish, distribute, sublicense, and sell the software, on the sole condition
that the copyright notice and permission text are preserved in copies or substantial portions of
the Software, and it disclaims all warranty. As the license text found at the repository root, MIT
is the license that governs the project as a whole in the absence of a more specific statement for
a particular subtree.

## The subdirectory `LICENSE`: GPLv3

A second, much longer `LICENSE` file — 674 lines, the complete and unmodified GPLv3 text as
published by the Free Software Foundation — sits inside `src/WindowsPhoneSpeedyBlupi/`, the
directory containing every one of the project's C++ implementation files (`Game1.cpp`, `Decor.cpp`,
`Program.cpp`, and the rest of the `.cpp` sources documented throughout this book). Its preamble
identifies it unambiguously:

*From `src/WindowsPhoneSpeedyBlupi/LICENSE:1-6`:*

```text
                    GNU GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
 Everyone is permitted to copy and distribute verbatim copies
 of this license document, but changing it is not allowed.
```

GPLv3 is a copyleft license, materially different in character from MIT: it requires that
distributed copies (and works based on the program) remain under the GPL, that source code be made
available to recipients, and that no additional restrictions be layered on top of the rights it
grants. The file is the license's standard boilerplate, ending — as GPLv3 conventionally does —
with a template for how a project should apply the license to its own source files:

*From `src/WindowsPhoneSpeedyBlupi/LICENSE:648-656`:*

```text
    <one line to give the program's name and a brief idea of what it does.>
    Copyright (C) <year>  <name of author>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
```

Notably, this template is present only as the license's own generic boilerplate — the repository
does not fill in the placeholders (`<one line to give the program's name...>`, `<year>`, `<name of
author>`) anywhere in `src/WindowsPhoneSpeedyBlupi/`, nor do the individual `.cpp` files in that
directory carry a GPL header of their own; their file-level Doxygen comments (like the one on
`Decor.hpp`, quoted in [Chapter 1](ch01-what-is-mobile-eggbert.md)) name authorship and dates but
do not cite either license by name.

## What this book will and will not claim

Having two license files present, in two incompatible license families, at two different scopes
(whole-repository vs. one source subdirectory) without an accompanying `NOTICE` file or README
section explaining the relationship between them, is an observable fact about this repository as it
stands. This book states that fact plainly and declines to resolve it, for two reasons:

1. **It is not this book's place to make a legal determination.** Whether the GPLv3 file governs
   only the `src/WindowsPhoneSpeedyBlupi/` subtree, whether it is meant to supersede the root MIT
   license for that subtree, whether it is a leftover from an earlier licensing decision no longer
   in effect, or whether it is simply present for informational/reference reasons — all of these are
   possible readings, and none of them can be verified from the text of the two files alone. Readers
   with a genuine legal need to know which terms apply to a specific use of this code should consult
   the project's current maintainers or their own counsel, not this book.
2. **The project's own methodology (this book's `CLAUDE.md`) requires every claim to be grounded in
   an actual source read**, and there is no third source file in the repository that adjudicates
   between the two licenses. Inventing a resolution here would violate that standard.

What can be said with confidence, reading only the two files as written: the root-level MIT grant is
the broadest permission stated anywhere in the repository, covering the project "as a whole" absent
a more specific statement; the GPLv3 file's mere presence inside the one directory that holds every
C++ implementation file is, at minimum, a signal that copyleft terms may have been intended to apply
there at some point in the project's history — and GPLv3, being the more restrictive of the two, is
the safer assumption for anyone redistributing code specifically from that subdirectory.

## Provenance, restated

Setting the licensing question aside, the provenance chain itself is unambiguous and consistent
across every source this book has read:

- **2013** — Daniel Roux (Epsitec SA) writes the original Speedy Blupi for Windows Phone in C#
  using XNA 4.0. This is the copyright attributed in `LICENSE:3` and the authorship named in
  `Decor.hpp:19` ("Original XNA/C# game by Epsitec SA").
- **2024–2026** — Robert Vokac undertakes the full transformation pipeline described in
  [Chapter 1](ch01-what-is-mobile-eggbert.md): ILSpy decompilation, MonoGame migration, the C++
  rewrite, and the CNA-based port that is the current state of the codebase. This is the second
  copyright line in `LICENSE:4` and the "C++ port by the mobile-eggbert team" half of `Decor.hpp`'s
  authorship note.

Both copyright holders are named consistently between the two places this book has checked
(`LICENSE` and `Decor.hpp`'s file header), which is the strongest confirmation this book can offer
for the authorship chain without access to external, off-repository sources (e.g. the original
Windows Phone Marketplace listing, which this book's source access does not include).

## See also

- [Chapter 1 — What Is Mobile Eggbert](ch01-what-is-mobile-eggbert.md)
- [Chapter 2 — The OpenEggbert Ecosystem Map](ch02-openeggbert-ecosystem-map.md)
- [Chapter 55 — ILSpy Decompilation and C# Stubs](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)
