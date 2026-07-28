# Chapter 47: TinyPoint and TinyRect

`TinyPoint` and `TinyRect` are the two smallest, most heavily used value types in the entire
`mobile-eggbert` codebase. Between them they carry every screen coordinate, every sprite
destination rectangle, and every touch/click hit-test used by `Pixmap`, `Decor`, `InputPad`,
`Jauge`, and `Slider`. They are declared in
`include/WindowsPhoneSpeedyBlupi/TinyPoint.hpp` and
`include/WindowsPhoneSpeedyBlupi/TinyRect.hpp`, with the non-trivial `TinyRect` methods
implemented in `src/WindowsPhoneSpeedyBlupi/TinyRect.cpp`.

Both types are direct, field-for-field ports of C# structs from the original
WindowsPhoneSpeedyBlupi codebase (the Windows Phone/XNA-era C# game that `mobile-eggbert` is a
C++ port of). Both use `intcs`, a `SharpRuntime` typedef for `int32_t`, for every coordinate —
matching the original C# `int` exactly.

## TinyPoint: a plain 2D integer point

`TinyPoint` (`TinyPoint.hpp:35`) is about as simple as a struct gets:

*From `TinyPoint.hpp:35`:*
```cpp
struct TinyPoint
{
    intcs X; ///< @brief Horizontal (column) coordinate in pixels.
    intcs Y; ///< @brief Vertical (row) coordinate in pixels.

    TinyPoint()
        : X(0), Y(0)
    {
    }

    TinyPoint(intcs x, intcs y)
        : X(x), Y(y)
    {
    }

    [[nodiscard]] std::string ToString() const
    {
        std::ostringstream oss;
        oss << X << ";" << Y;
        return oss.str();
    }
};
```

