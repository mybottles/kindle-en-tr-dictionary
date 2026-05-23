# Kindle için İngilizce → Türkçe Sözlük

**Kindle'da İngilizce kitap okurken kelimeye uzun basınca Türkçe karşılığı çıksın.**

[![GitHub stars](https://img.shields.io/github/stars/mybottles/kindle-en-tr-dictionary?style=social)](https://github.com/mybottles/kindle-en-tr-dictionary/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/mybottles/kindle-en-tr-dictionary?style=social)](https://github.com/mybottles/kindle-en-tr-dictionary/network/members)
[![License: GPL v2+](https://img.shields.io/badge/License-GPL%20v2%2B-blue.svg)](https://www.gnu.org/licenses/gpl-2.0)
[![Kindle](https://img.shields.io/badge/Kindle-Paperwhite%2012-orange)](https://github.com/mybottles/kindle-en-tr-dictionary)

> _**English version:** [README.en.md](README.en.md)_

**41.424 kelime · 152.097 çeviri · 45.675 çekim formu** &nbsp;·&nbsp; CC BY-SA + GPL kaynaklarından derlendi.

İndirin → Kindle'a kopyalayın → varsayılan sözlük seçin → okumaya başlayın.

---

## Bu sözlük neden var?

Aylar boyu aradım — **Kindle'a kurulabilen, gerçekten çalışan, ücretsiz bir İngilizce-Türkçe sözlük yoktu.**

- Amazon Store'daki ücretli sözlükler ya yok ya çok pahalı
- Webde dolaşan eski `.mobi` dosyaları ya bozuk, ya yeni Kindle'larda lookup yapmıyor, ya da çekim ("ran", "running", "books", "better") tanımıyor
- Calibre / pyglossary üretimleri Kindle Paperwhite 12 firmware'inde "no definition found" hatası veriyor (eksik `infl_index`/`names_index` MOBI bölümleri)

Bu boşluğu doldurmak için yaptım. Açık kaynak, açık veri, açık lisans. C1 seviyesinde İngilizce bilim/akademi kitapları okuyanları, dil öğrenenleri, Nick Lane / Sapolsky / Pinker gibi yazarları Türkçe sözlük yardımıyla rahat okumak isteyen herkesi düşünerek hazırlandı.

İhtiyacı olan herkese armağan olsun.

---

## Hızlı kurulum

1. [Releases](../../releases/latest) sayfasından **`english-turkish-dictionary.mobi`** dosyasını indir
2. Kindle'ı USB ile bilgisayara bağla, `documents/` klasörüne kopyala (veya Send-to-Kindle uygulamasıyla gönder)
3. Kindle'da: **Settings → Language & Dictionaries → Dictionaries → English →** *English-Turkish (muratuysal.com)* seç
4. İngilizce bir kitap aç. Bir kelimeye uzun bas. Türkçe karşılığı popup'ta görünecek.

> "ran" → "run" girdisi; "running" → "run"; "mice" → "mouse"; "better" → "good".
> Çekim eşleştirmesi 45.675 form için yapılmış.

---

## Neler içeriyor

| | |
|---|---|
| **Headword** (kök kelime) | 41.424 |
| **Türkçe çeviri** | 152.097 (kelime başına ort. 3,7) |
| **Çekim formu** (`<idx:infl>`) | 45.675 |
| **Dosya boyutu** | 5.5 MB |
| **Kaynak** | English Wiktionary + FreeDict eng-tur |
| **Popup başlığı** | English-Turkish (muratuysal.com) |

### Kapsam örneği

Bilim/akademi terimleri (C1+ okuyucular için kritik):

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

Günlük kelimeler:

```
run     v.  koşmak; akmak; yönetmek; çalıştırmak
book    n.  kitap;  v. yer ayırtmak
better  →   "good" girdisine yönlenir
```

---

## Veri kaynakları

| Kaynak | Lisans | Headword | Rolü |
|---|---|---|---|
| [kaikki.org Wiktextract](https://kaikki.org/dictionary/English/) (English Wiktionary, May 2026) | CC BY-SA 4.0 + GFDL | 19.384 | Birincil — sense disambiguator + İngilizce gloss |
| [FreeDict eng-tur v0.3](https://download.freedict.org/dictionaries/eng-tur/0.3/) | GPL v2.0+ | 22.040 yeni + 10.358 augment | İkincil — kapsamı genişletir |

**Lisans:** Birleştirilmiş `.mobi` artifact'i **GPL v2.0+** altında dağıtılır (CC BY-SA 4.0 tek yönlü olarak GPLv3 ile uyumludur, FreeDict'in GPL'i baskındır). Build script'i ([`build.py`](build.py)) ise **MIT** lisansıyla.

---

## Sıfırdan derlemek

Releases'tan indirebilirsin — ama kendin derlemek istersen:

### Gereksinimler

- Python 3.11+
- macOS Apple Silicon için **Rosetta 2** (`softwareupdate --install-rosetta --agree-to-license`)
- Amazon kindlegen 2.9 (x86_64 Mac binary — [arşivde mevcut](https://github.com/andyljones/kindlegen-64))
- ~3 GB boş disk alanı (kaikki dump'ı için)

### Adımlar

```bash
git clone https://github.com/mybottles/kindle-en-tr-dictionary
cd kindle-en-tr-dictionary

# Python ortamı
python3 -m venv .venv
.venv/bin/pip install pyglossary lemminflect Pillow

# Kaikki English Wiktextract dump'ı indir (2.8 GB)
curl -L -o kaikki-en.jsonl \
  https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl

# FreeDict eng-tur indir + tab'a dönüştür
curl -L -o freedict.tar.xz \
  https://download.freedict.org/dictionaries/eng-tur/0.3/freedict-eng-tur-0.3.stardict.tar.xz
mkdir -p freedict && tar -xJf freedict.tar.xz -C freedict
.venv/bin/pyglossary --read-format=Stardict --write-format=Tabfile \
  freedict/*/eng-tur.ifo freedict-eng-tur.tab

# kindlegen indir
curl -L -o kindlegen \
  https://github.com/andyljones/kindlegen-64/raw/master/kindlegen
chmod +x kindlegen

# OPF + HTML üret
.venv/bin/python build.py

# MOBI derle (Rosetta üzerinden)
cd dict-src && arch -x86_64 ../kindlegen dict.opf -c1 -dont_append_source
cp dict.mobi ../english-turkish-dictionary.mobi
```

Toplam süre: yaklaşık 4-5 dakika (download süresi hariç).

### Neden `-c1` ve neden kindlegen?

- **kindlegen (`-c1`)**: ayrı `infl_index` ve `names_index` records üretir. Kindle Paperwhite 12 firmware 5.19+ bunlar olmadan dictionary lookup yapmıyor (silent "no definition found"). `-c2` (huffdic compression) Apple Silicon + Rosetta kombinasyonunda 41k entry'de SIGSEGV veriyor — bu bilinen bir kindlegen bug'ı.
- **kindling (Rust, arm64 native, hızlı) denedik**: çıktısı yapısal olarak kindlegen'e benziyor ama `infl_index`/`names_index` records'ları üretmiyor (tüm lookup'ları orth INDX'e gömüyor). Bu yaklaşım eski Kindle'larda çalışıyor ama Paperwhite 12'de çalışmıyor.

Detaylı teknik notlar için: [`CLAUDE.md`](CLAUDE.md).

---

## Bilinen sınırlamalar

- **Tek kelime arama**: Kindle popup'ı sadece tek kelime seçer. "in spite of" gibi çoklu ifadeler bu sözlükte yok (zaten Kindle altyapısı izin vermiyor).
- **Wiktionary boşlukları**: Bazı teknik/güncel kelimeler Wiktionary'de Türkçe karşılıksız (örn. `mitochondria` çekim formu olarak alınır → headword `mitochondrion`).
- **Bağlam yok**: Çeviriler genellikle tek kelime. Karmaşık deyimler için ek bir sözlüğe ihtiyaç olur.
- **Wiktionary'nin tutarsız kalitesi**: Bazı çeviriler dialect/argo (örn. "lügat", "ışılbireşim"). Kullanışlı çoğu giriş ilk sırada.

---

## Katkıda bulunmak

Pull request'ler memnuniyetle karşılanır. Özellikle:

- **Daha iyi sense disambiguator'lar** — şu an İngilizce gloss göstereyim, ideal olan Türkçe gloss olurdu
- **Yeni veri kaynakları** — Apertium, Wikidata lexemes, vs.
- **HTML rendering iyileştirmeleri** — popup'ta daha okunaklı format
- **Bug report'lar** — kelime X için yanlış/eksik çeviri varsa Issue açın

---

## Geliştirici

**Murat Uysal** &nbsp;·&nbsp; [muratuysal.com](https://muratuysal.com)

Açık veriden açık çıktıya — Kindle'da Türkçe kitap okumak isteyenlere armağandır.

---

## Lisans

- **Build kodu** (`build.py`): MIT — bkz. [`LICENSE`](LICENSE)
- **Dictionary içeriği** (`english-turkish-dictionary.mobi`): GPL v2.0+ (kaynak verilerden miras)

## Teşekkür

- Tatu Ylönen ve [Wiktextract](https://github.com/tatuylonen/wiktextract) ekibi — kaikki.org dump'ı için
- Mehmet Ali Vardar — orijinal gtksozluk2 (FreeDict eng-tur'un kaynağı) için
- English Wiktionary'ye bilim/teknik çeviri katkısı yapan binlerce gönüllü editör
- [Amazon kindlegen](https://kdp.amazon.com/) — 2015'te bırakılmış olsa da hâlâ tek güvenilir Kindle dictionary builder
