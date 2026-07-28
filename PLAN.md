# Plán knihy Mobile Eggbert Bible

## Rozsah zdrojového kódu (změřeno 2026-07-28)

`mobile-eggbert` (větev `develop`, commit `07e0a67`):

- `include/WindowsPhoneSpeedyBlupi/**/*.hpp`: 34 souborů
- `src/WindowsPhoneSpeedyBlupi/**/*.cpp`: 16 souborů
- Celkem C++ (`.hpp` + `.cpp`) + zbytkové `.cs` stuby: **31 301 řádků**
  - `Decor.cpp` samotný: **11 720 řádků** (přes třetinu celého projektu — jádro herní simulace)
  - `Tables.cpp`: 2 208 řádků, `Decor.hpp`: 2 064 řádků, `InputPad.cpp`: 1 970 řádků,
    `Game1.cpp`: 1 113 řádků
- `worlds/*.txt`: 78 souborů (textový formát úrovní/uložených her)
- `Content/{icons,sounds,backgrounds}`: 93 `.wav`, desítky `.png`
- Existující `.md` dokumentace v repozitáři (vstupní materiál, ne náhrada čtení zdroje):
  `README.md`, `CLAUDE.md`, `ANDROID.md`, `AUDIO_ANALYSIS.md`, `ENUMS.md` (návrh, ne
  implementace!), `RAM.md`, `WINDOWS.md`, `TODO.md`, `DOXYGEN_DOCUMENTATION_PLAN.md`,
  `.Net and XNA used part.md` (prázdný stub), `documentation/Cheat System.md`

## Poctivá poznámka k rozsahu (analogie k `cna-bible/PROGRESS.md`)

Zadání žádá „klidně tisíc stran". `cna-bible` pokrývá **celý** CNA ekosystém (CNA samotné + 5
grafických backendů + sharp-runtime + easy-gl + free-direct + síť/audio/vstup/storage +
cross-platform porting na 4 platformách + přes deset satelitních repozitářů) a i tak, při
důsledném lpění na tom, že každé tvrzení musí být podložené reálným zdrojem, skončila na 233
stranách — ne na požadovaných 4000. `mobile-eggbert` je **jedna hra**, ~31k řádků, ne ekosystém.
Poctivý odhad genuinně unikátního, do hloubky jdoucího obsahu (bez vycpávání opakováním nebo
vymyšlenými pasážemi) je řádově **300–500 stran ekvivalentu** (při ~500 slovech/stránku), rozdělené
do 54 kapitol + 6 příloh napříč 11 částmi — a to je už extrémně podrobné pokrytí jedné hry: každá
třída, každá metoda s netriviální logikou, každý enum, formát souboru úrovně po bajtech, build
pro každou platformu, celá historie migrace C# → C++ → CNA.

Cíl proto je: **maximální upřímná hloubka, ne umělý počet stran.** Tento dokument sleduje skutečný
odhadovaný rozsah v sekci "Stav kapitol" níže a bude upřesňován, jak práce postupuje.

## Metodika

Viz `CLAUDE.md` pro plné nesmlouvatelné zásady. Shrnutí:

1. Každá kapitola je založená na skutečném přečtení odpovídajících `.hpp`/`.cpp`/`.txt`/`.md`
   souborů z `mobile-eggbert` (a případně `cna`, `mobile-eggbert-legacy` pro kontext).
2. Kódové ukázky = reálné úryvky s citací `soubor:řádek`.
3. Žádné fiktivní screenshoty (hru zde nelze spustit a vyfotit).
4. `ENUMS.md` = analytický návrh, nikoli implementovaný kód — musí být takto označen, kdykoliv je
   citován.
5. Commit po menších krocích, push po každém.
6. Kapitoly píšou dílčí agenti (viz session log), ale musí projít kontrolou hlavní relace před
   commitem — namátková kontrola grounding (skutečně cituje reálný kód?) a konzistence stylu.

## Struktura knihy — 54 kapitol + 6 příloh, 11 částí

### Part I — Původ a ekosystém (`part01-puvod-a-ekosystem/`)
1. `ch01-co-je-mobile-eggbert.md` — Co je Mobile Eggbert: historie Speedy Blupi → Windows Phone/XNA
   (2013) → ILSpy dekompilace → MonoGame → C++ → CNA
2. `ch02-ekosystem-openeggbert.md` — Mapa ekosystému OpenEggbert (cna, sharp-runtime,
   mobile-eggbert-core/legacy/libgdx, galaxy-eggbert, vztahy mezi nimi)
3. `ch03-licence-a-puvod.md` — Licence, autorství, provenience (Epsitec SA, LICENSE soubor)

