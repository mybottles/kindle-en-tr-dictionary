# Kindle English → Turkish Dictionary

**Long-press any English word in your Kindle book and see its Turkish translation.**

[![GitHub stars](https://img.shields.io/github/stars/mybottles/kindle-en-tr-dictionary?style=social)](https://github.com/mybottles/kindle-en-tr-dictionary/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/mybottles/kindle-en-tr-dictionary?style=social)](https://github.com/mybottles/kindle-en-tr-dictionary/network/members)
[![License: GPL v2+](https://img.shields.io/badge/License-GPL%20v2%2B-blue.svg)](https://www.gnu.org/licenses/gpl-2.0)
[![Kindle](https://img.shields.io/badge/Kindle-Paperwhite%2012-orange)](https://github.com/mybottles/kindle-en-tr-dictionary)

> _**Türkçe sürüm:** [README.md](README.md)_

**41,424 headwords · 152,097 translations · 45,675 inflected forms** &nbsp;·&nbsp; built from CC BY-SA + GPL open sources.

Download → copy to Kindle → set as default English dictionary → start reading.

---

## Why this dictionary exists

I searched for months — **there was no free, working English-to-Turkish dictionary you could sideload onto a modern Kindle.**

- Paid options on the Amazon Store are either absent or overpriced
- Old `.mobi` files floating on the web are broken, fail lookup on recent Kindles, or don't resolve inflections (no popup result for "ran", "running", "books", "better")
- Outputs from Calibre and pyglossary throw "no definition found" on Kindle Paperwhite 12 firmware because they omit the `infl_index` and `names_index` MOBI sections that the lookup engine requires

I built this to fill the gap. Open source, open data, open license. Designed with C1-level English readers in mind — people reading scientific or academic books (Nick Lane, Sapolsky, Pinker, etc.) who want one-tap Turkish definitions without breaking flow.

A gift to everyone who needs it.

---

## Quick install

1. Download **`english-turkish-dictionary.mobi`** from the [Releases](../../releases/latest) page
2. Connect Kindle via USB, copy the file into `documents/` (or send via Send-to-Kindle)
3. On Kindle: **Settings → Language & Dictionaries → Dictionaries → English →** select *English-Turkish (muratuysal.com)*
4. Open any English book, long-press a word, see the Turkish translation in the popup.

> "ran" → resolves to "run"; "running" → "run"; "mice" → "mouse"; "better" → "good".
> Inflection mapping covers 45,675 forms.

---

## What's inside

| | |
|---|---|
| **Headwords** | 41,424 |
| **Turkish translations** | 152,097 (avg. 3.7 per word) |
| **Inflected forms** (`<idx:infl>`) | 45,675 |
| **File size** | 5.5 MB |
| **Sources** | English Wiktionary + FreeDict eng-tur |
| **Popup label** | English-Turkish (muratuysal.com) |

### Coverage sample

Scientific / academic terms (critical for C1+ readers):

```
mitochondrion    → mitokondri    [organelle in eukaryotic cells]
photosynthesis   → fotosentez    [process of converting light to chemical energy]
phosphorylation  → fosforilasyon [transfer of phosphate group]
eukaryote        → ökaryot       [organism with nucleus-containing cells]
substrate        → alt tabaka; mayadan etkilenmiş madde
recursion        → özyineleme; tekrarlama
allele           → alel; gen çifti
chloroplast      → kloroplast
oxidative        → oksidatif
evolution        → evrim; tekamül; inkişaf; gelişme
```

Everyday vocabulary:

```
run     v.  koşmak; akmak; yönetmek; çalıştırmak
book    n.  kitap;  v. yer ayırtmak
better  →   resolves to "good"
```

---

## Data sources

| Source | License | Headwords | Role |
|---|---|---|---|
| [kaikki.org Wiktextract](https://kaikki.org/dictionary/English/) (English Wiktionary, May 2026) | CC BY-SA 4.0 + GFDL | 19,384 | Primary — provides sense disambiguators and English glosses |
| [FreeDict eng-tur v0.3](https://download.freedict.org/dictionaries/eng-tur/0.3/) | GPL v2.0+ | 22,040 new + 10,358 augmented | Secondary — expands coverage |

**Licensing:** The combined `.mobi` artifact is effectively distributed under **GPL v2.0+** (CC BY-SA 4.0 is one-way compatible with GPLv3; FreeDict's GPL dominates the combined work). The build code ([`build.py`](build.py)) is **MIT** licensed.

---

## Building from scratch

You can grab the prebuilt MOBI from Releases — but if you want to rebuild:

### Prerequisites

- Python 3.11+
- For macOS Apple Silicon: **Rosetta 2** (`softwareupdate --install-rosetta --agree-to-license`)
- Amazon kindlegen 2.9 (x86_64 Mac binary — [archived here](https://github.com/andyljones/kindlegen-64))
- ~3 GB free disk (for the kaikki dump)

### Steps

```bash
git clone https://github.com/mybottles/kindle-en-tr-dictionary
cd kindle-en-tr-dictionary

# Python environment
python3 -m venv .venv
.venv/bin/pip install pyglossary lemminflect Pillow

# Download the kaikki English Wiktextract dump (2.8 GB)
curl -L -o kaikki-en.jsonl \
  https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl

# Download FreeDict eng-tur and convert to tab
curl -L -o freedict.tar.xz \
  https://download.freedict.org/dictionaries/eng-tur/0.3/freedict-eng-tur-0.3.stardict.tar.xz
mkdir -p freedict && tar -xJf freedict.tar.xz -C freedict
.venv/bin/pyglossary --read-format=Stardict --write-format=Tabfile \
  freedict/*/eng-tur.ifo freedict-eng-tur.tab

# Download kindlegen
curl -L -o kindlegen \
  https://github.com/andyljones/kindlegen-64/raw/master/kindlegen
chmod +x kindlegen

# Generate OPF + HTML
.venv/bin/python build.py

# Compile MOBI (via Rosetta)
cd dict-src && arch -x86_64 ../kindlegen dict.opf -c1 -dont_append_source
cp dict.mobi ../english-turkish-dictionary.mobi
```

Total runtime: ~4-5 minutes (excluding the 2.8 GB download).

### Why `-c1` and why kindlegen specifically?

- **kindlegen with `-c1`**: produces separate `infl_index` and `names_index` records. Kindle Paperwhite 12 firmware 5.19+ silently returns "no definition found" without them. `-c2` (huffdic compression) crashes with SIGSEGV on Apple Silicon under Rosetta for 41k-entry dictionaries — known kindlegen bug.
- **We tried kindling (Rust, arm64-native, faster)**: its output is structurally similar to kindlegen but omits the `infl_index`/`names_index` records, folding all lookups into a single orth INDX. This works on older Kindles but not on Paperwhite 12.

Full technical notes: [`CLAUDE.md`](CLAUDE.md).

---

## Known limitations

- **Single-word lookups only**: the Kindle popup can only select a single token. Multi-word phrases like "in spite of" aren't covered (Kindle infrastructure restriction).
- **Wiktionary gaps**: some technical or modern terms don't have Turkish translations in Wiktionary (e.g. `mitochondria` is captured as the plural inflection of headword `mitochondrion`).
- **Limited context**: translations are mostly single-word equivalents. For complex idioms, a separate reference is needed.
- **Wiktionary's inconsistent quality**: some translations are dialectal or archaic (`lügat`, `ışılbireşim`). Common usages appear first.

---

## Contributing

Pull requests welcome, especially for:

- **Better sense disambiguators** — currently I show English glosses; Turkish glosses would be ideal
- **Additional data sources** — Apertium, Wikidata lexemes, etc.
- **HTML rendering improvements** — more readable popup format
- **Bug reports** — open an issue if you find a word with a wrong or missing translation

---

## Author

**Murat Uysal** &nbsp;·&nbsp; [muratuysal.com](https://muratuysal.com)

From open data to open output — dedicated to everyone who wants to read English on a Kindle with Turkish translations at their fingertips.

---

## License

- **Build code** (`build.py`): MIT — see [`LICENSE`](LICENSE)
- **Dictionary content** (`english-turkish-dictionary.mobi`): GPL v2.0+ (inherited from source data)

## Acknowledgments

- Tatu Ylönen and the [Wiktextract](https://github.com/tatuylonen/wiktextract) team — for the kaikki.org dump
- Mehmet Ali Vardar — for the original gtksozluk2 that became FreeDict eng-tur
- The thousands of volunteer editors who contributed scientific and technical translations to English Wiktionary
- [Amazon kindlegen](https://kdp.amazon.com/) — abandoned in 2020 but still the only reliable Kindle dictionary builder
