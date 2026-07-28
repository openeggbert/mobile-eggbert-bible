# Chapter 54: RAM Memory Analysis

`mobile-eggbert`'s repository includes `RAM.md`, a short, standalone static-analysis document
titled (in the original Czech) *"Analýza zbytečného vytváření objektů v projektu mobile-eggbert"* —
"Analysis of unnecessary object creation in the mobile-eggbert project." It is a code-reading
exercise, not a profiling report: no allocator, sampler, or memory tool was run against a live
build. Every finding in it comes from reading `Decor.cpp`, `Game1.cpp`, and `Pixmap.cpp` and
reasoning about what each piece of code must be doing on the stack and heap. This chapter presents
that document's findings in English, faithfully preserving which claims are simple, verifiable
facts about the code (a struct has these fields, this loop runs every frame) and which are
estimates or recommendations that were never measured against a running process.

Where this chapter's own reading of the current checkout turns up something `RAM.md` didn't
capture — most notably, that the source file has grown since `RAM.md` was written, so several of
its line-number citations point a few hundred lines short of where the same code now lives — that
is noted explicitly rather than silently corrected.

## Finding 1: `ByeByeDraw` copies every debris object, every frame

`RAM.md`'s first finding concerns the render loop for what the code calls "ByeBye objects" — the
small debris/particle fragments spawned when something is destroyed (an exploding crate, a
defeated enemy). `RAM.md` describes the loop as iterating by value instead of by reference:

*From `RAM.md`:*

> **File:** `src/WindowsPhoneSpeedyBlupi/Decor.cpp`, line 9252
>
> ```cpp
> // PROBLEM: copies every ByeByeObject instead of using a reference
> for (ByeByeObject byeByeObject : byeByeObjects)
> {
>     TinyPoint tinyPoint;
>     tinyPoint.X = m_drawBounds.Left + (int)byeByeObject.posX - posDecor.X;
>     ...
> }
> ```

In the checkout this chapter was written against, the equivalent code is real and unchanged in
substance, but now sits at `Decor.cpp:10131` (`RAM.md`'s file has since grown by roughly 870-900
lines, shifting every later citation down by a similar amount — see the note under Finding 4):

*From `Decor.cpp:10129-10139` (`Decor::ByeByeDraw`):*

```cpp
void Decor::ByeByeDraw(TinyPoint posDecor)
{
    for (ByeByeObject byeByeObject : byeByeObjects)
    {
        TinyPoint tinyPoint;
        tinyPoint.X = m_drawBounds.Left + (int)byeByeObject.posX - posDecor.X;
        tinyPoint.Y = m_drawBounds.Top + (int)byeByeObject.posY - posDecor.Y;
        TinyPoint pos = tinyPoint;
        m_pixmap->QuickIcon(byeByeObject.channel, byeByeObject.icon, pos, 1.0, byeByeObject.rotation);
    }
}
```

`RAM.md` characterizes `ByeByeObject` as a class with 9 members, mostly `double` (8 bytes each) —
roughly 72 bytes per instance — and notes that `Decor::Draw` calls this loop every single frame,
so the range-`for` above copies every live debris fragment's full ~72 bytes on every draw call
rather than binding a `const ByeByeObject&`. `RAM.md`'s suggested fix is the minimal one-word
change:

```cpp
// Correct — const reference, no copy
for (const ByeByeObject& byeByeObject : byeByeObjects)
```

`RAM.md` marks this finding's severity as **Medium** (⚠️). No benchmark accompanies this
conclusion; it rests entirely on "this copies a ~72-byte struct once per live fragment, once per
frame," which is true by inspection of the type and the loop, but the actual performance impact
(how many `ByeByeObject`s are typically alive at once, whether 72 bytes of stack-copy overhead per
iteration is measurable against everything else `Decor::Draw` does per frame) was not measured.

## Finding 2: `ByeByeAdd` constructs the same object twice

