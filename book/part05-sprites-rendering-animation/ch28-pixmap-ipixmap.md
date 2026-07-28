# Chapter 28: Pixmap and IPixmap — the Sprite Rendering Layer

## The seam between gameplay and the screen

Every earlier part of this book has been about *what the game knows*: the tile grid, Blupi's
state machine, moving objects, enemy AI. None of that code draws a single pixel. When `Decor::Build()`
(Chapter 15) wants Blupi's current frame to actually appear on screen, it does not touch a
texture, a vertex buffer, or a `SpriteBatch` directly — it calls `m_pixmap->QuickIcon(PixmapChannel::Blupi,
m_blupiIcon, m_blupiPos)` and forgets about it. `IPixmap` and its concrete implementation `Pixmap`
are that seam: the entire rendering back-end for Speedy Blupi, and the only place in the codebase
that knows what a `Texture2D` or a `SpriteBatch::Draw()` call looks like.

*From `IPixmap.hpp:22-47`:*
```cpp
/**
 * @class IPixmap
 * @brief Interface for the game's sprite/rendering subsystem.
 *
 * @details IPixmap abstracts all drawing operations needed by the gameplay and UI layers.
 * ...
 * Coordinate conventions used by this interface:
 * - Game-space (logical): 640x480 base resolution, origin top-left.
 * - HUD-space: same as game-space but offset by the pixmap origin (for viewport centering).
 * - Screen-space: physical pixels after zoom/origin transform applied by the implementation.
 */
```

`Pixmap` is the sole implementation (`Pixmap.hpp:73`, `Pixmap : public IPixmap`). The interface
exists so that gameplay code (`Decor`, `Game1`, `Jauge`, `Slider`, `Text`) depends only on the
abstract contract, never on `SpriteBatch`, `Texture2D`, or any XNA/CNA graphics type directly —
this book's scope note applies squarely here: *how* `SpriteBatch::Draw()` gets a triangle onto a
GPU backend is CNA's job (see [Chapter 14](../part03-architecture/ch14-xna-api-via-cna.md) and
`cna-bible` for that), and this chapter stays on the mobile-eggbert side of the line: what
`Pixmap` calls, and why.

## Three coordinate spaces, one class

`Pixmap.hpp`'s own file-header table names the three spaces every draw call in this class moves
between:

*From `Pixmap.hpp:11-16`:*
```
| Space       | Description                                        |
|-------------|-----------------------------------------------------|
| Game-space  | Logical 640x480, origin top-left.                  |
| HUD-space   | Game-space offset by (originX, originY).           |
| Screen-space| Physical pixels after the zoom transform.          |
```

`Decor` and `Game1` (Chapter 12) always think in game-space — a fixed 640×480 logical canvas,
regardless of the player's actual window or screen size. `Pixmap` is responsible for the two
transforms that turn a game-space coordinate into an actual on-screen pixel:

1. **Viewport zoom** (`zoom`), recomputed by `UpdateGeometry()` every time the geometry might have
   changed:

   *From `Pixmap.cpp:306-319`:*
   ```cpp
   void Pixmap::UpdateGeometry()
   {
       double screenWidth = graphics.getGraphicsDeviceProperty()->getViewportProperty().getWidthProperty();
       double screenHeight = graphics.getGraphicsDeviceProperty()->getViewportProperty().getHeightProperty();
       if (CNA::getCurrentPlatform() == CNA::Platform::Android && screenHeight > 480)
       {
           screenWidth = screenHeight * (640.0 / 480.0);
       }
       double widthScale = screenWidth / 640.0;
       double heightScale = screenHeight / 480.0;
       zoom = System::Math::Min(widthScale, heightScale);
       originX = (screenWidth - 640.0 * zoom) / 2.0;
       originY = (screenHeight - 480.0 * zoom) / 2.0;
   }
   ```

   `zoom` is the smaller of the width and height scale factors, so the logical 640×480 canvas is
   always fully visible and never stretched non-uniformly — a classic letterbox/pillarbox fit.
   `originX`/`originY` are the resulting blank margins on whichever axis has slack. The Android
   branch is a special case: because Android viewports are frequently much taller than 4:3,
   `screenWidth` is first replaced with an equivalent 4:3-normalized value derived from
   `screenHeight`, so a tall phone screen still computes a sensible `zoom` instead of one distorted
   by an unusually large height.

