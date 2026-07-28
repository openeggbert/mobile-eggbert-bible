# Chapter 37: Slider — UI Control

## A single-purpose widget

`Slider` is the smallest UI class in Part V, and the most narrowly scoped: a horizontal draggable
control used, per its own header comment, for exactly one setting in the entire game.

*From `Slider.hpp:17-33`:*
```cpp
/**
 * @class Slider
 * @brief Horizontal UI slider widget for adjusting a continuous setting.
 *
 * @details Renders a draggable thumb (94 x 94 px icon) centred at the
 *          X position corresponding to the current value on a 248-pixel-wide
 *          track.  The usable track extent runs from topLeftCorner.X + 22
 *          to topLeftCorner.X + 226 (248 - 22).  Decorative icons are drawn
 *          to the left and right of the track to indicate the min/max extremes.
 * ...
 * @note This class is UI code and does not directly affect gameplay state.
 */
```

The one real caller of this widget is the settings screen's accelerometer-sensitivity control — a
continuous `[0, 1]` value, mapped linearly onto a fixed-width horizontal track. Unlike `Jauge`
([Chapter 36](ch36-jauge-hud-gauges.md)), which is a pure display widget, `Slider` also handles
input: `Move()` converts a touch/click position directly into a new slider value.

## A reused sprite, borrowed from three different atlases

`Slider::Draw()` is a compact demonstration of how thoroughly this codebase reuses existing sprite
assets rather than commissioning dedicated art for every UI element — its three visual pieces are
borrowed whole from three different atlases already covered in earlier chapters:

*From `Slider.cpp:53-90`:*
```cpp
void Slider::Draw(IPixmap& pixmap)
{
    TinyPoint tinyPoint{};
    tinyPoint.X = getTopLeftCornerProperty().X - pixmap.getOriginProperty().X;
    tinyPoint.Y = getTopLeftCornerProperty().Y - pixmap.getOriginProperty().Y;
    TinyRect tinyRect{0, 124, 0, 22};
    pixmap.DrawPart(PixmapChannel::Jauge, tinyPoint, tinyRect, 2.0);

    intcs num = (intcs)((double)(getPosRightProperty() - getPosLeftProperty()) * getValueProperty());
    intcs num2 = getTopLeftCornerProperty().Y + 22;
    intcs num3 = 94;
    TinyRect tinyRect2{
        getPosLeftProperty() + num - num3 / 2, getPosLeftProperty() + num + num3 / 2,
        num2 - num3 / 2, num2 + num3 / 2
    };
    pixmap.DrawIcon(PixmapChannel::Pad, 1, tinyRect2, 1.0, false);

    TinyRect tinyRect3{
        getTopLeftCornerProperty().X - 65, getTopLeftCornerProperty().X - 65 + 60,
        getTopLeftCornerProperty().Y - 10, getTopLeftCornerProperty().Y - 10 + 60
    };
    pixmap.DrawIcon(PixmapChannel::Element, 37, tinyRect3, 1.0, false);

    TinyRect tinyRect4{
        getTopLeftCornerProperty().X + 248 + 5, getTopLeftCornerProperty().X + 248 + 5 + 60,
        getTopLeftCornerProperty().Y - 10, getTopLeftCornerProperty().Y - 10 + 60
    };
    pixmap.DrawIcon(PixmapChannel::Element, 38, tinyRect4, 1.0, false);
}
```

Three distinct draw calls, three distinct channels:

1. **The track**, drawn via `DrawPart(PixmapChannel::Jauge, ..., zoom=2.0)` — the exact same
   124×22 gauge-background rectangle `Jauge::Draw()` uses for its own empty-gauge background
   ([Chapter 36](ch36-jauge-hud-gauges.md)), reused here at double scale rather than as a
   dedicated slider-track asset. The `zoom = 2.0` argument doubles the on-screen size of the same
   source rectangle `Jauge` draws at 1x elsewhere.
