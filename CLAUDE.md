# CLAUDE.md

Notes for future Claude sessions working on this repo. Read this before suggesting changes — it captures hard-won lessons that aren't visible from the code alone.

## Project purpose

A Kindle popup dictionary that translates English → Turkish. The user reads scientific/academic English (Nick Lane, etc.) at C1 level and wanted Turkish translations one long-press away. No such dictionary existed in usable form, so we built one from open data.

Output artifact: `english-turkish-dictionary.mobi`. Drop it on a Kindle, set as default English dictionary, done.

Repo: `github.com/mybottles/kindle-en-tr-dictionary` (developer: Murat Uysal, muratuysal.com).
Dictionary popup label: `English-Turkish (muratuysal.com)` — this is what shows under each popup; set in `<dc:title>` and propagates to EXTH 503 + MOBI full_name.

## Architecture

```
                            build.py
   ┌──────────────────┐         │
   │ kaikki-en.jsonl  │─┐       ▼
   │ (2.8 GB, Wikt)   │ │   ┌────────────┐    kindlegen -c1     ┌──────────────┐
   └──────────────────┘ ├──▶│ dict-src/  │──────────────────▶   │ english-     │
   ┌──────────────────┐ │   │  *.html    │   (via Rosetta 2)    │ turkish-     │
   │ freedict-eng-tur │─┤   │  dict.opf  │                      │ dictionary   │
   │ .tab (7 MB, GPL) │ │   │  toc.ncx   │                      │ .mobi 5.5MB  │
   └──────────────────┘ │   │  cover.jpg │                      └──────────────┘
   ┌──────────────────┐ │   └────────────┘
   │ lemminflect      │─┘
   │ (Python lib)     │
   └──────────────────┘
```

### `build.py` (single file, ~280 lines)

1. **Stream-parse** kaikki JSONL (1.46M lines) → keep entries with at least one Turkish translation (`code == "tr"` in `translations` field, both entry-level and sense-level).
2. **Group** by headword across POS (verbs, nouns, etc. for the same word merge into one entry).
3. **Generate inflections** for each headword via `lemminflect.getAllInflections` (covers -s, -ed, -ing, comparatives), plus pull irregular forms from the entry's `forms` field (mice, children, aardwolves).
4. **Augment with FreeDict eng-tur** — adds 22k new headwords and augments 10k existing ones.
5. **Render** each entry as `<idx:entry>` HTML; chunk into 6,000 entries per file (kindlegen prefers <30 MB per HTML).
6. **Write OPF** with `<x-metadata>` containing `DictionaryInLanguage=en`, `DictionaryOutLanguage=tr`, `DefaultLookupIndex=default`. Also writes `toc.ncx`, `cover.jpg`, and license/usage HTML.

### Final compile step (not in build.py)

```bash
cd dict-src && arch -x86_64 ../kindlegen dict.opf -c1 -dont_append_source
```

Then copy `dict-src/dict.mobi` → `english-turkish-dictionary.mobi`.

## Hard-won lessons (don't relearn these)

### Use kindlegen, not kindling