### Part II — Sestavení a spuštění (`part02-sestaveni-a-spusteni/`)
4. `ch04-prehled-sestaveni.md` — CMakeLists.txt do hloubky: cíle, závislosti, submoduly, backendy
5. `ch05-linux-build.md` — Linux nativní build
6. `ch06-windows-a-krizova-kompilace.md` — Windows nativní build a cross-build z Linuxu (MinGW-w64)
7. `ch07-direct3d-wine-proton.md` — D3D11/D3D12 backendy přes Wine/Proton na Linuxu
8. `ch08-web-emscripten-build.md` — Web/Emscripten build, virtuální FS, IndexedDB save
9. `ch09-android-build.md` — Android build (Gradle, NDK, ANDROID.md do hloubky)
10. `ch10-config-legacy-vs-modern.md` — `Config.hpp`: LEGACY vs MODERN režim, časování, rozlišení

### Part III — Architektura (`part03-architektura/`)
11. `ch11-program-a-vstupni-bod.md` — `Program.cpp`, vstupní bod aplikace
12. `ch12-game1-stavovy-automat.md` — `Game1`: hlavní XNA Game třída, stavový automat fází hry
13. `ch13-igame1-a-zavislosti.md` — `IGame1` rozhraní, závislosti mezi podsystémy
14. `ch14-cna-xna-adaptacni-vrstva.md` — Jak se hra mapuje na XNA API skrze CNA

### Part IV — Simulace Decor (`part04-simulace-decor/`) — nejrozsáhlejší část
15. `ch15-decor-prehled.md` — `Decor`: přehled zodpovědností a datového modelu
16. `ch16-mapa-dlazdic.md` — Mapa dlaždic 100×100, `Cellule`, souřadnicové systémy
17. `ch17-blupi-stavovy-automat.md` — Blupi: stavový automat hráčovy postavy
18. `ch18-akce-a-animace-blupiho.md` — `BlupiAction` a animační sekvence
19. `ch19-objekty-a-decor-akce.md` — `MoveObject`, `DecorAction`, `ObjectType`
20. `ch20-ai-nepratel-a-tvoru.md` — AI nepřátel a tvorů
21. `ch21-fyzika-a-kolize.md` — Fyzika pohybu a detekce kolizí
22. `ch22-dvere-klice-a-doorkeyflags.md` — Dveře, klíče, `DoorKeyFlags`, teleporty, výtahy
23. `ch23-tajne-schopnosti-a-cheat-system.md` — `SecretPower`, cheat systém (`Cheat System.md`)
24. `ch24-mise-a-continuemission.md` — Cíle mise, `ContinueMission`, podmínky výhry/prohry
25. `ch25-rychlost-hry-a-zoom.md` — `GameSpeed`, `Zoom`, škálování času
26. `ch26-katalog-dlazdic-a-ikon.md` — Katalog herních dlaždic/ikon podle chování (na základě
    skutečných `Is*()` predikátů v `Decor.cpp`, s odkazem na `ENUMS.md` jako analytický zdroj)
27. `ch27-referencni-katalog-decor-hpp.md` — Úplný katalog členů `Decor.hpp` (metody, proměnné)

### Part V — Vykreslování (`part05-vykreslovani/`)
28. `ch28-pixmap-ipixmap.md` — `Pixmap`/`IPixmap`: vrstva vykreslování sprajtů
29. `ch29-pixmapchannel-a-vrstveni.md` — `PixmapChannel`, vrstvení pozadí/objektů/UI
30. `ch30-tables-animace-a-pohyb.md` — `Tables`: animační a pohybové tabulky
31. `ch31-text-rendering.md` — `Text`: vykreslování textu
32. `ch32-jauge-ukazatele.md` — `Jauge`: ukazatele/HUD lišty
33. `ch33-slider-ovladaci-prvek.md` — `Slider`: UI posuvník

### Part VI — Zvuk (`part06-zvuk/`)
34. `ch34-sound-isound-architektura.md` — `Sound`/`ISound` architektura
35. `ch35-soundchannel-a-mixovani.md` — `SoundChannel`, hlasitost/výška tónu (`tableVolumePitch`)
36. `ch36-analyza-zvukovych-problemu.md` — Rozbor `AUDIO_ANALYSIS.md`: hlášené problémy se zvukem

### Part VII — Vstup (`part07-vstup/`)
37. `ch37-inputpad-dotyk-klavesnice-akcelerometr.md` — `InputPad`: sjednocení dotyku/klávesnice/akcelerometru
38. `ch38-keypressflags-a-mapovani.md` — `KeyPressFlags` a mapování vstupu na akce

