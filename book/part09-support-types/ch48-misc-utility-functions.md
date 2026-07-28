# Chapter 48: Misc — Utility Functions

`Misc` is a small, static-only geometry toolbox declared in
`include/WindowsPhoneSpeedyBlupi/Misc.hpp` and implemented in
`src/WindowsPhoneSpeedyBlupi/Misc.cpp`. Like `TinyPoint` and `TinyRect` from the previous
chapter, it is a direct port of a C# static class of the same name from the original
WindowsPhoneSpeedyBlupi codebase. Its declared purpose, straight from the header's own doc
comment, is:

*From `Misc.hpp:22-36`:*
```cpp
/**
 * @class Misc
 * @brief Static utility class for 2D geometry operations used throughout the game.
 *
 * @details This class is a C++ port of the original C# static class @c Misc from
 *          WindowsPhoneSpeedyBlupi.  It provides:
 *          - Point rotation around an arbitrary centre via the standard sin/cos matrix.
 *          - Degree-to-radian conversion.
 *          - Integer approach (smooth step toward a target value).
 *          - Normalised-speed-to-integer conversion with guaranteed non-zero result.
 *          - Rectangle inflation, inside test, intersection, and union.
 *
 * @note All methods are static; the class cannot be instantiated or destroyed.
 * @note Status: Ported
 */
class Misc
{
public:
    Misc() = delete;
    ~Misc() = delete;
```

`Misc() = delete` and `~Misc() = delete` enforce, at compile time, that `Misc` can never be
instantiated — every member is `static`, and the class exists purely as a namespace-like
grouping for free functions, mirroring the C# `static class` it was ported from.

The class has nine public methods and one private helper. This chapter documents each one from
its actual implementation in `Misc.cpp`, not from the method name alone.

## Rotation: RotatePointRad and RotateAdjust

The two-argument overload rotates a point around the origin by delegating to the three-argument
form:

*From `Misc.cpp:33-36`:*
```cpp
TinyPoint Misc::RotatePointRad(double angle, const TinyPoint& p)
{
    return RotatePointRad(TinyPoint{}, angle, p);
}
```

The three-argument form does the real work — translate to be relative to `center`, apply the
standard 2D rotation matrix using `std::sin`/`std::cos` (via `System::Math::Sin`/`Cos`), then
translate back:

*From `Misc.cpp:38-61`:*
```cpp
TinyPoint Misc::RotatePointRad(const TinyPoint& center, double angle, const TinyPoint& point)
{
    TinyPoint relativePoint{};
    TinyPoint rotatedPoint{};

    relativePoint.X = point.X - center.X;
    relativePoint.Y = point.Y - center.Y;

    double sinAngle = System::Math::Sin(angle);
    double cosAngle = System::Math::Cos(angle);

    rotatedPoint.X = static_cast<int>(
        static_cast<double>(relativePoint.X) * cosAngle -
        static_cast<double>(relativePoint.Y) * sinAngle);

    rotatedPoint.Y = static_cast<int>(
        static_cast<double>(relativePoint.X) * sinAngle +
        static_cast<double>(relativePoint.Y) * cosAngle);

    rotatedPoint.X += center.X;
    rotatedPoint.Y += center.Y;

    return rotatedPoint;
}
```

This is the textbook rotation matrix
$\begin{pmatrix}\cos\theta & -\sin\theta \\ \sin\theta & \cos\theta\end{pmatrix}$
applied to a point translated relative to `center`, with the result translated back. Because
`TinyPoint`'s fields are `intcs` (32-bit integers), the fractional result of the floating-point
rotation is **truncated toward zero** by the `static_cast<int>` — there is no rounding, so
repeated small rotations can accumulate visible pixel drift, though nothing in the surrounding
code compensates for this; it is simply how integer-pixel rotation works here.

`RotateAdjust` uses `RotatePointRad` to answer a narrower question: given a destination
rectangle that is about to be drawn rotated by some angle, how must its top-left corner shift so
that the rectangle's *visual center* stays put (since rotating a sprite naturally pivots around
its own center, not its top-left corner)?