2. **Hotspot zoom** (`hotSpotZoom`), a second, independent scale factor used only for the in-game
   camera-zoom feature and applied only when a draw call explicitly opts in via `useHotSpot = true`
   (`SetHotSpot()`, `Pixmap.cpp:144-149`, and `GetDstRectangle()` below).

`HotSpotToHud()` is the one coordinate-conversion helper gameplay code calls directly, and its
implementation is exactly the inverse of the hotspot transform documented in its own header:

*From `Pixmap.cpp:130-142`:*
```cpp
TinyPoint Pixmap::HotSpotToHud(TinyPoint pos)
{
    if (hotSpotZoom == 0.0)
    {
        return pos;
    }
    return {
        static_cast<intcs>(static_cast<double>(pos.X - static_cast<intcs>(hotSpotX)) / hotSpotZoom) + static_cast<
            intcs>(hotSpotX) - static_cast<intcs>(originX),
        static_cast<intcs>(static_cast<double>(pos.Y - static_cast<intcs>(hotSpotY)) / hotSpotZoom) + static_cast<
            intcs>(hotSpotY) - static_cast<intcs>(originY)
    };
}
```

A zero `hotSpotZoom` returns the input unchanged rather than dividing by zero — a defensive guard
worth noting given that `hotSpotZoom` defaults to `1.0` (`Pixmap.hpp:114`) and is only ever set
away from that default via `SetHotSpot()`.

## Ten texture atlases, one owning class

`Pixmap` owns every `Texture2D` the game ever draws from — thirteen member fields covering the ten
distinct image assets shipped in `Content/icons/` and `Content/backgrounds/` (`blupi1.png` is
shared by three separate `PixmapChannel` values, discussed in [Chapter 29](ch29-sprite-atlas-system.md)):

*From `Pixmap.hpp:133-145`:*
```cpp
Texture2D bitmapText;          ///< PixmapChannel::Text
Texture2D bitmapButton;        ///< PixmapChannel::Button
Texture2D bitmapJauge;         ///< PixmapChannel::Jauge
Texture2D bitmapBlupi;         ///< PixmapChannel::Blupi
Texture2D bitmapBlupi1;        ///< shared by Blupi1_11/12/13
Texture2D bitmapObject;        ///< PixmapChannel::Object
Texture2D bitmapElement;       ///< PixmapChannel::Element
Texture2D bitmapExplo;         ///< PixmapChannel::Explosion
Texture2D bitmapPad;           ///< PixmapChannel::Pad
Texture2D bitmapSpeedyBlupi;   ///< PixmapChannel::SpeedyBlupiBackground
Texture2D bitmapBlupiYoupie;   ///< PixmapChannel::BlupiYoupieBackground
Texture2D bitmapGear;          ///< PixmapChannel::GearBackground
Texture2D bitmapBackground;    ///< PixmapChannel::Background, swapped by BackgroundCache()
```

`LoadContent()` loads every one of these exactly once, at startup, choosing an asset sub-directory
prefix based on `Config::RESOLUTION_SCALE` (`icons/` at 1x, `icons2x/`/`icons4x/` at higher
scales — see [Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md) for the
`RESOLUTION_SCALE`/`ScaleAsset()` mechanism itself, which this chapter treats only as a given):

*From `Pixmap.cpp:288-300`:*
```cpp
bitmapText    = game1->getContentProperty().Load<Texture2D>(iconPrefix + "text");
bitmapButton  = game1->getContentProperty().Load<Texture2D>(iconPrefix + "button");
bitmapJauge   = game1->getContentProperty().Load<Texture2D>(iconPrefix + "jauge");
bitmapBlupi   = game1->getContentProperty().Load<Texture2D>(iconPrefix + "blupi");
bitmapBlupi1  = game1->getContentProperty().Load<Texture2D>(iconPrefix + "blupi1");
bitmapObject  = game1->getContentProperty().Load<Texture2D>(iconPrefix + "object-m");
bitmapElement = game1->getContentProperty().Load<Texture2D>(iconPrefix + "element");
bitmapExplo   = game1->getContentProperty().Load<Texture2D>(iconPrefix + "explo");
bitmapPad     = game1->getContentProperty().Load<Texture2D>(iconPrefix + "pad");

bitmapSpeedyBlupi = game1->getContentProperty().Load<Texture2D>(backgroundPrefix + "speedyblupi");
bitmapBlupiYoupie = game1->getContentProperty().Load<Texture2D>(backgroundPrefix + "blupiyoupie");
bitmapGear        = game1->getContentProperty().Load<Texture2D>(backgroundPrefix + "gear");
```