*From `RAM.md`:*

> **File:** `src/WindowsPhoneSpeedyBlupi/Decor.cpp`, lines 9187–9206
>
> ```cpp
> void Decor::ByeByeAdd(...)
> {
>     ByeByeObject byeByeObject;      // construction 1
>     byeByeObject.channel = channel;
>     ...
>     ByeByeObject byeByeObject2 = byeByeObject;  // copy-construction 2 (unnecessary!)
>     byeByeObject2.speedX = ...;
>     byeByeObjects.push_back(byeByeObject2);      // copy 3 (a move would work here)
> }
> ```

The current code (`Decor.cpp:10056-10078`, again shifted from `RAM.md`'s cited `9187-9206`) matches
this description exactly:

*From `Decor.cpp:10056-10078` (`Decor::ByeByeAdd`):*

```cpp
void Decor::ByeByeAdd(PixmapChannel channel, int icon, TinyPoint pos, double rotationSpeed, double animationSpeed)
{
    ByeByeObject byeByeObject;
    byeByeObject.channel = channel;
    byeByeObject.icon = icon;
    byeByeObject.posX = pos.X;
    byeByeObject.posY = pos.Y;
    byeByeObject.rotation = 0.0;
    byeByeObject.phase = 0.0;
    byeByeObject.rotationSpeed = rotationSpeed;
    byeByeObject.animationSpeed = animationSpeed;
    ByeByeObject byeByeObject2 = byeByeObject;
    int num = m_random.get()->Next(0, 10);
    if (m_random.get()->Next(0, 1000) % 2 == 0)
    {
        byeByeObject2.speedX = num + 10;
    }
    else
    {
        byeByeObject2.speedX = -(num + 10);
    }
    byeByeObjects.push_back(byeByeObject2);
}
```

The object is genuinely built once (`byeByeObject`), copy-constructed a second time
(`byeByeObject2`) purely so `speedX` can be set on the copy rather than the original, and then
copied a third time into the vector by `push_back`. `RAM.md` rates this finding **Low** (🔵) — it
is a real, verifiable inefficiency (`ByeByeAdd` is only called when something is destroyed, not
every frame, unlike Finding 1), and `RAM.md`'s own severity ranking reflects that lower call
frequency rather than downplaying the finding's accuracy.

## Finding 3: `ByeByeStep` erases from the middle of a vector

*From `RAM.md`:*

> **File:** `src/WindowsPhoneSpeedyBlupi/Decor.cpp`, line 9241
>
> ```cpp
> while (num < byeByeObjects.size())
> {
>     ...
>     if (byeByeObject.phase > 30.0)
>     {
>         // This shifts every remaining element left by one — O(n) per erase!
>         byeByeObjects.erase(byeByeObjects.begin() + num);
>     }
>     ...
> }
> ```

The real function, now at `Decor.cpp:10087-10127`, confirms the shape of this loop (`RAM.md`'s
description simplifies the surrounding ballistic-motion math, which is documented in the function's
own header comment, but the erase-in-a-while-loop structure it flags is exactly as described):

*From `Decor.cpp:10087-10127` (`Decor::ByeByeStep`, abridged to the relevant control flow):*

```cpp
void Decor::ByeByeStep()
{
    int num = 0;
    while (num < byeByeObjects.size())
    {
        ByeByeObject& byeByeObject = byeByeObjects[num];
        // ... ballistic-arc position/rotation update ...
        if (byeByeObject.phase > Config::ScaleTime(30))
        {
            byeByeObjects.erase(byeByeObjects.begin() + num);
        }
        else
        {
            num++;
        }
    }
}
```

`RAM.md`'s point stands on inspection: `std::vector::erase()` at an arbitrary position (as opposed
to the last element) is a linear-time operation, because every element after the erased one must be
shifted down by one slot. With up to 100 live `ByeByeObject`s (an assumed working-set size, not a
value read from a hard limit in the code — `byeByeObjects` is an unbounded `std::vector`, not a
fixed-size array like `m_moveObject`), `RAM.md` estimates each erase could move up to 99 elements.
Its suggested alternative is the standard erase-remove idiom, or marking expired fragments dead and
batch-removing them once per frame instead of removing one at a time mid-iteration. `RAM.md` rates
this finding **Medium** (⚠️) as well.