2. **The thumb**, drawn via `DrawIcon(PixmapChannel::Pad, 1, ...)` — icon `1` of the touch-input pad
   atlas ([Chapter 29](ch29-sprite-atlas-system.md)), a 94×94-pixel destination rectangle centered
   on the current value's X position. Borrowing a `Pad`-channel icon for a settings-screen slider
   thumb (rather than the `Button` channel, which exists specifically for UI buttons) is a real,
   notable reuse decision — the same round button-like glyph used for on-screen touch controls
   elsewhere doubles as this slider's draggable handle.
3. **Two decorative end-icons**, drawn via `DrawIcon(PixmapChannel::Element, 37, ...)` and
   `DrawIcon(PixmapChannel::Element, 38, ...)` — icons `37`/`38` of the `Element` atlas
   ([Chapter 29](ch29-sprite-atlas-system.md)), flanking the track on the left and right to indicate
   the sensitivity control's min/max extremes. `Element` is otherwise this book's tile-rendering and
   collectible-effect atlas ([Chapters 16](../part04-decor-simulation/ch16-tile-map.md) and
   [32](ch32-creature-and-object-animation-catalog.md)) — its icons `37`/`38` are apparently a small
   pair of general-purpose sensitivity/indicator glyphs living in the same shared sheet as tile art
   and creature sprites, rather than a UI-dedicated icon range.

The screen-space translation at the top of `Draw()` — subtracting `pixmap.getOriginProperty()` from
the slider's own HUD-space `topLeftCorner` before the first `DrawPart()` call — is notable precisely
because it is the *opposite* direction of the origin adjustment `Pixmap::DrawPart()` itself already
applies for the `Jauge` channel specifically (`Pixmap.cpp:465-477`,
[Chapter 28](ch28-pixmap-ipixmap.md)/[Chapter 36](ch36-jauge-hud-gauges.md)): `Slider::Draw()`
subtracts the origin here, and `DrawPart()`'s own `Jauge`-specific branch adds it back before
issuing the actual draw call — the two operations cancel out, leaving the net effect equivalent to
passing the original HUD-space coordinate directly. This is very likely a harmless redundancy
carried over from the original C# port rather than a deliberate double-transform, but it is worth
stating precisely as observed rather than silently "correcting" it into a simpler description that
the real code does not actually match.

## The track geometry: two private accessors

*From `Slider.cpp:45-50`:*
```cpp
intcs Slider::getPosLeftProperty() const { return getTopLeftCornerProperty().X + 22; }

intcs Slider::getPosRightProperty() const
{
    return getTopLeftCornerProperty().X + 248 - 22;
}
```

