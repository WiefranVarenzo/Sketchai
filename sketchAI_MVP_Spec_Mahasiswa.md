# sketchAI — MVP Spec (Versi Mahasiswa, 100% Free Tier)
### AI-Powered 2D Game Asset Generator menggunakan Gemini 2.5 Flash Image (Nano Banana)

> Dokumen ini dirancang untuk dua fungsi: (1) sebagai blueprint teknis proyek, dan (2) sebagai **prompt langsung** yang bisa di-paste ke Claude Code / AI coding assistant lain untuk mulai membangun aplikasinya.

---

## 1. RINGKASAN PROYEK

**Nama Produk:** sketchAI (MVP)

**One-liner:** Web app yang mengubah sketsa kasar menjadi asset game 2D yang **benar-benar siap pakai** (bukan cuma gambar AI) — lengkap dengan background transparan, ukuran standar game, dan format export yang langsung bisa di-import ke game engine.

**Masalah yang diselesaikan:** Indie developer / mahasiswa yang bisa coding tapi tidak bisa menggambar, sehingga game mereka tidak pernah selesai karena terhambat di bagian art asset.

**Diferensiasi utama dari sekadar "image generator":**
Output AI **tidak berhenti di gambar**. Ada pipeline pemrosesan lanjutan yang mengubah hasil generate menjadi *game-ready asset*:
- Background otomatis transparan (alpha channel bersih, bukan putih)
- Ukuran dipaksa ke standar grid game (misal 32x32, 64x64, 128x128 px)
- Bisa di-export sebagai sprite sheet + metadata JSON (siap import ke engine)
- Konsistensi style dijaga lewat strategi prompting terstruktur (bukan LoRA training, tapi tetap terkontrol)

---

## 2. DEFINISI "USABLE" (Kriteria Wajib Lulus)

Sebuah asset hasil generate dianggap **gagal** kalau tidak memenuhi semua ini:

1. ✅ Background transparan (PNG dengan alpha channel, tidak ada residu warna solid di pinggir)
2. ✅ Ukuran final sesuai grid yang dipilih user (16x16 / 32x32 / 64x64 / 128x128 / 256x256 px), bukan ukuran random dari AI
3. ✅ Subjek berada di tengah canvas dengan padding konsisten (supaya pas kalau dipasang grid di game)
4. ✅ Bisa diunduh langsung dalam format yang dikenali game engine (PNG individual + opsi sprite sheet)
5. ✅ Kalau digenerate beberapa varian dari sketsa yang sama, gaya visual (outline, shading, palet warna) harus terlihat konsisten satu set

Pipeline post-processing-lah yang menjamin poin 1–4. Poin 5 dijamin lewat prompt engineering (lihat bagian 6).

---

## 3. TECH STACK (Semua Free Tier, Tanpa Biaya)

| Layer | Tools | Alasan |
|---|---|---|
| AI Generation | **Gemini 2.5 Flash Image (nano-banana)** via Google AI Studio API | Free tier tersedia, image-to-image bagus untuk sketch-to-asset, native image editing |
| Frontend | **Next.js (React) + Tailwind CSS** | Standar modern, deploy gratis |
| Canvas/Drawing | **Fabric.js** atau **Konva.js** (pilih salah satu, jangan dua-duanya) | Untuk kanvas gambar sketsa di browser |
| Background Removal | **rembg (Python, open source, jalan lokal/serverless)** atau model `@imgly/background-removal` (jalan di browser, client-side, gratis & tanpa API key) | Gemini kadang tidak hasilkan background bersih 100%, perlu post-process |
| Image Processing | **Sharp.js** (Node) atau **Pillow (Python)** | Resize, crop ke grid, padding, generate sprite sheet |
| Auth | **Firebase Authentication (Free Spark Plan)** | Gratis sampai batas wajar untuk MVP |
| Storage | **Firebase Storage (Free Spark Plan, 5GB)** | Simpan sketsa & hasil asset |
| Database | **Firebase Firestore (Free Spark Plan)** | Metadata project, asset, user |
| Hosting | **Vercel (Hobby/Free Plan)** | Auto-deploy Next.js gratis |
| Engine Demo Target | **Godot Engine** (open source, gratis, import PNG paling sederhana) atau **Phaser.js** (kalau mau demo langsung di browser tanpa install apapun) | Bukti bahwa asset benar-benar usable di game engine sungguhan |