## Finding 4: `MoveObjectSort`'s bubble sort with manual struct copying

This is the finding `RAM.md` rates most severely, and the one where the line-number drift between
`RAM.md` and the current checkout is largest:

*From `RAM.md`:*

> **File:** `src/WindowsPhoneSpeedyBlupi/Decor.cpp`, lines 9074–9108
>
> ```cpp
> void Decor::MoveObjectSort()
> {
>     MoveObject dst;
>     ...
>     do {
>         flag = false;
>         for (int i = 0; i < num - 1; i++)
>         {
>             if (SortGetType(...) > SortGetType(...))
>             {
>                 MoveObjectCopy(dst, m_moveObject[i]);       // ~67-byte copy
>                 MoveObjectCopy(m_moveObject[i], m_moveObject[i + 1]);
>                 MoveObjectCopy(m_moveObject[i + 1], dst);
>                 flag = true;
>             }
>         }
>     } while (flag);
> }
> ```
>
> `MoveObjectCopy` manually copies every field of the `MoveObject` struct (~67 bytes). A bubble
> sort with `MAXMOVEOBJECT = 200` objects means up to **~40,000 copies** in the worst case (each
> ~67 bytes).

In this checkout, `Decor::MoveObjectSort` is at `Decor.cpp:9933-9970` — roughly 860 lines earlier
than the rest of this chapter's other citations relative to `RAM.md`'s own numbering, which is a
useful reminder that "the file has grown since this doc was written" doesn't shift every citation
by a uniform, predictable amount; each function's position depends on how much code was added
before it specifically. The real function matches `RAM.md`'s description exactly, including the
classic swap-via-three-copies bubble-sort body:

*From `Decor.cpp:9933-9970` (`Decor::MoveObjectSort`):*

```cpp
void Decor::MoveObjectSort()
{
    MoveObject dst;
    int num = 0;
    for (int i = 0; i < MAXMOVEOBJECT; i++)
    {
        if (m_moveObject[i].type != ObjectType::ObjectType0)
        {
            MoveObjectCopy(m_moveObject[num++], m_moveObject[i]);
        }
    }
    for (int i = num; i < MAXMOVEOBJECT; i++)
    {
        m_moveObject[i].type = ObjectType::ObjectType0;
    }
    if (num <= 1)
    {
        return;
    }
    bool flag;
    do
    {
        flag = false;
        for (int i = 0; i < num - 1; i++)
        {
            if (SortGetType(m_moveObject[i].type) > SortGetType(m_moveObject[i + 1].type))
            {
                MoveObjectCopy(dst, m_moveObject[i]);
                MoveObjectCopy(m_moveObject[i], m_moveObject[i + 1]);
                MoveObjectCopy(m_moveObject[i + 1], dst);
                flag = true;
            }
        }
    }
    while (flag);
    UpdateCaisse();
    m_nbLinkCaisse = 0;
}
```

`MAXMOVEOBJECT` is confirmed as a real, current constant:

*From `Decor.hpp:185`:*

```cpp
static constexpr intcs MAXMOVEOBJECT = 200;
```

