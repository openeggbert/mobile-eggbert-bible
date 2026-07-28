# NEXT — aktuální stav a co dělat dál

**Poslední aktualizace: 2026-07-28, zakládací sezení.**

## Co je hotovo

- Kostra repozitáře: `README.md`, `CLAUDE.md`, `PLAN.md`, `PROGRESS.md`, tento soubor.
- Adresářová struktura `book/part01-…` až `book/part11-…` + `book/appendices/`.
- Plán 54 kapitol + 6 příloh v `PLAN.md`.

## Co dělat hned příště

1. Vytvořit `book/SUMMARY.md` (obsah se stavem kapitol), pokud ještě neexistuje nebo je zastaralý.
2. Psát kapitoly po vlnách podle `PLAN.md` (Vlna 1: Part I–IV, kapitoly 1–27). Každá kapitola musí
   být založená na reálném přečtení zdroje v `mobile-eggbert` — viz metodika v `CLAUDE.md`.
3. Po každé vlně: namátkově zkontrolovat 2–3 kapitoly na grounding (cituje skutečný kód?),
   opravit styl/konzistenci, aktualizovat `book/SUMMARY.md`, commitnout a pushnout.
4. Po dokončení všech tří vln aktualizovat `PLAN.md` (log sezení) a toto `NEXT.md`.

## Otevřené otázky / rozhodnutí, která čekají na autora

- Žádná zatím. Pokud při psaní narazíš na rozpor (např. zjistíš, že skutečný rozsah by měl být jiný
  než plán počítá), zapiš to do `PLAN.md` sekce "Log sezení" a do tohoto souboru, ne mlčky.

## Repozitáře potřebné pro pokračování

Přidej do sezení (nástrojem pro přidání repozitáře) a naklonuj mimo tento repozitář:
- `openeggbert/mobile-eggbert` — hlavní zdroj
- `openeggbert/cna-bible` — vzor stylu (jen pro formu, ne obsah)
- `openeggbert/mobile-eggbert-legacy` — pro kapitoly o historii/migraci (Part XI), pokud ještě
  není přidán