**Total biaya: Rp 0** — semua dalam batas free tier selama skala MVP/demo/skripsi.

---

## 4. CORE USER FLOW (3 Langkah + 1 Langkah Tersembunyi)

```
1. GAMBAR SKETSA  →  2. PILIH STYLE  →  3. GENERATE  →  [4. AUTO POST-PROCESS] → ASSET SIAP PAKAI
```

Langkah 4 **tidak terlihat user**, tapi inilah yang membedakan sketchAI dari "tempel prompt ke Gemini biasa":

1. User gambar sketsa kasar di canvas (mouse/trackpad, upload PNG/JPG juga didukung)
2. User pilih: (a) art style preset, (b) tipe asset (karakter / item / environment / tile), (c) ukuran target grid
3. Sistem kirim sketsa + structured prompt ke Gemini 2.5 Flash Image API
4. Hasil generate AI masuk pipeline otomatis:
   - Background removal
   - Crop & resize ke grid yang dipilih
   - Centering + padding konsisten
   - (Opsional) generate varian warna/kondisi dari hasil yang sama
5. Asset masuk ke Asset Library, siap di-export

---

## 5. MODUL APLIKASI (Scope MVP — Hanya yang Esensial)

### Modul A — Sketch Canvas
- Kanvas gambar dasar: pen, eraser, undo/redo, clear, ukuran brush
- Upload sketsa dari file (PNG/JPG)
- Preview sebelum generate

### Modul B — AI Generation Engine
- Pemilihan art style preset (minimal 4–5 pilihan: misal *Pixel Fantasy, Cartoon Casual, Dark Dungeon, Flat Vector*)
- Pemilihan tipe asset (Character / Item / Environment / Tile) — ini mempengaruhi struktur prompt
- Pemilihan ukuran target (16/32/64/128/256 px)
- Panggil Gemini 2.5 Flash Image API dengan structured prompt (lihat bagian 6)
- Tombol "Generate Variasi" (warna/kondisi berbeda dari hasil yang sudah ada, pakai image-to-image dari hasil sebelumnya supaya style tetap nyambung)

### Modul C — Asset Processing Pipeline (Modul paling kritis — INI yang bikin "beneran usable")
- Background removal otomatis
- Auto-crop ke bounding box subjek
- Resize & padding ke grid standar yang dipilih user
- Penamaan file otomatis (rapi, bisa langsung dipakai: `character_knight_idle_32x32.png`)

### Modul D — Asset Library
- Grid view semua asset yang sudah dibuat per project
- Tagging sederhana (karakter/item/environment/tile)
- Preview ukuran asli (1:1 pixel) supaya user lihat hasil real di ukuran game

### Modul E — Export
- Download single PNG (transparent)
- Download sebagai **Sprite Sheet** (gabungan beberapa asset jadi satu PNG + file JSON metadata posisi tiap sprite — format kompatibel dengan Godot `AtlasTexture` / Phaser `TextureAtlas` / Unity sprite slicing)
- (Bonus kalau waktu cukup) tombol "Test di Godot/Phaser" — preview langsung asset terpasang di scene demo sederhana, untuk membuktikan ke penguji/dosen bahwa hasilnya beneran jalan

> ❌ **TIDAK PERLU di MVP:** payment gateway, multi-tier subscription, mobile app, community sharing, admin dashboard analytics kompleks, CDN, LoRA training custom, real-time WebSocket queue. Semua ini boleh disebut di laporan sebagai "future development", tapi tidak usah dibangun.

---