Two fields, `X` and `Y`, in the conventional order. There is nothing ambiguous about
`TinyPoint`'s constructor order — `TinyPoint(x, y)` always means horizontal-then-vertical, exactly
as every C++ programmer would expect from `SDL_Point`, `POINT`, or `sf::Vector2i`. The
default constructor zero-initializes both fields (equivalent to `default(TinyPoint)` in the
original C#), and `ToString()` produces the compact form `"X;Y"` (e.g. `"10;20"`), intended for
logging rather than serialization — nothing in the codebase parses this string back into a
`TinyPoint`.

`TinyPoint` is a plain aggregate: no heap allocation, no virtual functions, cheap to copy and
pass by value. It appears throughout `Decor.cpp` as the carrier for tile-grid pixel positions,
e.g. `TinyPoint pos{celx * 64, cely * 64}` (`Decor.cpp:622`), and throughout `InputPad.cpp` as
the carrier for a single touch or click coordinate, e.g. the `touchesOrClicks` collection
iterated as `for (const TinyPoint& tp : touchesOrClicks)` (`InputPad.cpp:533`).

## TinyRect: the rectangle with a trap built into its declaration

`TinyRect` (`TinyRect.hpp:46`) looks, at first glance, like an equally unremarkable four-field
rectangle. It is not.

> ### ⚠ Warning — Non-standard field order
>
> **`TinyRect`'s fields are declared, and its four-argument constructor accepts its arguments,
> in the order `Left, Right, Top, Bottom` — NOT the conventional `Left, Top, Right, Bottom`
> order used by Win32's `RECT`, SDL's `SDL_Rect`-adjacent conventions, or almost every other
> rectangle type a C++ programmer has ever touched.**
>
> This is not a typo and not something introduced by the C++ port — it is preserved exactly
> from the original C# `TinyRect` struct in WindowsPhoneSpeedyBlupi, and the header itself
> carries a `@warning` Doxygen block calling it out (`TinyRect.hpp:5-11`, repeated at
> `TinyRect.hpp:36-41`). `mobile-eggbert`'s own `CLAUDE.md` flags this exact gotcha for anyone
> touching the codebase. **Passing arguments in the "obvious" `left, top, right, bottom` order
> to the four-argument constructor produces a rectangle with `Top` and `Right` silently
> swapped** — no compiler error, no runtime assertion, just wrong geometry that only shows up
> as a misplaced sprite or a hit-test that inexplicably fails near one edge.

Here is the actual declaration:

*From `TinyRect.hpp:46-52`:*
```cpp
struct TinyRect
{
    intcs Left;   ///< @brief Left edge (minimum X) of the rectangle in pixels.
    intcs Right;  ///< @brief Right edge (maximum X) of the rectangle in pixels.
    intcs Top;    ///< @brief Top edge (minimum Y) of the rectangle in pixels.
    intcs Bottom; ///< @brief Bottom edge (maximum Y) of the rectangle in pixels.
```

And the four-argument constructor, whose parameter order matches the field order exactly:

*From `TinyRect.hpp:80-83`:*
```cpp
TinyRect(const intcs left, const intcs right, const intcs top, const intcs bottom)
    : Left(left), Right(right), Top(top), Bottom(bottom)
{
}
```

A real, correct call site exists in `InputPad.cpp`, constructing a touch-pad's bounding
rectangle from a center point and radius:

*From `InputPad.cpp:1473`:*
```cpp
return TinyRect(center.X - radius, center.X + radius, center.Y - radius, center.Y + radius);
```

Read the argument order carefully: `center.X - radius` (left), `center.X + radius` (right),
`center.Y - radius` (top), `center.Y + radius` (bottom) — `Left, Right, Top, Bottom`, exactly
matching the declared field order. If you were porting similar code from a mental model of
"the usual" rectangle constructor, you would instinctively write
`TinyRect(left, top, right, bottom)` and get a rectangle whose `Right` field actually holds the
top coordinate and whose `Top` field actually holds the right coordinate — a bug that would
compile silently and only manifest as scrambled geometry at runtime.

In practice, most of the codebase sidesteps the constructor entirely by default-constructing a
`TinyRect` and then assigning each named field individually — which is unambiguous precisely
*because* it names each field. This pattern appears throughout `Decor.cpp` and `Jauge.cpp`:

*From `Jauge.cpp:75-78`:*
```cpp
rect.Left = 0;
rect.Right = 124;
rect.Top = 0;
rect.Bottom = 22;
```

This is likely the safest idiom in the codebase precisely because it makes the non-standard
order irrelevant — each assignment names its own field, so there is no positional ambiguity to
get wrong. Chapters and code elsewhere in this book that show `TinyRect` construction favor this
field-by-field style for the same reason.

### Other constructors

`TinyRect` also has a default constructor and a single-point constructor:

*From `TinyRect.hpp:61-64` and `TinyRect.cpp:18-21`:*
```cpp
TinyRect()
    : Left(0), Right(0), Top(0), Bottom(0)
{
}
```
```cpp
TinyRect::TinyRect(TinyPoint point)
    : Left(point.X), Right(point.X), Top(point.Y), Bottom(point.Y)
{
}
```

The default constructor zero-initializes all four edges, equivalent to `default(TinyRect)` in
C#. The single-`TinyPoint` constructor is `explicit` and produces a **degenerate, zero-area
rectangle** anchored at the point: `Left == Right == point.X` and `Top == Bottom == point.Y`.
The header's own doc comment explains its purpose precisely: it is "used by icon-drawing APIs
where a zero-area TinyRect signals 'use the icon's default dimensions'" (`TinyRect.hpp:90-91`) —
i.e. callers construct `TinyRect(pos)` to mean "just draw at this position, don't clip or resize
the source rectangle," and the zero width/height is a sentinel value interpreted downstream by
the `Pixmap` drawing code (covered in [Chapter 28](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md)),
not a literal empty rectangle to be rendered.

### Width, Height, and ToString

The two computed properties are implemented in `TinyRect.cpp`:

*From `TinyRect.cpp:23-31`:*
```cpp
intcs TinyRect::getWidthProperty() const
{
    return Right - Left;
}

intcs TinyRect::getHeightProperty() const
{
    return Bottom - Top;
}
```

Both are straightforward subtractions and, notably, are **not** clamped to zero — a rectangle
with `Right < Left` or `Bottom < Top` yields a negative width or height, which the header
explicitly documents as a valid, if degenerate, outcome ("may be zero or negative for degenerate
rectangles," `TinyRect.hpp:33-34`). Downstream code that treats a rectangle as "empty" (such as
`Misc::IsRectEmpty`, covered in [Chapter 48](ch48-misc-utility-functions.md)) checks for `width <= 0 ||
height <= 0` rather than relying on any invariant enforced by the struct itself — `TinyRect` does
no validation of its own fields anywhere.

`ToString()` is worth a second look precisely because of the field-order gotcha:

*From `TinyRect.hpp:133-138`:*
```cpp
[[nodiscard]] std::string ToString() const
{
    std::ostringstream oss;
    oss << Left << ";" << Top << ";" << Right << ";" << Bottom;
    return oss.str();
}
```

Notice that `ToString()` prints the fields in the order `Left; Top; Right; Bottom` — the
*conventional* display order — even though the fields are stored (and the four-argument
constructor accepts them) in `Left, Right, Top, Bottom` order. This is internally consistent
(the doc comment at `TinyRect.hpp:126-129` documents exactly this display format), but it means
a developer skimming a debug log line produced by `ToString()` sees coordinates in the familiar
order, which could reinforce the wrong mental model of the constructor's parameter order if they
haven't read the header's warning. The takeaway: the *display* format is conventional; the
*storage and construction* order is not. Do not infer one from the other.

## TinyRect is not the only rectangle in the codebase

It is worth being explicit that `TinyRect` is **not** the same type as
`Microsoft::Xna::Framework::Rectangle`, the XNA-compatibility rectangle type supplied by the CNA
framework (`cna/include/Microsoft/Xna/Framework/Rectangle.hpp`) that `mobile-eggbert` also uses.
That type stores its geometry as `X, Y, Width, Height` — the conventional XNA layout, with no
field-order surprise:

*From `Rectangle.hpp:15-30` (CNA, referenced only for contrast):*
```cpp
struct Rectangle
{
    intcs X;
    intcs Y;
    intcs Width;
    intcs Height;
```

`Misc::RotateAdjust` (covered in the next chapter) actually operates on this XNA `Rectangle`
type, not on `TinyRect` — it is called from `Pixmap.cpp` while preparing a sprite's destination
rectangle for rotated drawing. So the codebase has two independent rectangle representations in
active use side by side: `TinyRect` (`Left, Right, Top, Bottom`, the WindowsPhoneSpeedyBlupi-native
type used for hit-testing, sprite-part sub-rectangles, and most `Decor`/`InputPad` geometry) and
XNA's `Rectangle` (`X, Y, Width, Height`, used where code interacts more directly with the
CNA/XNA-style drawing API). Neither converts to the other automatically — there is no implicit
constructor or conversion operator between them anywhere in either header — so a developer moving
a rectangle value between `Decor`/`InputPad`-style code and `Pixmap`'s XNA-facing drawing calls
must convert deliberately, field by field, and must do so being careful about which of the two
very different field orderings applies on each side of the conversion. This makes the
`TinyRect` field-order warning above doubly important: the two rectangle types don't just differ
in field order convention (edges vs. origin+size), they differ in field *order* even where they
overlap conceptually (`Left`/`X` both come first, but `TinyRect`'s second field is `Right` while
`Rectangle`'s second field is `Y`).

## Why the order is this way

Nothing in either header or the `.cpp` file explains *why* the original C# struct chose
`Left, Right, Top, Bottom` over the more common ordering — it is simply inherited unchanged from
WindowsPhoneSpeedyBlupi, and the C++ port's own documentation comments (added during porting,
per the `@note Status: Ported` / `@note Status: IMPLEMENTED` markers throughout) treat
preserving it as a deliberate compatibility decision, not an oversight: "This order is preserved
from the original C# WindowsPhoneSpeedyBlupi codebase" (`TinyRect.hpp:9`, `TinyRect.cpp:8-9`).
Changing the field order now would require touching every field-by-field assignment site across
`Decor.cpp`, `InputPad.cpp`, `Jauge.cpp`, and `Slider.cpp` — a large, error-prone refactor for a
cosmetic gain — so the port keeps the original layout and instead documents it aggressively with
`@warning` blocks in three places (the file header comment, the struct's own doc comment, and the
four-argument constructor's doc comment).

## Practical guidance for anyone modifying this code

- Prefer field-by-field assignment (`rect.Left = …; rect.Right = …;`) over the four-argument
  constructor wherever the call site isn't already using it — it eliminates the ordering risk
  entirely.
- If you do use `TinyRect(a, b, c, d)`, mentally read it as `TinyRect(left, right, top, bottom)`
  and double-check against the header before trusting a "looks right" ordering.
- When porting *new* C# code that constructs a `TinyRect` positionally, check the C# call site's
  actual argument order rather than assuming — the C# source itself follows this same unusual
  layout, so a faithful port should too.
- `Misc`'s rectangle helper functions (`Inflate`, `IsInside`, `IntersectRect`, `UnionRect`,
  covered in the next chapter) all operate on named fields internally, so they are safe to use
  regardless of how the rectangle was originally constructed.

## See also

- [Chapter 48: Misc — Utility Functions](ch48-misc-utility-functions.md) — the geometry helpers
  (`Inflate`, `IsInside`, `IntersectRect`, `UnionRect`, point rotation) that consume `TinyPoint`
  and `TinyRect` values.
- [Chapter 28: Pixmap/IPixmap](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md) — the
  sprite-drawing layer where `TinyRect` is used as both source and destination rectangles, and
  where the zero-area "use default dimensions" sentinel from the `TinyPoint` constructor is
  interpreted.
- [Chapter 41: InputPad](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md) — the
  touch/keyboard/accelerometer input layer, the heaviest consumer of `TinyPoint` for touch
  coordinates and `TinyRect` for hit-testing UI regions.
- [Chapter 16: The Tile Map](../part04-decor-simulation/ch16-tile-map.md) — the coordinate systems
  (tile-grid vs. pixel-space) that `TinyPoint` values move between throughout `Decor.cpp`.
