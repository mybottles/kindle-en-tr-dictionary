"""
Build a Kindle English -> Turkish dictionary from kaikki.org Wiktextract JSONL.

Pipeline:
  1. Stream-parse kaikki-en.jsonl. For each English entry, collect Turkish
     translations (entry-level + sense-level).
  2. Generate English inflections via lemminflect.
  3. Emit OPF + content HTML with <idx:infl>/<idx:iform> tags.
  4. Caller then runs `kindling build dict.opf -o english-turkish-dictionary.mobi`.
"""
from __future__ import annotations

import html
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import re
from lemminflect import getAllInflections

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "kaikki-en.jsonl"
FREEDICT = ROOT / "freedict-eng-tur.tab"
OUT_DIR = ROOT / "dict-src"
OUT_DIR.mkdir(exist_ok=True)

# kaikki POS -> Universal POS tag for lemminflect, and a display label
POS_MAP = {
    "noun": ("NOUN", "n."),
    "verb": ("VERB", "v."),
    "adj": ("ADJ", "adj."),
    "adv": ("ADV", "adv."),
    "name": ("PROPN", "n."),
    "num": ("NUM", "num."),
    "pron": ("PRON", "pron."),
    "prep": ("ADP", "prep."),
    "conj": ("CCONJ", "conj."),
    "intj": ("INTJ", "interj."),
    "det": ("DET", "det."),
    "freedict": (None, ""),
}

# Skip these POS (they aren't normally looked up as words)
SKIP_POS = {"character", "punct", "symbol", "phrase", "proverb", "abbrev",
            "prefix", "suffix", "infix", "circumfix", "affix", "letter",
            "contraction", "particle", "article"}


def clean_translation(text: str) -> str:
    """Trim, collapse whitespace, drop common parenthetical noise."""
    text = text.strip()
    # remove dangling parenthetical clarifications added by editors that don't
    # contain useful Turkish text (most Turkish translations are clean already)
    if not text:
        return ""
    return text


def get_inflections(word: str, kaikki_pos: str, forms_field: list | None) -> set[str]:
    """Return inflected forms, excluding the headword itself.

    Combines lemminflect output with any 'forms' already listed in the kaikki
    entry (e.g. irregular plurals like 'mice', 'children').
    """
    out: set[str] = set()

    # Forms from the entry itself
    for f in forms_field or []:
        fw = f.get("form")
        if not fw or fw == word:
            continue
        # Skip non-orthographic forms (IPA-only, tagged with weird metadata)
        tags = set(f.get("tags") or [])
        if tags & {"romanization", "transliteration"}:
            continue
        # Skip multi-word forms (Kindle only looks up single tokens)
        if " " in fw or "/" in fw or "-" in fw and len(fw) < 3:
            continue
        out.add(fw)

    # Forms from lemminflect
    upos = POS_MAP.get(kaikki_pos, (None,))[0]
    if upos in ("NOUN", "VERB", "ADJ", "ADV", "PROPN"):
        try:
            tab = getAllInflections(word, upos=upos)
            for forms in tab.values():
                for f in forms:
                    if f and f != word and " " not in f:
                        out.add(f)
        except Exception:
            pass

    return out


def extract_entries(jsonl_path: Path):
    """Stream the JSONL file, yield (word, pos, translations, senses, forms).

    translations: list of dicts {tr: str, sense: str or None}.
    senses: list of strings (English glosses, used for disambiguation).
    """
    n_lines = 0
    n_kept = 0
    with jsonl_path.open() as f:
        for line in f:
            n_lines += 1
            if n_lines % 100_000 == 0:
                print(f"  parsed {n_lines:>8,} lines, kept {n_kept:>6,}",
                      file=sys.stderr)
            try:
                d = json.loads(line)
            except Exception:
                continue

            if d.get("lang_code") != "en":
                continue
            pos = d.get("pos")
            if not pos or pos in SKIP_POS:
                continue
            word = d.get("word")
            if not word or len(word) > 60:
                continue
            # Skip multi-word entries — Kindle popup only looks up single tokens.
            if " " in word or "\t" in word:
                continue

            # Gather Turkish translations (entry-level + per-sense)
            translations: list[dict] = []
            for t in d.get("translations") or []:
                if t.get("code") == "tr" or t.get("lang_code") == "tr":
                    tw = clean_translation(t.get("word") or "")
                    if tw:
                        translations.append({"tr": tw, "sense": t.get("sense")})
            for s in d.get("senses") or []:
                for t in s.get("translations") or []:
                    if t.get("code") == "tr" or t.get("lang_code") == "tr":
                        tw = clean_translation(t.get("word") or "")
                        if tw:
                            translations.append({"tr": tw,
                                                 "sense": (s.get("glosses") or [None])[0]})

            if not translations:
                continue

            senses = []
            for s in d.get("senses") or []:
                g = s.get("glosses") or []
                if g:
                    senses.append(g[0])

            n_kept += 1
            yield {
                "word": word,
                "pos": pos,
                "translations": translations,
                "senses": senses,
                "forms": d.get("forms"),
            }

    print(f"  done: {n_lines:,} lines, {n_kept:,} entries with Turkish",
          file=sys.stderr)