`RAM.md`'s worst-case arithmetic (`O(n²)` bubble sort over up to 200 elements, three manual field-by-
field copies per swap) is sound as a description of algorithmic complexity — a true statement about
what the code *can* do in the worst case, not a measurement of what it typically does. Whether
`MoveObjectSort` is called often enough, and with a typical `num` close enough to 200, for this to
be a real, felt performance cost during actual gameplay was not measured; `RAM.md` presents it as
the most severe finding on structural grounds (an `O(n²)` sort with manual copying, versus
`std::sort`'s typical `O(n log n)` with move semantics), not because a profiler pointed at it.
`RAM.md`'s suggested fix is exactly that comparison:

```cpp
// Instead of MoveObjectCopy — use direct assignment:
dst = m_moveObject[i];          // automatic copy of all members
m_moveObject[i] = m_moveObject[i + 1];
m_moveObject[i + 1] = dst;

// Or better still — use std::sort with a lambda:
std::sort(m_moveObject, m_moveObject + num,
    [](const MoveObject& a, const MoveObject& b) {
        return SortGetType(a.type) < SortGetType(b.type);
    });
```

`RAM.md` rates this finding **High** (🔴), the only one of the five to receive that rating.

## Finding 5: large fixed-size arrays as `Decor` member fields

The final finding is not about a hot loop at all, but about `Decor`'s own memory footprint as an
object — how much stack (not heap) space one `Decor` instance occupies by virtue of the fixed-size
arrays it declares as direct members:

*From `RAM.md`:*

> **File:** `include/WindowsPhoneSpeedyBlupi/Decor.hpp`
>
> ```cpp
> Cellule m_decor[100][100]{};       // 10,000 × 4 bytes = 40 KB
> Cellule m_bigDecor[100][100]{};    // 10,000 × 4 bytes = 40 KB
> intcs m_balleTraj[1300]{};         // 1,300 × 4 = 5.2 KB
> intcs m_moveTraj[1300]{};          // 1,300 × 4 = 5.2 KB
> MoveObject m_moveObject[200];      // 200 × ~67 = ~13.4 KB
> ```
>
> These arrays sit on the stack of the `Decor` object — roughly **~104 KB** total just for these
> fields. They are static allocations, not dynamic ones, so they are not repeatedly allocated.
> Nevertheless, `InitDecor()` zeroes all of them in a loop (`for 100×100`).

Every array and its declared size checks out against the current header. `Cellule` is a
single-field struct wrapping one `intcs` (a 32-bit integer type, per `intcs`'s definition in
`cna`/`sharp-runtime`), so 4 bytes per cell is correct:

*From `Decor.hpp:113-116` (`Cellule`):*

```cpp
struct Cellule
{
    intcs icon; ///< Tile icon index used for rendering and collision classification.
};
```

*From `Decor.hpp:209-221`:*

```cpp
Cellule m_decor[100][100]{};
...
Cellule m_bigDecor[100][100]{};
...
static constexpr int m_balleTrajLength = 1300;
intcs m_balleTraj[m_balleTrajLength]{};
...
static constexpr int m_moveTrajLength = 1300;
intcs m_moveTraj[m_moveTrajLength]{};
...
MoveObject m_moveObject[MAXMOVEOBJECT];
```

`RAM.md`'s framing here is important and worth restating precisely: this is explicitly *not* a
"memory leak" or "excessive allocation" finding. `RAM.md` calls these **static allocations**,
meaning their size is fixed at compile time and they are allocated exactly once per `Decor`
instance's lifetime (as part of that object's own storage, wherever it lives — stack or heap
depending on how `Decor` itself is instantiated) — not allocated and freed repeatedly during
gameplay the way the `ByeByeObject` vector churn in Findings 1–3 is. The only runtime cost `RAM.md`
attaches to this ~104 KB figure is the zeroing loop in `InitDecor()`, confirmed at
`Decor.cpp:263-279`, which touches every one of the 20,000 `Cellule` slots in `m_decor` and
`m_bigDecor` combined once, at level-load time — not once per frame.

## What `RAM.md` explicitly rules out

The document's closing summary is as important as its five findings, because it draws a line the
analysis deliberately did not cross:

*From `RAM.md`'s summary table and closing paragraph:*