kindling (Rust, [github.com/ciscoriordan/kindling](https://github.com/ciscoriordan/kindling)) is faster and runs natively on arm64. We tried it first. Its README claims drop-in kindlegen compatibility.

**It is not, for Kindle Paperwhite 12 firmware 5.19+.**

kindling produces a MOBI with only the orth INDX record. kindlegen produces a MOBI with three separate INDX records:

| Field | kindlegen | kindling |
|---|---|---|
| `mobi.orth_index` | ✓ | ✓ |
| `mobi.infl_index` | **separate INDX record** | NONE (merged into orth) |
| `mobi.names_index` | **separate INDX record** | NONE |

On Kindle Paperwhite 12 the lookup engine silently returns "no definition found" for every word when `infl_index`/`names_index` are missing. The bug is invisible — the file shows up in the library, can be selected as default dictionary, even displays popups; but every popup is empty.

If a future user reports the same symptom, **the answer is "rebuild with kindlegen"**, not "fiddle with the OPF" — we tried that path exhaustively.

### Use `-c1`, not `-c2`

kindlegen 2.9 on Apple Silicon (via Rosetta) crashes with SIGSEGV under `-c2` (huffdic compression) for dictionaries with ~40k entries. `-c1` (standard PalmDOC) works fine and produces a usable MOBI. File size grows slightly (5.5 MB vs ~3 MB compressed), still trivial.

The kindling README documents this exact crash: kindlegen has "superlinear inflection index computation, and a 32-bit Windows build that crashes on large files."

### kindlegen output naming

kindlegen names its output after the OPF basename. `dict.opf` → `dict.mobi`. There is no flag to change this — the `-o` flag in old versions took a directory, not a filename. We rename it post-build.

### `<idx:orth>` entry structure

The format Kindle expects:

```html
<idx:entry name="default" scriptable="yes" spell="yes">
  <idx:orth value="run">
    <b>run</b>
    <idx:infl>
      <idx:iform value="ran"/>
      <idx:iform value="running"/>
      <idx:iform value="runs"/>
    </idx:infl>
  </idx:orth>
  <p>v. koşmak; akmak; yönetmek</p>
</idx:entry>
```

Key points:
- The headword **must appear as visible text** inside `<idx:orth>` (we use `<b>...</b>`). Without visible text, kindling silently fails to locate the entry in the text blob.
- `<idx:infl>` lives *inside* `<idx:orth>`, after the visible `<b>`.
- The `value=` attribute on `<idx:orth>` should equal the visible headword (kindlegen indexes against this attribute; the visible text is for rendering).
- `<idx:iform value="ran"/>` is **self-closing**; iforms have no visible text.

### Data source choice

- **kaikki.org Wiktextract**: best machine-readable Wiktionary extract. Per-entry `translations` field gives `lang_code: "tr"` matches. 19k English headwords have Turkish translations — surprisingly small fraction of the 1.46M-entry dump because most English headwords don't get translated on Wiktionary.
- **FreeDict eng-tur**: 36k headwords, GPLv2+. Has dirty data (literal "(anat.)", "(ark.)" entries from a sloppy converter) — `build.py` filters with a regex requiring `^[A-Za-z][A-Za-z'-]+$`. After filtering, ~22k truly new headwords plus augmentation for existing ones.

We did **not** use dict.cc (license unclear) or Apertium (smaller eng-tur than FreeDict).

### License combinatorics

CC BY-SA 4.0 is one-way compatible with GPLv3 (CC content can be relicensed into GPL but not the reverse). Since FreeDict is GPLv2+, the combined artifact is effectively GPLv2+. The build code (`build.py`) is MIT because Murat authored it and chose MIT.

This is reflected in `LICENSE` and both READMEs.

## Common operations

### Rebuilding from scratch

```bash
git clone https://github.com/mybottles/kindle-en-tr-dictionary
cd kindle-en-tr-dictionary

# 1. Get source data (not in repo - too large, regenerable)
curl -L -o kaikki-en.jsonl \
  https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl
curl -L -o freedict.tar.xz \
  https://download.freedict.org/dictionaries/eng-tur/0.3/freedict-eng-tur-0.3.stardict.tar.xz
mkdir -p freedict && tar -xJf freedict.tar.xz -C freedict
.venv/bin/pyglossary --read-format=Stardict --write-format=Tabfile \
  freedict/*/eng-tur.ifo freedict-eng-tur.tab

# 2. Get kindlegen
curl -L -o kindlegen \
  https://github.com/andyljones/kindlegen-64/raw/master/kindlegen
chmod +x kindlegen
softwareupdate --install-rosetta --agree-to-license  # if not installed

# 3. Python deps
python3 -m venv .venv
.venv/bin/pip install pyglossary lemminflect Pillow

# 4. Build
.venv/bin/python build.py                                    # ~30s
cd dict-src && arch -x86_64 ../kindlegen dict.opf -c1 -dont_append_source  # ~3min
cp dict.mobi ../english-turkish-dictionary.mobi
```

### Updating with a newer Wiktionary dump

kaikki.org refreshes monthly. New dump URL is the same; just re-download `kaikki-en.jsonl` and rerun `build.py` + kindlegen. The May 2026 dump used here had ~21k entries with Turkish translations; newer dumps will likely have more.

### Verifying the build is correct

```bash
./kindling dump english-turkish-dictionary.mobi | grep -E "^mobi\.(orth|infl|names)_index"
```

Should show three non-NONE values. If `infl_index` says `NONE`, you built with kindling instead of kindlegen — start over.

```bash
./kindling validate dict-src/dict.opf
```

Should return "0 errors, 0 warnings" (only an info note about marketing cover image, which is irrelevant for sideload).

### Inspecting an entry

```bash
.venv/bin/python -c "
import re
with open('dict-src/content002.html') as f: c = f.read()
m = re.search(r'<idx:entry.*?<b>evolution</b>.*?</idx:entry>', c, re.S)
print(m.group(0))
"
```

## Files not in the repo (intentional)

| File | Why excluded |
|---|---|
| `kaikki-en.jsonl` (2.8 GB) | Too large; download from kaikki.org |
| `freedict-eng-tur.tab` (7.4 MB) | Regenerable from `freedict.tar.xz` |
| `freedict.tar.xz` (2 MB) | Source; user should download fresh |
| `freedict/` | Extracted source |
| `kindlegen` (22 MB) | Amazon's binary, license unclear for redistribution |
| `kindling` (12 MB) | Third-party; download from their releases |
| `dict-src/` | Intermediate build artifacts |
| `.venv/` | Python virtualenv |

`english-turkish-dictionary.mobi` (5.5 MB) **is** in the repo — that's the user-facing artifact.

## Likely future requests

- **"Add a Turkish-English direction too"** — would require a second OPF (`DictionaryInLanguage=tr`, `DictionaryOutLanguage=en`) with Turkish headwords. Would need to invert kaikki translations and add Turkish inflection support (different morphology — agglutinative). Not a small task.
- **"Make a Calibre plugin"** — Calibre's dict converter strips index records; can't produce a working Kindle dict. Don't try.
- **"Why isn't kindlegen on Homebrew?"** — Amazon abandoned it in 2020. No official source. The GitHub mirror ([andyljones/kindlegen-64](https://github.com/andyljones/kindlegen-64)) is the closest thing.
- **"Make the popup show etymology / IPA / example sentences"** — possible (kaikki has all that data) but bloats the MOBI and slows lookups. Punt unless the user explicitly asks.

## Quick reference: MOBI dictionary spec

EXTH records Kindle reads for dictionary detection:
- `531` — DictionaryInLanguage (e.g. `"en"`)
- `532` — DictionaryOutLanguage (e.g. `"tr"`)
- `547` — `"InMemory"` flag

MOBI header fields:
- offset 24 — `orth_index` (record number of orthographic INDX)
- offset 28 — `infl_index` (record number of inflection INDX)
- offset 32 — `names_index`
- offset 92 — `locale` (book lang LCID)
- offset 96 — `dict_input_lang` LCID
- offset 100 — `dict_output_lang` LCID

LCIDs of interest:
- `0x0009` — English (any)
- `0x0409` — English (US)
- `0x001F` — Turkish

## When in doubt

Re-read kindling's [README](https://github.com/ciscoriordan/kindling) — best practical MOBI dictionary documentation in 2026. The Amazon Kindle Publishing Guidelines PDF is also accurate but harder to navigate.

Don't trust LLM-generated MOBI advice unless you can verify it against either a working kindlegen reference MOBI or the actual binary file structure.