*From `Misc.cpp:15-31`:*
```cpp
Microsoft::Xna::Framework::Rectangle Misc::RotateAdjust(const Microsoft::Xna::Framework::Rectangle& rect,
                                                        const double angle)
{
    TinyPoint center{};
    center.X = rect.Width / 2;
    center.Y = rect.Height / 2;
    TinyPoint originalCenter = center;
    TinyPoint rotatedCenter = RotatePointRad(angle, originalCenter);
    int offsetX = rotatedCenter.X - originalCenter.X;
    int offsetY = rotatedCenter.Y - originalCenter.Y;
    return {
        rect.getLeftProperty() - offsetX,
        rect.getTopProperty() - offsetY,
        rect.Width,
        rect.Height
    };
}
```

It computes the rectangle's half-size center, rotates that center around the origin, and shifts
the rectangle's top-left position by the resulting offset — width and height are left unchanged.
Note that `RotateAdjust` operates on `Microsoft::Xna::Framework::Rectangle` (the XNA-style
rectangle type from the CNA compatibility layer), not on `TinyRect` — the two rectangle types
coexist in the codebase, and `Misc` bridges between them at this one call site.

This pair is put to real use in `Pixmap.cpp`, for drawing rotated sprites — for example, objects
or effects that spin:

*From `Pixmap.cpp:670-671`:*
```cpp
rotationRad = static_cast<float>(Misc::DegToRad(rotationDeg));
rectangle = Misc::RotateAdjust(rectangle, rotationRad);
```

This confirms the exact call chain speculated in `PLAN.md`: `Pixmap.cpp`'s icon-drawing code
converts a degrees value to radians via `Misc::DegToRad`, then immediately re-centers the
destination rectangle via `Misc::RotateAdjust` before handing it to the underlying draw call.

## DegToRad

*From `Misc.cpp:63-66`:*
```cpp
double Misc::DegToRad(double angle)
{
    return angle * System::Math::PI / 180.0;
}
```

A single-line degree-to-radian conversion, `angle * π / 180`, with no surprises. As shown above,
its sole confirmed call site is `Pixmap.cpp:670`, immediately feeding into `RotateAdjust`.

## Approach: a smooth stepping helper

*From `Misc.cpp:68-79`:*
```cpp
intcs Misc::Approach(intcs actual, const intcs final, const intcs step)
{
    if (actual < final)
    {
        actual = System::Math::Min(actual + step, final);
    }
    else if (actual > final)
    {
        actual = System::Math::Max(actual - step, final);
    }
    return actual;
}
```

`Approach` nudges `actual` toward `final` by at most `step`, clamping so it never overshoots —
classic "ease toward a target" logic for integer values, typically called once per frame. It has
real call sites in `Decor.cpp`, driving Blupi's rotation while running or falling:

*From `Decor.cpp:2303`, `2328`, `4282`, `4286`:*
```cpp
m_blupiLogicRotation = Misc::Approach(m_blupiLogicRotation, num5, 10);
m_blupiLogicRotation = Misc::Approach(m_blupiLogicRotation, 0, 10);
m_blupiRealRotation = Misc::Approach(m_blupiRealRotation, -45, 5);
m_blupiRealRotation = Misc::Approach(m_blupiRealRotation, 45, 5);
```

These calls step Blupi's logical and "real" (visual) rotation angles toward target values (0°,
±45°) by fixed increments of 10 or 5 per call, which is how the character's lean/tilt animation
eases in and out rather than snapping instantly — a detail explored further in
[Chapter 17](../part04-decor-simulation/ch17-blupi-state-machine.md).

## Speed: normalized speed to guaranteed-nonzero integer

*From `Misc.cpp:81-92`:*
```cpp
intcs Misc::Speed(const double speed, const intcs max)
{
    if (speed > 0.0)
    {
        return System::Math::Max(static_cast<intcs>(speed * static_cast<double>(max)), 1);
    }
    if (speed < 0.0)
    {
        return System::Math::Min(static_cast<intcs>(speed * static_cast<double>(max)), -1);
    }
    return 0;
}
```