`bitmapBackground` is conspicuously absent from this list — it is loaded separately and repeatedly,
by `BackgroundCache()`, whenever the current level's region changes ([Chapter 34](ch34-backgrounds-and-level-art.md)
covers this in depth):

*From `Pixmap.cpp:321-333`:*
```cpp
void Pixmap::BackgroundCache(const string& name)
{
    std::string backgroundPrefix;
    switch (Config::RESOLUTION_SCALE)
    {
    case 4:  backgroundPrefix = "backgrounds4x/"; break;
    case 2:  backgroundPrefix = "backgrounds2x/"; break;
    default: backgroundPrefix = "backgrounds/";   break;
    }
    bitmapBackground = game1->getContentProperty().Load<Texture2D>(backgroundPrefix + name);
}
```

`GetBitmap()` is the private lookup that every draw method uses to turn a `PixmapChannel` into the
matching texture pointer — a plain `switch` with one case per channel, returning `nullptr` for
anything unmapped (`Pixmap.cpp:745-780`). Every draw method checks that pointer before using it,
so an invalid or not-yet-loaded channel fails silently (or logs an error) rather than crashing.

## `DrawIcon`: the workhorse

`DrawIcon()` is the single method through which the overwhelming majority of sprites in this game
reach the screen — Blupi, every moving object, every tile, every explosion, every button. Its
two-argument-list overload set collapses to one real implementation:

*From `Pixmap.cpp:499-507`:*
```cpp
void Pixmap::DrawIcon(PixmapChannel channel, intcs icon, TinyRect rect, double opacity, bool useHotSpot)
{
    if (!spriteBatch)
    {
        CNA::Logger::Error("Pixmap::DrawIcon called before LoadContent()");
        return;
    }
    DrawIcon(channel, icon, rect, opacity, 0.0, useHotSpot);
}
```

The five-argument version does the real work: resolve which atlas and grid parameters the channel
uses, compute a source rectangle and a destination rectangle, apply rotation if requested, and
issue exactly one `SpriteBatch::Draw()` call. `icon == -1` is a deliberate, universally-honored
sentinel for "draw nothing" — checked once, up front:

*From `Pixmap.cpp:509-539` (abridged):*
```cpp
void Pixmap::DrawIcon(PixmapChannel channel, intcs icon, TinyRect rect, double opacity, double rotationDeg, bool useHotSpot)
{
    if (!spriteBatch) { /* log and return */ }
    if (icon == -1)
    {
        return;
    }
    // touch-button suppression for non-Android platforms without a touchscreen ...
    const Texture2D* bitmap = GetBitmap(channel);
    if (bitmap == nullptr)
    {
        return;
    }
    // ... resolve srcGridX/Y, srcIconWidth/Height, srcGap, dstIconWidth/Height
    //     from a switch(channel) — see Chapter 29 for the full table.
}
```

This `icon == -1` convention is exactly why `Decor::Build()`'s tile-drawing pass (Chapter 16) can
freely skip empty `m_decor[][]` cells by simply never special-casing them — an empty cell already
stores `-1`, and the very same `-1` naturally becomes a no-op the instant it reaches `DrawIcon()`.
It is the same reason `Tables::table_blupi` entries and every other icon-index table in the game
can use `-1` as a "blank frame" marker (Chapter 30) without any table-side special handling —
`DrawIcon()` is the one place that convention has to be honored, and it is honored unconditionally.

One more suppression rule lives in this method and nowhere else: on non-Android platforms, when
`Config::TOUCH_BUTTONS_SHOWN_ONLY_IF_TOUCHSCREEN_IS_AVAILABLE` is set and no touch device is
detected, a fixed list of gameplay `Pad`-channel icon numbers (`{0, 1, 2, 3, 30, 12, 23}`) is
silently skipped — the on-screen virtual joystick/buttons that make sense on a phone are hidden on
a desktop with a mouse and keyboard, at the exact point where they would otherwise be drawn, rather
than by not calling `DrawInputButton()` in the first place.