## 6. STRATEGI PROMPT ENGINEERING (Pengganti LoRA/ControlNet untuk Konsistensi Style)

Karena tidak training model sendiri, konsistensi gaya visual dijaga lewat **structured prompt template** yang konsisten setiap generate dalam satu project:

```
Template dasar:
"Convert this rough sketch into a clean 2D game asset.
Style: {style_preset_description}.
Asset type: {asset_type}.
Requirements:
- Transparent background
- Flat clean outline, no background scenery, no shadow on ground
- Centered composition with even padding
- Consistent art direction: {locked_style_descriptor}
- Resolution intent: optimized for {target_size}px game sprite
Do not add extra elements not present in the sketch."
```

- `{locked_style_descriptor}` di-generate sekali di awal project (misal hasil dari prompt pertama dijadikan acuan kata kunci: "thick black outline, pastel palette, soft cel-shading") dan **dikunci** dipakai ulang di semua generate berikutnya dalam project yang sama → ini simulasi sederhana dari "style locking" tanpa perlu training model.
- Untuk generate variasi, gunakan mode **image-to-image**: kirim ulang asset yang sudah jadi sebagai reference image + instruksi perubahan spesifik ("ubah warna jadi musim gugur", "buat versi rusak/retak") — bukan generate dari nol, supaya style tetap konsisten.

---

## 7. ALUR TEKNIS (Architecture Singkat)

```
[Browser: Next.js + Fabric.js Canvas]
        ↓ (sketsa base64 + parameter style/size)
[API Route Next.js / Backend Function]
        ↓
[Gemini 2.5 Flash Image API] → hasil gambar mentah
        ↓
[Post-Processing Pipeline]
   ├─ Background removal (rembg / @imgly/background-removal)
   ├─ Auto-crop bounding box
   ├─ Resize + padding ke grid (Sharp.js / Pillow)
   └─ Generate filename + metadata
        ↓
[Firebase Storage] (simpan PNG final)
[Firebase Firestore] (simpan metadata: nama, tag, ukuran, project_id, style_locked_descriptor)
        ↓
[Asset Library UI] → [Export: single PNG / Sprite Sheet + JSON]
```

---

## 8. DATA MODEL SEDERHANA (Firestore)

```
projects/
  {projectId}
    - name
    - styleLockedDescriptor (string, dikunci di awal project)
    - createdAt

assets/
  {assetId}
    - projectId (ref)
    - name
    - type (character | item | environment | tile)
    - sizePx (32 | 64 | 128 | ...)
    - originalSketchURL
    - rawGeneratedURL
    - finalProcessedURL (yang sudah transparan + resized — INI yang didownload user)
    - createdAt

users/
  {userId}
    - email
    - projects (array of projectId)
```

---

## 9. BATASAN FREE TIER & CARA MENGAKALI

| Batasan | Mitigasi |
|---|---|
| Rate limit Gemini API free tier | Tambahkan queue sederhana di frontend (disable tombol generate beberapa detik), jangan demo ke banyak orang bersamaan |
| Firebase Spark Plan storage 5GB | Cukup untuk ratusan asset kecil; compress PNG sebelum simpan |
| Konsistensi style tidak setajam model yang di-training khusus (SD+ControlNet+LoRA) | Disebutkan terbuka di laporan sebagai **limitation yang disadari**, bukan disembunyikan — justru jadi bahan diskusi "future work" yang kuat secara akademis |
| Tidak ada GPU compute sendiri | Tidak perlu — semua inference image generation dilakukan di sisi Google (API), bukan komputer mahasiswa |

---

## 10. MVP FEATURE SCOPE — IN vs OUT

**✅ HARUS ADA (Core MVP):**
- Canvas sketsa + upload
- Pilih style preset + asset type + ukuran target
- Generate via Gemini API
- Pipeline post-processing (transparent bg + resize grid) — **non-negotiable, ini esensi produk**
- Asset library per project
- Export PNG transparan
- Export sprite sheet + JSON (minimal 1 format engine, sarankan Godot/Phaser)

