# Mobile Eggbert Bible

Toto je rozsáhlá, do hloubky jdoucí technická kniha o zdrojovém kódu hry
[**Mobile Eggbert**](https://github.com/openeggbert/mobile-eggbert) — C++ portu hry *Speedy Blupi*
(původně Windows Phone/XNA, 2013), postaveného na frameworku [CNA](https://github.com/openeggbert/cna).

Kniha je psána **česky**, po vzoru sesterského projektu
[`cna-bible`](https://github.com/openeggbert/cna-bible) (anglická kniha o samotném CNA ekosystému),
ale zaměřuje se výhradně na `mobile-eggbert`: každou třídu, každý soubor, každý herní mechanismus,
formát souborů úrovní, build systém pro všechny platformy a historii portování z originálního C#/XNA.

## Cíl

Po přečtení této knihy by měl čtenář rozumět zdrojovému kódu hry natolik hluboko, že se v něm dokáže
orientovat jako expert — vědět, kde která herní mechanika žije, jak funguje stavový automat postavy
Blupi, jak je uložena mapa úrovně, jak funguje ukládání her, zvuk, vstup, a jak se hra sestavuje a
spouští na Linuxu, Windows, webu (Emscripten) a Androidu.

## Poctivá poznámka k rozsahu

Zadání zní „klidně tisíc stran, ale musím být po nastudování expert". `mobile-eggbert` má cca 31 000
řádků C++ (viz `PLAN.md`) — to je jedna hra, ne celý ekosystém. Sesterská kniha `cna-bible`, která
pokrývá **celý** CNA ekosystém (desítky repozitářů), skončila poctivě na 233 stranách, protože autoři
odmítli vycpávat text nepodloženými nebo opakujícími se pasážemi jen kvůli počtu stran. Tady platí
stejné pravidlo: **žádná věta bez reálného přečtení zdrojového kódu**. Cílíme na maximální upřímnou
hloubku (viz `PLAN.md` pro aktuální odhad rozsahu), ne na umělé vata-stránky. Kniha je stavěná tak, aby
se dala v dalších sezeních dále rozšiřovat.

## Struktura repozitáře

- `book/` — samotná kniha, v Markdownu. `book/SUMMARY.md` je obsah se stavem každé kapitoly.
  Kapitoly jsou rozdělené do `book/partNN-slug/chNN-slug.md` podle 11 částí (Part I–XI) plus
  `book/appendices/` (přílohy A–F).
- `PLAN.md` — pracovní plán: seznam kapitol, cílový rozsah, metodika psaní, otevřené otázky.
  Trvalý zdroj pravdy o tom, co se ještě má napsat a proč.
- `NEXT.md` — krátké shrnutí aktuálního stavu pro navazující sezení (co bylo právě dokončeno, co
  dělat příště). Čti jako první při pokračování práce.
- `PROGRESS.md` — historický log dokončené práce.

## Zdrojové repozitáře, ze kterých kniha čerpá

- [`openeggbert/mobile-eggbert`](https://github.com/openeggbert/mobile-eggbert) — samotná hra (hlavní zdroj)
- [`openeggbert/cna`](https://github.com/openeggbert/cna) — CNA framework, na kterém hra běží
- [`openeggbert/cna-bible`](https://github.com/openeggbert/cna-bible) — vzor stylu a metodiky
- [`openeggbert/mobile-eggbert-legacy`](https://github.com/openeggbert/mobile-eggbert-legacy) — dekompilovaný C# původ