After the grid lookup, two further private helpers do the coordinate math — `GetSrcRectangle()`
(Chapter 29's subject) and `GetDstRectangle()` (below) — and the method finishes by handing the
resulting rectangles straight to `SpriteBatch::Draw()`:

*From `Pixmap.cpp:659-680` (abridged):*
```cpp
if (srcGridX != 0)
{
    Rectangle srcRectangle = GetSrcRectangle(*bitmap, srcGridX, srcGridY, srcIconWidth, srcIconHeight, srcGap, icon);
    Rectangle rectangle = GetDstRectangle(rect, dstIconWidth, dstIconHeight, useHotSpot);
    float rotationRad = 0.0f;
    if (rotationDeg != 0.0)
    {
        rotationRad = static_cast<float>(Misc::DegToRad(rotationDeg));
        rectangle = Misc::RotateAdjust(rectangle, rotationRad);
    }
    if (!batch_started_) spriteBatch->Begin(/* BackToFront, AlphaBlend */);
    spriteBatch->Draw(*bitmap, rectangle, srcRectangle,
                      Color::FromNonPremultiplied(255, 255, 255, static_cast<intcs>(255.0 * opacity)),
                      rotationRad, origin, effect, 0.0f);
    if (!batch_started_) spriteBatch->End();
}
```

The color argument is always pure white with an alpha derived from `opacity` — this codebase never
tints a sprite; opacity/fading is the *only* per-draw color effect ever used, applied via
`Color::FromNonPremultiplied`'s alpha channel.

## `GetDstRectangle`: zoom and hotspot math, verified

`GetDstRectangle()` is where a logical game-space destination rectangle becomes actual physical
screen pixels — and it is the one place in `Pixmap` where the two independent zoom factors from
earlier in this chapter (`zoom`, `hotSpotZoom`) compose:

*From `Pixmap.cpp:699-743`:*
```cpp
Microsoft::Xna::Framework::Rectangle Pixmap::GetDstRectangle(TinyRect rect, intcs iconWidth, intcs iconHeight,
                                                             bool useHotSpot)
{
    intcs finalWidth = ((rect.getWidthProperty() == 0) ? iconWidth : rect.getWidthProperty());
    intcs finalHeight = ((rect.getHeightProperty() == 0) ? iconHeight : rect.getHeightProperty());
    intcs scaledLeftX = (intcs)((double)rect.Left * zoom);
    intcs scaledTopY = (intcs)((double)rect.Top * zoom);
    intcs scaledRightX = (intcs)((double)scaledLeftX + (double)finalWidth * zoom);
    intcs scaledBottomY = (intcs)((double)scaledTopY + (double)finalHeight * zoom);
    if (useHotSpot && hotSpotZoom > 1.0)
    {
        scaledLeftX -= (intcs)hotSpotX;    scaledTopY -= (intcs)hotSpotY;
        scaledRightX -= (intcs)hotSpotX;   scaledBottomY -= (intcs)hotSpotY;
        scaledLeftX = (intcs)((double)scaledLeftX * hotSpotZoom);
        scaledTopY = (intcs)((double)scaledTopY * hotSpotZoom);
        scaledRightX = (intcs)((double)scaledRightX * hotSpotZoom);
        scaledBottomY = (intcs)((double)scaledBottomY * hotSpotZoom);
        scaledLeftX += (intcs)hotSpotX;    scaledTopY += (intcs)hotSpotY;
        scaledRightX += (intcs)hotSpotX;   scaledBottomY += (intcs)hotSpotY;
    }
#ifdef MODERN
    else if (useHotSpot && hotSpotZoom > 0.0 && hotSpotZoom < 1.0) { /* identical zoom-out branch */ }
#endif
    return Microsoft::Xna::Framework::Rectangle(scaledLeftX, scaledTopY, scaledRightX - scaledLeftX,
                                                scaledBottomY - scaledTopY);
}
```

Reading this precisely (rather than paraphrasing "it applies zoom and a hotspot transform"), the
computation is a strict two-stage pipeline:

1. **Natural size resolution.** A caller passing a zero-sized `TinyRect` (width/height both `0`) is
   asking for the icon's *natural* size — `iconWidth`/`iconHeight`, the `dstIconWidth`/`dstIconHeight`
   values `DrawIcon()`'s channel `switch` already resolved (Chapter 29). A non-zero rectangle
   overrides that with an explicit destination size instead. This is why so many call sites in
   `Decor.cpp` construct a `TinyRect` from nothing but a `TinyPoint` (`TinyRect{pos}` sets only the
   top-left corner, leaving width/height at their default `0`) — they are deliberately asking for
   "draw this icon at its native size here," not specifying a size at all.
2. **Viewport zoom**, applied unconditionally to every corner: `Left`/`Top` are scaled by `zoom`
   directly; `Right`/`Bottom` are derived from the *already-scaled* top-left plus the *separately
   zoom-scaled* width/height — not simply `(Left + width) * zoom`, though the two are numerically
   equivalent here since both terms share the same `zoom` factor.
3. **Hotspot zoom**, applied only when `useHotSpot` is true *and* the current `hotSpotZoom` is
   strictly greater than `1.0` (a real in-game zoom-in) — or, under a `MODERN`-only branch, strictly
   between `0.0` and `1.0` (a zoom-*out*, gated behind the `MODERN` build define discussed in
   [Chapter 10](../part02-building-and-running/ch10-config-legacy-vs-modern.md), since the original
   LEGACY game never let the camera zoom out). The transform is a textbook "translate to
   hotspot-relative space, scale, translate back" pivot scale, applied identically to all four
   corners of the already-zoom-scaled rectangle. A `hotSpotZoom` of exactly `1.0` — the default —
   takes neither branch, so `useHotSpot = true` is harmless when no camera zoom is active; the
   hotspot machinery only ever does something once `SetHotSpot()` has actually been called with a
   non-unity value.

The practical effect: every sprite in the game passes through exactly one rectangle-scaling
pipeline, whether it is a UI button (`useHotSpot = false`, always drawn at 1:1 viewport scale) or a
gameplay sprite (`useHotSpot = true` via `QuickIcon()`, subject to the camera-zoom cheat).

## `DrawPart`, `DrawBackground`, and `DrawChar`: the other draw paths

Not everything goes through the icon-grid machinery. `DrawPart()` draws an arbitrary rectangular
sub-region of a texture at a destination position, bypassing the atlas grid entirely — this is how
`Decor::Build()` blits whole 640×480 panorama panels ([Chapter 34](ch34-backgrounds-and-level-art.md))
and how `Jauge`/`Slider` ([Chapters 36](ch36-jauge-hud-gauges.md) and [37](ch37-slider-ui-control.md))
draw hand-picked rectangles out of `jauge.png` that don't correspond to any uniform grid cell at
all:

*From `Pixmap.cpp:453-497` (abridged):*
```cpp
bool Pixmap::DrawPart(PixmapChannel channel, TinyPoint dest, TinyRect rect, double zoom)
{
    const Texture2D* bitmap = GetBitmap(channel);
    if (bitmap == nullptr) { return false; }
    if (channel == PixmapChannel::Jauge)
    {
        dest.X = static_cast<intcs>(static_cast<double>(dest.X) + originX);
        dest.Y = static_cast<intcs>(static_cast<double>(dest.Y) + originY);
    }
    TinyRect scaledRect = ScaleSourceRect(rect);  // multiplies by Config::RESOLUTION_SCALE
    Rectangle value = Rectangle(scaledRect.Left, scaledRect.Top, scaledRect.getWidthProperty(), scaledRect.getHeightProperty());
    Rectangle destinationRectangle = Rectangle(
        dest.X, dest.Y,
        static_cast<intcs>(static_cast<double>(rect.getWidthProperty()) * zoom),
        static_cast<intcs>(static_cast<double>(rect.getHeightProperty()) * zoom)
    );
    // Begin/Draw/End, respecting batch_started_
}
```

Two things stand out: `DrawPart()` never applies the viewport `zoom` member at all — its `zoom`
parameter is a caller-supplied, independent scale factor (used by `Jauge`/`Slider` to draw at 2x,
for instance), and `Jauge` is the *only* channel singled out for an origin offset inside `DrawPart()`
itself, because every other caller of `DrawPart()` already computes screen-space coordinates
manually before calling it.

`DrawBackground()` is a distinct, simpler full-screen blit used for static single-image UI screens
(the title/init/pause/setup/win/lost screens — Chapter 34 catalogs the actual asset files):

*From `Pixmap.cpp:377-414` (abridged):*
```cpp
void Pixmap::DrawBackground()
{
    // ... resolves bitmap for PixmapChannel::Background ...
    Rectangle srcRectangle = GetSrcRectangle(bitmap, 10, 10, 10, 10, 0, 0);
    Rectangle destinationRectangle = Rectangle(0, 0, (intcs)screenWidth, (intcs)screenHeight);
    spriteBatch->Draw(bitmap, destinationRectangle, srcRectangle, Color::White);   // stretch-fill pass
    TinyRect rect{0, 640, 0, 480};
    DrawPart(PixmapChannel::Background, {(intcs)originX, (intcs)originY}, rect);  // crisp 1:1 pass
}
```

Two draws happen here, not one: a coarse stretch of a 10×10-pixel sample across the *entire*
physical screen first (a cheap, blurry full-bleed fill so there is no visible edge/letterbox gap
even before the second draw lands), followed by the crisp, correctly-proportioned 640×480 image at
native resolution positioned at the letterbox-corrected origin. `Decor::Build()`'s own gameplay
panorama rendering ([Chapter 34](ch34-backgrounds-and-level-art.md)) does **not** call
`DrawBackground()` at all — it calls `DrawPart(PixmapChannel::Background, ...)` directly, several
times per frame, to build its own repeating parallax-scrolled tiling. `DrawBackground()` is reserved
for the single-panel menu/loading screens that need no scrolling.

`DrawChar()` is the thinnest of the specialized wrappers, converting a font-glyph draw into an
ordinary `DrawIcon(PixmapChannel::Text, ...)` call after computing a `size`-scaled destination
square:

*From `Pixmap.cpp:416-426`:*
```cpp
void Pixmap::DrawChar(intcs rank, TinyPoint pos, double size)
{
    pos.X = static_cast<intcs>(static_cast<double>(pos.X) + originX);
    pos.Y = static_cast<intcs>(static_cast<double>(pos.Y) + originY);
    TinyRect tinyRect{pos.X, pos.X + (intcs)(32.0 * size), pos.Y, pos.Y + (intcs)(32.0 * size)};
    DrawIcon(PixmapChannel::Text, rank, tinyRect, 1.0, false);
}
```
[Chapter 35](ch35-text-rendering.md) covers the `Text` class that calls this once per glyph.

`HudIcon()` and `QuickIcon()` are the two remaining thin wrappers worth naming precisely, since the
whole rest of the codebase calls these two far more often than `DrawIcon()` directly: `HudIcon()`
translates by `(originX, originY)` and calls `DrawIcon(..., useHotSpot=false)` — for UI elements
that must never respond to the in-game camera zoom — while `QuickIcon()` does *not* translate by
origin (it is already meant to be called with game-space coordinates that `GetDstRectangle()`'s own
zoom math will place correctly) and always passes `useHotSpot=true` — the default path for ordinary
gameplay sprites (`Pixmap.cpp:428-446`).

## Sprite batching: `BeginBatch()`/`EndBatch()` and a real, hard-coded quirk

`IPixmap`'s `BeginBatch()`/`EndBatch()` pair exists to let a whole frame's worth of draw calls share
a single `SpriteBatch::Begin()`/`End()` pair instead of paying that cost once per sprite —
[Chapter 4](../part02-building-and-running/ch04-build-overview.md) covers the `CNA_SPRITE_BATCHING_ENABLED`
CMake `option()` that gates this feature at the build-system level (it defaults `OFF`), so this
chapter only covers what the flag changes inside `Pixmap` itself, not the CMake mechanics.

*From `Pixmap.cpp:346-375`:*
```cpp
void Pixmap::BeginBatch()
{
    UpdateGeometry();  // see note below — this is the real per-frame geometry-refresh hook
#ifdef CNA_SPRITE_BATCHING_ENABLED
    if (!spriteBatch || batch_started_) return;
    spriteBatch->Begin(SpriteSortMode::BackToFront, BlendState::AlphaBlend);
    batch_started_ = true;
#endif
}

void Pixmap::EndBatch()
{
#ifdef CNA_SPRITE_BATCHING_ENABLED
    if (!spriteBatch || !batch_started_) return;
    spriteBatch->End();
    batch_started_ = false;
#endif
}
```

Every draw method checks the shared `batch_started_` flag and, when it is `true`, skips its own
`Begin()`/`End()` pair entirely, trusting the outer batch opened by `BeginBatch()` to be flushed
later by `EndBatch()`. When the flag is `false` (batching disabled, or no batch currently open),
every draw call reverts to the original one-`Begin()`/`End()`-per-sprite behavior — functionally
identical to the pre-batching code, just slower.

Two facts here are worth stating precisely rather than glossing over, because both are directly
visible in the source and neither is what a reader might assume from the CMake option's description
alone:

**First**, `Pixmap.cpp` unconditionally re-defines the macro at file scope, immediately after its
`#include`s, regardless of what the CMake `option()` decided:

*From `Pixmap.cpp:63`:*
```cpp
#define CNA_SPRITE_BATCHING_ENABLED
```

This means that, as shipped, `Pixmap.cpp`'s own `#ifdef CNA_SPRITE_BATCHING_ENABLED` blocks are
*always* compiled in for this translation unit — independent of whether the CMake option that
controls `target_compile_definitions()` is `ON` or `OFF` for the rest of the target. The class's own
doc comment already flags this precisely as intentional, not an oversight: "When
`CNA_SPRITE_BATCHING_ENABLED` is defined (currently hard-coded in the .cpp) ..." (`Pixmap.hpp:19`).
The CMake option genuinely exists and genuinely controls `target_compile_definitions()`
(Chapter 4), but for this specific file it is currently redundant with a hard-coded `#define` that
overrides it either way — worth knowing if a reader builds with `-DCNA_SPRITE_BATCHING_ENABLED=OFF`
expecting the original per-sprite behavior and finds the batched path still active in `Pixmap.cpp`.

**Second**, `BeginBatch()` carries a substantial inline comment explaining a real bug fix that
piggybacks on this method, unrelated to batching itself:

*From `Pixmap.cpp:348-358`:*
```cpp
// UpdateGeometry() was previously only ever called once, from LoadContent() at startup --
// its own doc comment already said "re-call whenever the window is resized", but nothing
// did. zoom/originX/originY then stayed frozen at the startup viewport size forever, so
// any later resize (most visibly: toggling fullscreen) left every sprite drawn at the
// stale scale/offset while DrawBackground()'s own full-screen stretch (which re-queries
// the live viewport every call already) correctly filled the new size -- the game content
// pinned to a small stale corner against an otherwise-blank background. BeginBatch(), not
// Start(), is the real once-per-frame hook: Game1::Draw() calls pixmap->BeginBatch() every
// frame unconditionally, but nothing anywhere ever calls IPixmap::Start() despite its own
// doc comment claiming it's part of the per-frame contract. Placed outside the
// CNA_SPRITE_BATCHING_ENABLED guard below so it runs regardless of that flag.
UpdateGeometry();
```

This is a genuinely interesting piece of engineering history preserved directly in the comment: the
interface's own documentation describes a `Start()`/`Finish()` per-frame contract
(`IPixmap.hpp:108-130`) that `Game1::Draw()` (Chapter 12) never actually follows — `Start()` is
never called from anywhere in the codebase, so `UpdateGeometry()`'s "re-call whenever the window is
resized" note went unfulfilled until whoever wrote this comment noticed the bug (sprites frozen at
launch-time viewport dimensions after any resize) and fixed it by placing the call at the start of
`BeginBatch()` instead — the method that genuinely *is* called once per frame unconditionally,
regardless of whether sprite batching itself is even enabled. The `UpdateGeometry()` call sits
deliberately outside the `#ifdef CNA_SPRITE_BATCHING_ENABLED` block for exactly that reason: it must
run every frame no matter what the batching flag is doing.