_RE_TAG = re.compile(r"<[^>]+>")
_RE_WORD = re.compile(r"^[A-Za-z][A-Za-z'-]+$")


def parse_freedict_def(html_def: str) -> list[str]:
    """Pull a clean list of Turkish gloss strings out of a FreeDict HTML def.

    The HTML is wrapped in <div>/<ol>/<li>/<div>; we split on </li> to recover
    individual senses and strip remaining tags.
    """
    # Replace </li> with a separator, then strip tags
    s = html_def.replace("</li>", "␟").replace("\\n", " ")
    s = _RE_TAG.sub("", s)
    glosses = []
    for piece in s.split("␟"):
        piece = piece.strip().strip(";,.").strip()
        # Trim "(biyokim.) ... ." style — keep but compact
        piece = re.sub(r"\s+", " ", piece)
        if piece and len(piece) <= 200:
            glosses.append(piece)
    return glosses


def load_freedict() -> dict[str, list[str]]:
    """Return {headword: [turkish glosses]} from the FreeDict tab file."""
    out: dict[str, list[str]] = {}
    if not FREEDICT.exists():
        return out
    with FREEDICT.open() as f:
        for line in f:
            if line.startswith("##") or not line.strip():
                continue
            w, _, defn = line.partition("\t")
            if not _RE_WORD.fullmatch(w):
                continue
            if len(w) > 40:
                continue
            glosses = parse_freedict_def(defn.strip())
            if glosses:
                out[w] = glosses
    return out


def collect():
    """Merge per-POS entries by headword. Returns dict[word] -> list of POS blocks."""
    book: dict[str, list[dict]] = defaultdict(list)
    for e in extract_entries(SRC):
        # Dedupe translations within an entry, preserve order
        seen = set()
        unique_tr = []
        for t in e["translations"]:
            key = t["tr"].lower()
            if key in seen:
                continue
            seen.add(key)
            unique_tr.append(t)
        e["translations"] = unique_tr

        # Compute inflections
        infls = get_inflections(e["word"], e["pos"], e["forms"])
        e["inflections"] = sorted(infls)
        book[e["word"]].append(e)

    # Augment with FreeDict entries (GPLv2+).
    fd = load_freedict()
    n_added = 0
    n_augmented = 0
    for w, glosses in fd.items():
        if w in book:
            # Augment existing entry with FreeDict glosses as an extra POS block
            existing_trs = set()
            for blk in book[w]:
                for t in blk["translations"]:
                    existing_trs.add(t["tr"].lower())
            new_trs = [g for g in glosses if g.lower() not in existing_trs]
            if new_trs:
                book[w].append({
                    "word": w,
                    "pos": "freedict",
                    "translations": [{"tr": g, "sense": None} for g in new_trs],
                    "senses": [],
                    "inflections": sorted(get_inflections(w, "noun", None)),
                    "forms": None,
                })
                n_augmented += 1
        else:
            # Brand new headword — guess POS as noun for inflection lookups
            book[w].append({
                "word": w,
                "pos": "freedict",
                "translations": [{"tr": g, "sense": None} for g in glosses],
                "senses": [],
                "inflections": sorted(get_inflections(w, "noun", None)),
                "forms": None,
            })
            n_added += 1
    print(f"FreeDict: added {n_added} new headwords, augmented {n_augmented}",
          file=sys.stderr)
    return book