The track's usable extent is narrower than its visual 248-pixel width on both ends — a 22-pixel
margin on the left (matching the thumb icon's own half-width-ish clearance) and an identical margin
subtracted from the right, leaving a `248 - 44 = 204`-pixel usable range for the thumb's center
position to travel across. These two accessors are the single source of truth for that geometry;
both `Draw()`'s thumb-centering math and `Move()`'s value-mapping math below call them rather than
duplicating the `+22`/`-22` constants inline.

## `Move()`: mapping a touch point to a value

*From `Slider.cpp:92-113`:*
```cpp
bool Slider::Move(TinyPoint pos)
{
    TinyRect tinyRect{
        getTopLeftCornerProperty().X - 50, getTopLeftCornerProperty().X + 248 + 50,
        getTopLeftCornerProperty().Y - 50, getTopLeftCornerProperty().Y + 44 + 50
    };
    if (Misc::IsInside(tinyRect, pos))
    {
        double val = ((double)pos.X - (double)getPosLeftProperty()) / (double)(getPosRightProperty() -
            getPosLeftProperty());
        val = System::Math::Max(val, 0.0);
        val = System::Math::Min(val, 1.0);
        if (getValueProperty() != val)
        {
            setValueProperty(val);
            return true;
        }
    }
    return false;
}
```

The hit-test rectangle is deliberately much larger than the visible track — expanded by a generous
50 pixels in every direction beyond the nominal `248×44` control bounds. This is a standard
touch-target usability accommodation: a finger (or an imprecise mouse click) landing slightly
outside the visually-drawn slider still registers as a valid drag, rather than requiring
pixel-perfect precision on a control whose visible track is comparatively thin.

Once a touch point is confirmed inside that generous hit region, the actual value computation is a
plain linear interpolation: `(pos.X - posLeft) / (posRight - posLeft)`, clamped to `[0.0, 1.0]` via
`System::Math::Max`/`Min`. Because the clamp happens *after* the division rather than being folded
into the hit-test itself, a touch landing within the expanded 50-pixel margin but outside the actual
track produces a value pinned to exactly `0` or `1` — dragging past either end of the visible track
snaps the slider cleanly to its minimum or maximum rather than doing nothing or producing an
out-of-range value. `Move()` returns `true` only when the computed value genuinely differs from the
slider's current value — a direct floating-point inequality check, not an epsilon comparison — so a
caller polling `Move()` every frame during a drag can cheaply detect "did anything actually change"
without needing its own dirty-tracking logic, similar in spirit to (though structurally simpler
than) `Jauge`'s explicit redraw-dirty flag scheme ([Chapter 36](ch36-jauge-hud-gauges.md)).

## A preserved decompilation artifact

`Slider`'s constructor carries a small, explicitly-flagged piece of porting history worth quoting
directly, because it is a good example of this codebase's general practice of documenting
suspicious decompiled behavior rather than silently "fixing" it based on a guess:

*From `Slider.cpp:28-35`:*
```cpp
Slider::Slider(TinyPoint topLeftCorner, double value)
{
    this->setTopLeftCornerProperty(topLeftCorner);
    // Decompiled C# shows "value = Value", which is likely reversed by decompilation.
    // Intentionally initializing Value from constructor parameter.
    // value = Value;
    this->setValueProperty(value);
}
```

The original decompiled C# source (from the ILSpy-based migration path covered in
[Chapter 55](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md))
apparently showed the assignment written as `value = Value` — reading a property *into* the
constructor's own parameter, which would be a functionally useless no-op and is almost certainly an
artifact of how the decompiler represented a C# property backing-field initializer, not the
original developer's actual intent. Rather than reproducing that likely-backwards statement
literally, the port's author chose the sensible interpretation (initialize the object's `Value`
property *from* the constructor parameter) and left the reasoning — and the suspicious original
line, commented out — directly in the source for a future reader to evaluate.

## `IDATA`/`DDATA`: property-style accessors

`Slider::Value` uses the same `SharpRuntime` property-macro convention seen elsewhere in this
codebase's ported classes — `DDATA(double, Value)` in the header declares the getter/setter pair,
and `IDATA(double, Value, Slider)` in the source provides the implementation
(`Slider.hpp:60`, `Slider.cpp:44`) — a small piece of C#-property-emulation infrastructure that lets
`getValueProperty()`/`setValueProperty()` behave like the original C# `Value` property without this
class needing to hand-write both accessor bodies itself.

## See also

- [Chapter 28 — Pixmap/IPixmap](ch28-pixmap-ipixmap.md)
- [Chapter 29 — The Sprite Atlas System](ch29-sprite-atlas-system.md)
- [Chapter 32 — The Creature and Object Animation Catalog](ch32-creature-and-object-animation-catalog.md)
- [Chapter 36 — Jauge: HUD Gauges](ch36-jauge-hud-gauges.md)
- [Chapter 41 — InputPad: Touch, Keyboard, Accelerometer](../part07-input/ch41-inputpad-touch-keyboard-accelerometer.md)
- [Chapter 55 — ILSpy Decompilation and C# Stubs](../part11-history-and-practice/ch55-ilspy-decompilation-and-csharp-stubs.md)