### Part VIII — Data, perzistence, obsah (`part08-data-perzistence-obsah/`)
39. `ch39-gamedata-ukladani-her.md` — `GameData`: formát uložených her, 3 sloty hráčů
40. `ch40-worlds-format-urovni.md` — `Worlds`: načítání úrovní, formát textového souboru úrovně
41. `ch41-content-pipeline.md` — Obsahový pipeline: ikony, zvuky, pozadí
42. `ch42-myresource-sprava-zdroju.md` — `MyResource`: správa zdrojů

### Part IX — Pomocné typy (`part09-pomocne-typy/`)
43. `ch43-tinypoint-tinyrect.md` — `TinyPoint`, `TinyRect` (nestandardní pořadí polí!)
44. `ch44-misc-pomocne-funkce.md` — `Misc`: pomocné funkce
45. `ch45-helper.md` — `Helper`
46. `ch46-def-zakladni-definice.md` — `Def.hpp`: základní definice a konstanty

### Part X — Platformy do hloubky (`part10-platformy/`)
47. `ch47-android-hluboky-ponor.md` — Android integrace do hloubky (assets symlinky, APK balení)
48. `ch48-windows-hluboky-ponor.md` — Windows do hloubky (`WINDOWS.md`)
49. `ch49-web-virtualni-souborovy-system.md` — Web/Emscripten virtuální FS a IndexedDB perzistence
50. `ch50-ram-analyza-pameti.md` — Rozbor `RAM.md`: analýza spotřeby paměti

### Part XI — Historie a praxe (`part11-historie-a-praxe/`)
51. `ch51-ilspy-dekompilace-a-csharp-stuby.md` — ILSpy dekompilace, zbytkové C# stuby
    (`Microsoft.Xna.Framework.GamerServices`, `Microsoft.Devices.Sensors`)
52. `ch52-dotnet-a-xna-migrace.md` — Migrace .NET/XNA (rozbor `.Net and XNA used part.md`)
53. `ch53-doxygen-metodika.md` — Metodika Doxygen dokumentace (`DOXYGEN_DOCUMENTATION_PLAN.md`)
54. `ch54-todo-a-roadmapa.md` — `TODO.md` a plán do budoucna

### Přílohy (`appendices/`)
- A `appendix-a-katalog-trid-a-souboru.md` — Úplný katalog tříd a souborů
- B `appendix-b-katalog-vyctu.md` — Úplný katalog výčtů (skutečné enum class definice)
- C `appendix-c-specifikace-formatu-urovni.md` — Specifikace formátu souboru úrovně (`worlds/*.txt`)
- D `appendix-d-slovnik-pojmu.md` — Slovník pojmů (anglicko-český)
- E `appendix-e-cheat-kody.md` — Reference cheat kódů
- F `appendix-f-mapa-repozitare.md` — Mapa repozitářů OpenEggbert (rychlá reference)

## Stav kapitol

Sloupec Stav: `nenapsáno` / `rozpracováno` / `hotovo (nekontrolováno)` / `hotovo (zkontrolováno)`.
Podrobný, průběžně aktualizovaný stav viz `book/SUMMARY.md` — ten je zdroj pravdy pro stav
jednotlivých kapitol, tato tabulka v `PLAN.md` slouží jen k plánování vln práce.

- **Vlna 0 (kostra):** README, CLAUDE.md, PLAN.md, NEXT.md, PROGRESS.md, `book/SUMMARY.md`,
  prázdné adresáře pro všech 11 částí + přílohy.
- **Vlna 1:** Part I–IV (kapitoly 1–27)
- **Vlna 2:** Part V–VIII (kapitoly 28–42)
- **Vlna 3:** Part IX–XI + přílohy (kapitoly 43–54 + A–F)

## Log sezení

### 2026-07-28 — Založení projektu
- Prázdný repozitář `mobile-eggbert-bible` (žádné commity). Přidán a naklonován `mobile-eggbert`
  (hlavní zdroj) a `cna-bible` (vzor stylu/metodiky) do sezení.
- Změřen rozsah zdrojového kódu (31 301 řádků C++, `Decor.cpp` = 11 720 řádků jako jádro).
- Navržena struktura 54 kapitol + 6 příloh napříč 11 částmi, v Markdownu (LaTeX toolchain v tomto
  prostředí není dostupný — `pdflatex` chybí).
- Zapsána poctivá poznámka k rozsahu (1000 stran není dosažitelných jako genuinní, nevycpaný
  obsah pro jednu hru o 31k řádcích; cílíme na 300–500 stran ekvivalentu jako upřímný, hluboký
  výsledek — stejný princip jako `cna-bible`).