def escape(s: str) -> str:
    return html.escape(s, quote=True)


def render_entry(word: str, blocks: list[dict]) -> str:
    """Render one idx:entry block. Layout is intentionally minimal: a single
    flat <p> per POS, no nested lists, no inline styles. Kindle's per-record
    HTML indexer rejects dictionaries with too many mid-tag record splits, and
    nested tags multiply that risk every time an entry straddles a 4 KB record
    boundary.

    Output:
        <idx:entry ...>
        <idx:orth value="run"><b>run</b><idx:infl>...</idx:infl></idx:orth>
        <p><i>v.</i> [to move quickly] koşmak; [of liquids] akmak</p>
        </idx:entry>
        <mbp:pagebreak/>
    """
    all_infls: set[str] = set()
    for b in blocks:
        all_infls.update(b["inflections"])
    all_infls.discard(word)

    iforms = "".join(f'<idx:iform value="{escape(f)}"/>' for f in sorted(all_infls))
    infl_xml = f"<idx:infl>{iforms}</idx:infl>" if iforms else ""

    parts = [
        '<idx:entry name="default" scriptable="yes" spell="yes">',
        f'<idx:orth value="{escape(word)}"><b>{escape(word)}</b>{infl_xml}</idx:orth>',
    ]

    for b in blocks:
        pos_label = POS_MAP.get(b["pos"], (None, b["pos"]))[1]

        # Bucket by sense gloss, then emit a single <p> per POS.
        by_sense: dict[str, list[str]] = {}
        order: list[str] = []
        for t in b["translations"]:
            s = (t.get("sense") or "").strip()
            if s not in by_sense:
                by_sense[s] = []
                order.append(s)
            by_sense[s].append(t["tr"])

        chunks = []
        for s in order:
            trs = ", ".join(escape(x) for x in by_sense[s][:15])
            if s:
                # cap gloss length so entries stay compact
                if len(s) > 100:
                    s = s[:97] + "..."
                chunks.append(f'<i>[{escape(s)}]</i> {trs}')
            else:
                chunks.append(trs)
        body = "; ".join(chunks)

        if pos_label:
            parts.append(f'<p><i>{escape(pos_label)}</i> {body}</p>')
        else:
            parts.append(f'<p>{body}</p>')

    parts.append("</idx:entry>")
    parts.append("<mbp:pagebreak/>")
    return "".join(parts)


HEAD = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns:idx="https://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf"
      xmlns:mbp="https://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
</head>
<body>
<mbp:frameset>
"""

FOOT = """
</mbp:frameset>
</body>
</html>
"""


def write_html(book: dict, chunk_max: int = 6000) -> list[str]:
    """Write content into chunked HTML files (Kindle prefers <2MB chunks)."""
    words = sorted(book.keys(), key=lambda w: (w.lower(), w))
    files = []
    chunk_idx = 0
    chunk_path = None
    f = None
    n_in_chunk = 0
    for w in words:
        if f is None or n_in_chunk >= chunk_max:
            if f is not None:
                f.write(FOOT)
                f.close()
            chunk_idx += 1
            chunk_path = f"content{chunk_idx:03d}.html"
            f = open(OUT_DIR / chunk_path, "w", encoding="utf-8")
            f.write(HEAD)
            files.append(chunk_path)
            n_in_chunk = 0
        f.write(render_entry(w, book[w]))
        f.write("\n")
        n_in_chunk += 1
    if f is not None:
        f.write(FOOT)
        f.close()
    return files


COVER_HTML = """<?xml version="1.0" encoding="utf-8"?>
<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<title>English-Turkish (muratuysal.com)</title></head>
<body>
<h1>English &#x2192; Turkish</h1>
<p>Compiled by Murat Uysal &#x00B7; <a href="https://muratuysal.com">muratuysal.com</a></p>
<p>Source data: English Wiktionary (via kaikki.org Wiktextract) and FreeDict eng-tur v0.3.</p>
<p>Build code MIT-licensed; dictionary content GPL v2.0+ (inherited from FreeDict).</p>
</body></html>
"""

USAGE_HTML = """<?xml version="1.0" encoding="utf-8"?>
<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/></head>
<body>
<h2>Usage</h2>
<p>Set as default English dictionary in Kindle Settings &#x2192; Language &amp; Dictionaries.
Long-press any English word; Turkish translation appears in the popup.</p>
<p>Inflected forms (plurals, conjugations, comparatives) resolve to their headwords automatically.</p>
</body></html>
"""

COPYRIGHT_HTML = """<?xml version="1.0" encoding="utf-8"?>
<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/></head>
<body>
<h2>Credits &amp; Copyright</h2>
<p><b>Compiled by:</b> Murat Uysal &#x00B7; <a href="https://muratuysal.com">muratuysal.com</a></p>
<p>This dictionary was hand-assembled to fill a real gap: there was no working,
   open, free English-to-Turkish Kindle dictionary. It is dedicated to every
   Turkish reader who wants to enjoy English books on a Kindle with one-tap
   translations.</p>
