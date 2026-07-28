# Mobile Eggbert Bible — průvodce pro sezení Claude Code

Tento repozitář je jedna, sjednocená Markdown kniha o hře `openeggbert/mobile-eggbert` (C++ port
*Speedy Blupi*, postavený na frameworku CNA). Píše se postupně, napříč mnoha sezeními, samotným
Claude Code, pod vedením autora repozitáře. Je psaná **česky**.

**Na začátku každého sezení nejdřív přečti `NEXT.md`**, ne jen tento soubor — `NEXT.md` nese
konkrétní, aktuální kontext (co bylo právě dokončeno, co se rozpracovává, co dělat hned příště),
který tento soubor záměrně neopakuje. Pak přečti `PLAN.md` pro celý seznam úkolů a cílový rozsah
jednotlivých kapitol. `PROGRESS.md` je historický log toho, co bylo hotovo před aktuální fází
rozšiřování — užitečné pro kontext, ne pro „co dělat dál".

## Rozvržení repozitáře

- `book/SUMMARY.md` — obsah celé knihy se stavem každé kapitoly (`hotovo` / `rozpracováno` /
  `nenapsáno`). Aktualizuj při každé změně stavu kapitoly.
- `book/partNN-slug/chNN-slug.md` — jednotlivé kapitoly, číslované 1 až 54, napříč jedenácti částmi
  (Part I–XI).
- `book/appendices/appendix-X-slug.md` — přílohy A–F (katalog tříd, katalog výčtů, formát úrovní,
  slovník pojmů, cheat kódy, mapa repozitářů).
- `PLAN.md` — pracovní plán rozšiřování: seznam kapitol, cílový rozsah stránek, metodika, otevřené
  otázky/konflikty, datovaný log sezení. Trvalý zdroj pravdy o tom, jaký rozsah má která kapitola
  cílit a proč.
- `NEXT.md` — krátký, aktuální brífink pro sezení, které naváže. Aktualizuj na **konci** každého
  sezení (ne jen po dokončení kapitoly), aby nové sezení bez paměti na tuto konverzaci mohlo
  bezpečně navázat.
- `PROGRESS.md` — historický záznam o tom, co bylo hotovo v předchozích fázích. Nepřidávej sem nové
  záznamy — nová práce jde do session logu v `PLAN.md` a do `NEXT.md`.

## Formát knihy

Kniha je v **Markdownu**, ne v LaTeXu (na rozdíl od `cna-bible`) — v tomto prostředí není dostupný
`pdflatex`/`latexmk` toolchain, a Markdown se navíc dobře čte přímo na GitHubu bez nutnosti
kompilace. Pokud bude v budoucnu k dispozici LaTeX toolchain a autor bude chtít PDF, obsah lze
převést (např. přes pandoc) — struktura `book/partNN/chNN` je k tomu připravená.

## Nesmlouvatelná metodika (platí pro celý projekt, ne jen pro rozšiřování)

- **Každé tvrzení je podložené reálným přečtením zdroje.** Než napíšeš větu o nějaké třídě, metodě,
  konstantě nebo mechanice, přečti skutečný `.hpp`/`.cpp` soubor, `worlds/*.txt` soubor, nebo
  `*.md` dokument v `mobile-eggbert` repozitáři. Nikdy neparafrázuj z paměti a nevymýšlej
  věrohodně vypadající API, které jsi neověřil.
- **Ukázky kódu musí být reálné**, doslovně nebo téměř doslovně převzaté z konkrétního souboru a
  řádku (uváděj `soubor.cpp:NNN` u nefatálních citací), ne vymyšlené od nuly.
- **Žádné fiktivní screenshoty.** Tato kniha (na rozdíl od `cna-bible`) v této fázi neobsahuje
  screenshoty vůbec — hru zde není možné spustit a vyfotit. Pokud se to změní, platí stejné
  pravidlo jako v `cna-bible`: reálný screenshot, nebo žádný.
- **`ENUMS.md` v `mobile-eggbert` je návrh na refaktoring, ne existující kód.** Popisuje magická
  čísla, která by šlo nahradit výčty, ale výčty **nejsou** v kódu implementované — kód pořád
  používá syrová čísla (`68`, `91`, …) přímo v podmínkách. Kdykoliv kapitola cituje `ENUMS.md`,
  musí to být jasně označené jako analytický dokument/návrh, ne jako popis aktuálního stavu kódu.
- **Commituj po menších, popisných krocích a pushuj po každém** — ne jedním obřím commitem na
  konci sezení. Díky tomu je víceseanční projekt skutečně navazatelný.
- Křížové odkazy mezi kapitolami používej jako `[Kapitola N](../partNN-slug/chNN-slug.md)` —
  relativní Markdown odkazy, funkční přímo na GitHubu.
- Cituj konkrétní řádky/soubory z `mobile-eggbert` ve tvaru `` `Decor.cpp:1234` `` — bez
  hypertextových odkazů na konkrétní commit (ten se mění), jen jako textovou citaci.
- Technické identifikátory (názvy tříd, metod, proměnných, souborů, enum hodnot) zůstávají v
  angličtině/originále — nepřekládej je. Překládá se výklad okolo nich.

## Kde leží zdrojové repozitáře (v rámci jednoho sezení)

Tyto repozitáře se do sezení přidávají nástrojem pro přidání repozitáře a klonují se mimo tento
repozitář (typicky do `/workspace/<repo>`) — **neklonuj je dovnitř `mobile-eggbert-bible`**:

- `mobile-eggbert` — hlavní zdroj (hra samotná)
- `cna` — CNA framework (pro pochopení, na čem hra běží; citovat jen tam, kde je to nutné pro
  pochopení mobile-eggbert, hluboký rozbor CNA samotného patří do `cna-bible`, ne sem)
- `cna-bible` — vzor stylu/metodiky (nečerpat obsah, jen formu)
- `mobile-eggbert-legacy` — dekompilovaný C# původ, pro kapitoly o historii/migraci