**🟡 BAGUS KALAU ADA WAKTU (Nice to have):**
- Generate variasi otomatis dari asset yang sudah ada
- Preview live asset terpasang di mini demo scene (Phaser canvas kecil di halaman web)
- Version history sederhana per asset

**❌ TIDAK PERLU (Out of scope MVP):**
- Mobile app
- Payment/subscription
- Multi-role admin & analytics dashboard
- Komunitas/sharing publik
- Model training custom (LoRA dari nol)

---

## 11. BLOK PROMPT SIAP PAKAI (Untuk Mulai Coding ke AI Assistant Lain)

> Bagian ini bisa langsung di-copy-paste sebagai instruksi awal ke Claude Code / AI coding assistant untuk mulai membangun aplikasinya.

```
Bangun aplikasi web MVP bernama "sketchAI" dengan spesifikasi berikut:

TUJUAN: Web app yang mengubah sketsa gambar menjadi asset game 2D yang benar-benar
siap pakai di game engine — bukan sekadar generate gambar AI biasa.

STACK:
- Next.js + React + Tailwind CSS (frontend, deploy ke Vercel free tier)
- Fabric.js untuk canvas menggambar sketsa
- Gemini 2.5 Flash Image API (Google AI Studio) untuk image generation, mode image-to-image
- Sharp.js untuk post-processing gambar (resize, crop, padding)
- @imgly/background-removal (client-side, gratis, tanpa API key) untuk hapus background
- Firebase (Spark free plan): Auth, Firestore, Storage

FLOW UTAMA:
1. User gambar sketsa di canvas atau upload gambar
2. User pilih: style preset (Pixel Fantasy/Cartoon Casual/Dark Dungeon/Flat Vector),
   tipe asset (Character/Item/Environment/Tile), ukuran target (32/64/128/256 px)
3. Sistem kirim sketsa ke Gemini API dengan structured prompt yang mengunci style
   descriptor per-project agar konsisten antar generate
4. Hasil generate WAJIB melalui pipeline post-processing otomatis:
   - Hapus background jadi transparan
   - Crop ke bounding box subjek
   - Resize + center + padding ke ukuran grid yang dipilih
5. Asset final disimpan ke Asset Library (grid view per project) di Firestore + Storage
6. User bisa export: single PNG transparan, ATAU sprite sheet gabungan + file JSON
   metadata posisi (format kompatibel Godot AtlasTexture / Phaser TextureAtlas)

KRITERIA WAJIB (jangan dilewatkan):
- Output akhir HARUS transparent PNG, bukan background putih/solid
- Output akhir HARUS berukuran pas sesuai grid yang dipilih, bukan ukuran asli dari AI
- Beberapa asset dalam satu project harus terlihat konsisten gaya visualnya
- Sediakan fitur export sprite sheet + JSON, bukan cuma PNG satuan

BATASAN:
- Web only, tidak perlu mobile
- Semua tools harus gratis/free tier, tidak ada budget berbayar
- Tidak perlu payment gateway, tidak perlu multi-role admin dashboard
- Fokus MVP: functional end-to-end demo, bukan production-scale app

Mulai dengan struktur project Next.js, lalu bangun komponen canvas, lalu integrasi
Gemini API, lalu pipeline post-processing, baru terakhir Asset Library dan Export.
```

---

## 12. SARAN PRESENTASI UNTUK DOSEN/PENILAI

Posisikan project ini sebagai **proof-of-concept riset penerapan generative AI untuk game asset pipeline**, bukan klaim produk siap produksi. Poin penjualan utama:

1. Bukan sekadar "tempel prompt ke AI" — ada pipeline rekayasa nyata (post-processing) yang membuat output benar-benar *production-ready*
2. Strategi mengatasi limitasi free-tier API dengan structured prompting sebagai pengganti training model custom
3. Validasi langsung: asset hasil generate diuji benar bisa diimport dan dipakai di game engine sungguhan (Godot/Phaser), bukan klaim kosong