## Who calls what: a caller map

Pulling together every citation in this chapter and its Part V neighbors into one table gives a
useful orientation for the rest of Part V — which caller uses which `Pixmap` entry point, and where
that caller's own chapter lives:

| Caller | Method(s) used | Covered in |
|---|---|---|
| `Decor::Build()` | `QuickIcon()`, `DrawPart()` (panorama tiling), `DrawIcon()` (via `QuickIcon`) | [Chapter 15](../part04-decor-simulation/ch15-decor-overview.md), [Chapter 34](ch34-backgrounds-and-level-art.md) |
| `Decor::BlupiSearchIcon()`/`BlupiStep()` | (resolves `m_blupiIcon`, drawn later by `Build()`) | [Chapter 18](../part04-decor-simulation/ch18-blupi-actions-and-animation.md) |
| `Decor::MoveObjectStepIcon()` | (resolves each `MoveObject`'s icon, drawn later by `Build()`) | [Chapter 32](ch32-creature-and-object-animation-catalog.md) |
| `Pixmap::DrawInputButton()` | `DrawIcon(Pad, ...)`, `Text::DrawTextCenter()` | This chapter, [Chapter 35](ch35-text-rendering.md) |
| `Jauge::Draw()` | `DrawPart(Jauge, ...)` | [Chapter 36](ch36-jauge-hud-gauges.md) |
| `Slider::Draw()` | `DrawPart(Jauge, ...)`, `DrawIcon(Pad/Element, ...)` | [Chapter 37](ch37-slider-ui-control.md) |
| `Text::DrawCharSingle()` | `IPixmap::DrawChar()` -> `DrawIcon(Text, ...)` | [Chapter 35](ch35-text-rendering.md) |
| `Game1.cpp` (title/menu/victory phases) | `DrawIcon(SpeedyBlupiBackground/BlupiYoupieBackground/GearBackground, 0, ...)` | [Chapter 34](ch34-backgrounds-and-level-art.md) |
| `Game1::Draw()` | `BeginBatch()`/`EndBatch()` (once per frame, unconditionally) | This chapter |

No caller in the codebase ever constructs a `Microsoft::Xna::Framework::Rectangle` or touches a
`Texture2D` directly outside of `Pixmap` itself — every one of these callers speaks exclusively in
`TinyPoint`/`TinyRect`/`PixmapChannel`/icon-index terms, which is precisely the abstraction boundary
`IPixmap` exists to enforce (this chapter's opening section).

## What this class produces: real screenshots

Everything in this chapter is invisible machinery until a frame actually reaches the screen. Two
real, unmodified screenshots exist in this book's image library, captured from an actually-built,
actually-running copy of the game (see `tools/SCREENSHOT_ATTEMPT.md` for the full capture story) —
they are the end-to-end proof that this chapter's `DrawIcon()`/`DrawPart()`/`GetDstRectangle()`
pipeline is what ultimately puts these exact pixels on screen:

![Title/menu screen, real captured screenshot](../images/screenshot-title-menu.png)

*Real screenshot, `Texture2D::SaveAsPng` dump from an actually-built, actually-running copy of the
game — this is `Pixmap::DrawBackground()`'s stretch-then-crisp two-pass blit (this chapter) drawing
one of the menu-screen backgrounds cataloged in [Chapter 34](ch34-backgrounds-and-level-art.md).*

![Gameplay, level 1, real captured screenshot](../images/screenshot-gameplay-level1.png)

*Real screenshot, `Texture2D::SaveAsPng` dump from an actually-built, actually-running copy of the
game — every sprite visible here (Blupi, tiles, HUD gauges) reached the screen through
`Pixmap::DrawIcon()`/`QuickIcon()`/`DrawPart()` exactly as described in this chapter; the tile
layer's atlas slicing is [Chapter 29](ch29-sprite-atlas-system.md)'s subject, and Blupi's own
animation-frame resolution is [Chapter 30](ch30-tables-animation-and-movement-data.md)'s.*

## See also

- [Chapter 4 — Build Overview (CMake)](../part02-building-and-running/ch04-build-overview.md)
- [Chapter 10 — Config: LEGACY vs MODERN](../part02-building-and-running/ch10-config-legacy-vs-modern.md)
- [Chapter 12 — Game1: the State Machine](../part03-architecture/ch12-game1-state-machine.md)
- [Chapter 14 — The XNA API via CNA](../part03-architecture/ch14-xna-api-via-cna.md)
- [Chapter 16 — The Tile Map](../part04-decor-simulation/ch16-tile-map.md)
- [Chapter 18 — Blupi Actions and Animation](../part04-decor-simulation/ch18-blupi-actions-and-animation.md)
- [Chapter 29 — The Sprite Atlas System](ch29-sprite-atlas-system.md)
- [Chapter 34 — Backgrounds and Level Art](ch34-backgrounds-and-level-art.md)
- [Chapter 35 — Text Rendering](ch35-text-rendering.md)
- [Chapter 36 — Jauge: HUD Gauges](ch36-jauge-hud-gauges.md)
- [Chapter 37 — Slider: UI Control](ch37-slider-ui-control.md)
- [Appendix G — Screenshot and Visual Gallery](../appendices/appendix-g-screenshot-gallery.md)