<p>Data sources:</p>
<ul>
  <li><b>English Wiktionary</b> translations, extracted via kaikki.org Wiktextract
      (May 2026 dump). Available under
      <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>
      and the GFDL.</li>
  <li><b>FreeDict eng-tur v0.3</b> (originally gtksozluk2 by Mehmet Ali Vardar).
      Available under the
      <a href="https://www.gnu.org/licenses/gpl-2.0.html">GNU GPL v2.0 or later</a>.</li>
</ul>
<p><b>Licensing:</b> Build code is MIT (&#x00A9; Murat Uysal). The combined
   dictionary content is distributed under the GNU GPL v2.0 or later, inherited
   from FreeDict. CC BY-SA 4.0 is one-way compatible with GPLv3, so the merged
   artifact carries the more restrictive GPL terms.</p>
<p>Source code &amp; rebuild instructions:
   <a href="https://github.com/mybottles/kindle-en-tr-dictionary">github.com/mybottles/kindle-en-tr-dictionary</a></p>
</body></html>
"""


def _write_cover_jpg(path: Path) -> None:
    """Render a simple 1600x2560 JPEG cover with title + attribution.

    Falls back to leaving an existing cover.jpg untouched if Pillow is missing.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        if path.exists():
            return
        raise RuntimeError("Pillow not installed; cannot generate cover.jpg") from None

    img = Image.new("RGB", (1600, 2560), (40, 60, 90))
    d = ImageDraw.Draw(img)
    try:
        font_big = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf", 140)
        font_med = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf", 80)
        font_small = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf", 60)
    except Exception:
        font_big = ImageFont.load_default()
        font_med = ImageFont.load_default()
        font_small = ImageFont.load_default()
    d.text((100, 900),  "English",      fill="white",   font=font_big)
    d.text((100, 1080), "→ Türkçe",  fill="white",   font=font_big)
    d.text((100, 1260), "Dictionary",   fill="white",   font=font_big)
    d.text((100, 1500), "Murat Uysal",  fill="#cccccc", font=font_med)
    d.text((100, 1610), "muratuysal.com", fill="#aaaaaa", font=font_small)
    img.save(path, quality=85)


NCX_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{uuid}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>English-Turkish (muratuysal.com)</text></docTitle>
  <navMap>
    <navPoint id="nav-cover" playOrder="1"><navLabel><text>Cover</text></navLabel><content src="cover.html"/></navPoint>
    <navPoint id="nav-usage" playOrder="2"><navLabel><text>Usage</text></navLabel><content src="usage.html"/></navPoint>
    <navPoint id="nav-copyright" playOrder="3"><navLabel><text>Copyright</text></navLabel><content src="copyright.html"/></navPoint>
{content_nav}
  </navMap>
</ncx>
"""


def write_opf(content_files: list[str]):
    import uuid as _uuid
    book_uuid = str(_uuid.uuid5(_uuid.NAMESPACE_DNS, "kaikki-en-tr-2026-05"))

    manifest_items = [
        '<item id="cover-img" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>',
        '<item id="cover" href="cover.html" media-type="application/xhtml+xml"/>',
        '<item id="usage" href="usage.html" media-type="application/xhtml+xml"/>',
        '<item id="copyright" href="copyright.html" media-type="application/xhtml+xml"/>',
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
    ]
    spine_items = [
        '<itemref idref="cover"/>',
        '<itemref idref="usage"/>',
        '<itemref idref="copyright"/>',
    ]
    nav_lines = []
    for i, cf in enumerate(content_files, 1):
        cid = f"c{i:03d}"
        manifest_items.append(f'<item id="{cid}" href="{cf}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="{cid}"/>')
        nav_lines.append(
            f'    <navPoint id="nav-{cid}" playOrder="{3+i}">'
            f'<navLabel><text>Entries {i}</text></navLabel>'
            f'<content src="{cf}"/></navPoint>'
        )

    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package version="2.0"
         xmlns="http://www.idpf.org/2007/opf"
         xmlns:idx="https://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf"
         unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>English-Turkish (muratuysal.com)</dc:title>
    <dc:creator opf:role="edt" opf:file-as="Uysal, Murat">Murat Uysal</dc:creator>
    <dc:creator opf:role="aut">Wiktionary contributors</dc:creator>
    <dc:creator opf:role="aut">FreeDict eng-tur contributors</dc:creator>
    <dc:contributor opf:role="bkp">Murat Uysal (https://muratuysal.com)</dc:contributor>
    <dc:publisher>Murat Uysal — muratuysal.com</dc:publisher>
    <dc:description>English → Turkish popup dictionary for Kindle. 41,424 headwords with 45,675 inflected forms. Compiled by Murat Uysal from English Wiktionary and FreeDict eng-tur. https://muratuysal.com</dc:description>
    <dc:source>https://github.com/mybottles/kindle-en-tr-dictionary</dc:source>
    <dc:language>en</dc:language>
    <dc:identifier id="BookId" opf:scheme="UUID">{book_uuid}</dc:identifier>
    <dc:rights>Build code: MIT (c) Murat Uysal. Content: GPL v2.0+ (inherited from FreeDict eng-tur).</dc:rights>
    <meta name="cover" content="cover-img"/>
    <x-metadata>
      <DictionaryInLanguage>en</DictionaryInLanguage>
      <DictionaryOutLanguage>tr</DictionaryOutLanguage>
      <DefaultLookupIndex>default</DefaultLookupIndex>
    </x-metadata>
  </metadata>
  <manifest>
    {chr(10).join(manifest_items)}
  </manifest>
  <spine toc="ncx">
    {chr(10).join(spine_items)}
  </spine>
  <guide>
    <reference type="cover" title="Cover" href="cover.html"/>
    <reference type="index" title="Index" href="{content_files[0]}"/>
  </guide>
</package>
"""
    (OUT_DIR / "dict.opf").write_text(opf, encoding="utf-8")
    (OUT_DIR / "cover.html").write_text(COVER_HTML, encoding="utf-8")
    (OUT_DIR / "usage.html").write_text(USAGE_HTML, encoding="utf-8")
    _write_cover_jpg(OUT_DIR / "cover.jpg")
    (OUT_DIR / "copyright.html").write_text(COPYRIGHT_HTML, encoding="utf-8")
    (OUT_DIR / "toc.ncx").write_text(
        NCX_TEMPLATE.format(uuid=book_uuid, content_nav="\n".join(nav_lines)),
        encoding="utf-8",
    )


def main():
    print("Parsing kaikki JSONL...", file=sys.stderr)
    book = collect()
    n_words = len(book)
    n_infl = sum(len(b["inflections"]) for blocks in book.values() for b in blocks)
    n_trans = sum(len(b["translations"]) for blocks in book.values() for b in blocks)
    print(f"\nStats:", file=sys.stderr)
    print(f"  headwords:    {n_words:,}", file=sys.stderr)
    print(f"  translations: {n_trans:,}", file=sys.stderr)
    print(f"  inflections:  {n_infl:,}", file=sys.stderr)

    print("Writing HTML chunks...", file=sys.stderr)
    files = write_html(book)
    print(f"  wrote {len(files)} HTML files", file=sys.stderr)
    print("Writing OPF...", file=sys.stderr)
    write_opf(files)

    print(f"\nDone. Now run: ./kindling build {OUT_DIR}/dict.opf -o english-turkish-dictionary.mobi", file=sys.stderr)


if __name__ == "__main__":
    main()