`Speed` converts a normalized floating-point speed factor (presumably in a small range like
`[-1.0, 1.0]`) into an integer pixel-per-frame speed by multiplying by `max` and truncating. The
important detail is the clamping: a small positive `speed` that would truncate to `0` (e.g.
`0.3 * 2 = 0.6 → 0`) is instead forced up to `1` via `Math::Max(…, 1)`, and symmetrically a small
negative speed is forced down to `-1`. This guarantees that any nonzero input speed produces
actual movement — without it, slow-moving objects could stall completely due to integer
truncation. Real call sites appear in `Decor.cpp`'s Blupi horizontal-movement code, gated by the
build's target frame rate:

*From `Decor.cpp:3404-3405`:*
```cpp
if constexpr (Config::FPS == Fps::Fps20) { end.X += Misc::Speed(m_blupiSpeedX, num3); }
else { m_blupiSubPixelX += Misc::Speed(m_blupiSpeedX, num3) * Config::SPEED_SCALE; int wholePixelsX = static_cast<int>(std::floor(m_blupiSubPixelX)); m_blupiSubPixelX -= wholePixelsX; end.X += wholePixelsX; }
```

At the original 20 FPS timing, `Misc::Speed`'s result is added directly to the movement target.
At other frame rates, its result feeds a sub-pixel accumulator (`m_blupiSubPixelX`) before being
converted back to whole pixels — a frame-rate-independence mechanism that is out of scope for
this chapter but is covered by [Chapter 25](../part04-decor-simulation/ch25-game-speed-and-zoom.md).

## Rectangle helpers: Inflate, IsInside, IntersectRect, UnionRect

The remaining four public methods (plus one private helper) all operate on `TinyRect`.

**`Inflate`** grows (or shrinks, with a negative value) a rectangle uniformly in all four
directions:

*From `Misc.cpp:94-102`:*
```cpp
TinyRect Misc::Inflate(const TinyRect& rect, const intcs value)
{
    TinyRect result{};
    result.Left = rect.Left - value;
    result.Right = rect.Right + value;
    result.Top = rect.Top - value;
    result.Bottom = rect.Bottom + value;
    return result;
}
```

Its one confirmed call site enlarges a UI button's hit-test rectangle by 20 pixels in
`InputPad.cpp`, presumably to make small touch targets easier to hit accurately:

*From `InputPad.cpp:1123`:*
```cpp
buttonRect = Misc::Inflate(buttonRect, 20);
```

**`IsInside`** performs an inclusive point-in-rectangle test:

*From `Misc.cpp:104-107`:*
```cpp
bool Misc::IsInside(const TinyRect& rect, const TinyPoint& p)
{
    return p.X >= rect.Left && p.X <= rect.Right && p.Y >= rect.Top && p.Y <= rect.Bottom;
}
```

All four boundary comparisons are `>=`/`<=` (inclusive on both edges), meaning a point exactly on
the rectangle's border counts as inside. This is the workhorse of touch/click hit-testing across
the input layer, called repeatedly in `InputPad.cpp` (closing the virtual keyboard, testing
individual key rectangles, testing the accelerometer pad bounds, testing UI buttons — lines 539,
557, 899, and 1126) and once in `Slider.cpp:100` for the slider's drag handle.

**`IntersectRect`** and **`UnionRect`** compute the overlap and bounding-box of two rectangles
respectively, both sharing the same output-parameter style (`bool` return, `TinyRect&` out-param):

*From `Misc.cpp:109-127`:*
```cpp
bool Misc::IntersectRect(TinyRect& dst, const TinyRect& src1, const TinyRect& src2)
{
    dst = TinyRect{};
    dst.Left = System::Math::Max(src1.Left, src2.Left);
    dst.Right = System::Math::Min(src1.Right, src2.Right);
    dst.Top = System::Math::Max(src1.Top, src2.Top);
    dst.Bottom = System::Math::Min(src1.Bottom, src2.Bottom);
    return !IsRectEmpty(dst);
}

bool Misc::UnionRect(TinyRect& dst, const TinyRect& src1, const TinyRect& src2)
{
    dst = TinyRect();
    dst.Left = System::Math::Min(src1.Left, src2.Left);
    dst.Right = System::Math::Max(src1.Right, src2.Right);
    dst.Top = System::Math::Min(src1.Top, src2.Top);
    dst.Bottom = System::Math::Max(src1.Bottom, src2.Bottom);
    return !IsRectEmpty(dst);
}
```