| Location | File | Problem type | Severity |
|---|---|---|---|
| `ByeByeDraw` | `Decor.cpp` | Object copy in a per-frame loop | Medium |
| `ByeByeAdd` | `Decor.cpp` | Unnecessary intermediate copy | Low |
| `ByeByeStep` | `Decor.cpp` | Mid-vector `erase` = O(n) shift | Medium |
| `MoveObjectSort` | `Decor.cpp` | Bubble sort + manual O(n²) copying | High |
| `MoveObjectCopy` | `Decor.cpp` | Manual copy instead of default assignment / `std::swap` | Low |

> No unwanted heap allocation via `new` was found anywhere in the gameplay code — every dynamic
> allocation (`make_shared<Pixmap>`, `make_shared<Sound>`, `make_unique<Random>`,
> `make_unique<SpriteBatch>`) is a one-time initialization at startup, not a repeated allocation.

This chapter independently confirmed all four of those specific allocation call sites are real and
match the "one-time startup initialization" characterization — none of them sits inside a per-frame
or per-object-spawn code path:

*From `Game1.cpp:115-116`:*

```cpp
pixmap(std::make_shared<Pixmap>(this, graphics)),
sound(std::make_shared<Sound>(this, gameData)),
```

*From `Decor.cpp:220`:*

```cpp
m_random = std::make_unique<System::Random>();
```

*From `Pixmap.cpp:255`:*

```cpp
spriteBatch = std::make_unique<Microsoft::Xna::Framework::Graphics::SpriteBatch>(
```

All four appear in construction/setup code, not in `Update()`, `Draw()`, `ByeByeAdd()`, or any of
the other per-frame or per-event paths the five findings above concern themselves with. This
matters for how to weigh the chapter as a whole: `RAM.md` is not describing a project riddled with
allocation bugs. It describes a codebase whose one-time setup allocations look fine, and whose
per-frame hot paths contain a handful of specific, real, but modest inefficiencies — value-copying
patterns inherited from what reads like a fairly literal C#-to-C++ port (`MoveObjectCopy` manually
assigning every field is exactly the kind of code a mechanical or semi-mechanical port from C#
tends to produce, where C#'s reference-type semantics didn't require the original author to think
about copy cost at all) rather than anything approaching a memory leak or unbounded growth.

## How to read this chapter's confidence level

To be explicit about what has and hasn't been established: every code excerpt in this chapter was
verified against the actual current source during the writing of this chapter, including the
several places where `RAM.md`'s own line-number citations have drifted from where the same
functions live today. The *complexity* claims (this loop is `O(n)`, this sort is `O(n²)`, this
struct is approximately this many bytes) are straightforward, verifiable facts about the code as
written. The *severity* ratings and the estimated real-world impact ("~40,000 copies in the worst
case," "Medium," "High") are `RAM.md`'s own judgment calls, arrived at by static reading alone, with
no profiler, benchmark, or `perf`/Valgrind-style measurement backing them. No follow-up document in
this repository revisits `RAM.md`'s findings with actual runtime measurements, so this chapter, like
`RAM.md` itself, presents them as reasoned analysis rather than confirmed, measured performance
problems.

## See also

- [Chapter 15](../part04-decor-simulation/ch15-decor-overview.md) — `Decor`'s overall
  responsibilities and data model, of which the arrays and object pools discussed here are a part.
- [Chapter 19](../part04-decor-simulation/ch19-moving-objects-and-decor-actions.md) — `MoveObject`
  and `DecorAction` in full, including what `MoveObjectSort`'s sort order is actually used for.
- [Chapter 27](../part04-decor-simulation/ch27-decor-hpp-reference-catalog.md) — the full member
  catalog of `Decor.hpp`, including every field mentioned in Finding 5.
- [Chapter 40](../part06-audio/ch40-audio-issue-analysis.md) — a similarly structured static
  analysis document (`AUDIO_ANALYSIS.md`) covering a different subsystem, with the same
  suspected-not-confirmed epistemic discipline this chapter preserves.