`IntersectRect` takes the max of the two lefts/tops and the min of the two rights/bottoms
(shrinking toward the overlap); `UnionRect` does the reverse (min of lefts/tops, max of
rights/bottoms, growing to cover both). Both return whether the resulting rectangle is
non-empty, via the private helper:

*From `Misc.cpp:129-132`:*
```cpp
bool Misc::IsRectEmpty(const TinyRect& rect)
{
    return rect.getWidthProperty() <= 0 || rect.getHeightProperty() <= 0;
}
```

`IntersectRect` is by far the most heavily used function in the entire `Misc` class — it appears
more than a dozen times in `Decor.cpp`, almost always as a bounding-box overlap check between two
game objects or between an object and a collision region (e.g. `Decor.cpp:6746`, `6765`, `8022`,
`9140`, `9210`, `9221`, `9431`, `9571`, `9633`, `9671`, `9758`, `9763`, `9794`, `9826`, `9858`).
A representative example, testing whether two moving objects' bounding boxes overlap:

*From `Decor.cpp:9140`:*
```cpp
if (Misc::IntersectRect(dst, src2, src))
```

This makes `IntersectRect` a core building block of the collision-detection code covered in
[Chapter 21](../part04-decor-simulation/ch21-physics-and-collision.md). By contrast, a grep across
the entire codebase turns up **no call sites for `UnionRect`** outside its own definition and
declaration — it is implemented and exposed but, as far as the current source shows, unused
elsewhere in the game logic.

## Summary table

| Method | Purpose | Confirmed call sites |
|---|---|---|
| `RotatePointRad(angle, p)` | Rotate a point around the origin | Delegates to the 3-arg overload |
| `RotatePointRad(center, angle, point)` | Rotate a point around an arbitrary center | Called by `RotateAdjust` |
| `RotateAdjust(rect, angle)` | Re-center a rectangle's top-left after rotation | `Pixmap.cpp:671` |
| `DegToRad(angle)` | Degrees → radians | `Pixmap.cpp:670` |
| `Approach(actual, final, step)` | Step an integer toward a target | `Decor.cpp:2303,2328,4282,4286` |
| `Speed(speed, max)` | Normalized speed → guaranteed-nonzero integer speed | `Decor.cpp:3404-3405,3462-3463` |
| `Inflate(rect, value)` | Grow/shrink a rectangle uniformly | `InputPad.cpp:1123` |
| `IsInside(rect, p)` | Inclusive point-in-rectangle test | `InputPad.cpp:539,557,899,1126`; `Slider.cpp:100` |
| `IntersectRect(dst, src1, src2)` | Overlap of two rectangles | 14+ sites in `Decor.cpp` |
| `UnionRect(dst, src1, src2)` | Bounding box of two rectangles | None found outside `Misc.cpp` itself |

## See also

- [Chapter 47: TinyPoint and TinyRect](ch47-tinypoint-tinyrect.md) — the value types every `Misc`
  method operates on, including the non-standard `TinyRect` field order that `Misc`'s internals
  quietly work around by always addressing fields by name.
- [Chapter 21: Physics and Collision](../part04-decor-simulation/ch21-physics-and-collision.md) —
  the primary consumer of `Misc::IntersectRect` for bounding-box overlap tests.
- [Chapter 28: Pixmap/IPixmap](../part05-sprites-rendering-animation/ch28-pixmap-ipixmap.md) — where
  `Misc::DegToRad` and `Misc::RotateAdjust` are used together to draw rotated sprites.
- [Chapter 41: InputPad](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md) — the
  heaviest consumer of `Misc::IsInside` and `Misc::Inflate` for touch/click hit-testing.
