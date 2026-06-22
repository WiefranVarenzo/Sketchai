# Sketch.ai V2

Sketch.ai adalah aplikasi web interaktif yang memungkinkan developer dan artist mengubah sketsa tangan kasar (dibuat langsung di *canvas* browser) menjadi aset game 2D siap pakai (*production-ready*) dalam hitungan detik. 

Aplikasi ini menggunakan kekuatan **Google Gemini 2.5 Flash Image AI** dengan *pipeline post-processing* canggih (termasuk *Smart Background Removal* menggunakan model U^2-Net dari `rembg`, *Auto-Crop*, dan *Grid Resizing*) yang dioptimalkan untuk game engine seperti Godot, Phaser, atau Unity.

Fitur unggulan lainnya adalah **Animation Frame Generator**, di mana AI dapat men-generate deretan *frame-by-frame* animasi lengkap (Idle, Walk, Run, dll) atau bahkan gerakan *custom* dari satu gambar statis, lalu mengekspornya langsung menjadi *Sprite Sheet*.

---

## Fitur Utama

- **Live Drawing Canvas:** Menggambar sketsa langsung di browser menggunakan sistem grid.
- **Smart Style Conditioning:** Gaya visual aset (Pixel Art, Flat Vector, Dark Fantasy, dll) akan dikunci per proyek agar tetap konsisten satu sama lain.
- **Smart Background Removal (rembg):** Menghapus latar belakang gambar secara cerdas dan akurat tanpa API eksternal (memanfaatkan pemrosesan AI lokal dengan fallback ke *flood-fill*).
- **Game-Ready Grid Engine:** Hasil AI otomatis di-*crop* dan disesuaikan ke ukuran grid spesifik (misal 64x64px) lengkap dengan padding presisi.
- **Animation Frame Generator:** Menghasilkan urutan animasi (Idle, Walk, Run, dll) lengkap dengan ekspor dalam bentuk *Sprite Strip* dan metadata JSON (*TextureAtlas* format).
- **Advanced Export:** Dukungan untuk menyimpan ke *Local Library*, mengunduh PNG satuan dengan *alpha channel*, atau mengunduh paket ZIP (*Sprite Sheet* + JSON).

---

## 🚀 Cara Instalasi & Menjalankan Aplikasi

Ikuti panduan di bawah ini untuk menjalankan aplikasi secara lokal di komputer Anda.

### 1. Prasyarat (*Prerequisites*)
Pastikan Anda sudah menginstal:
- **Python 3.10** atau lebih baru
- **Git**
- *API Key* dari [Google AI Studio](https://aistudio.google.com/)

### 2. Kloning Repository
Buka terminal/command prompt dan jalankan:
```bash
git clone https://github.com/WiefranVarenzo/Sketchai.git
cd Sketchai
```

### 3. Setup Virtual Environment (Sangat Disarankan)
Untuk mengisolasi *dependency* project ini dari sistem Anda, buat dan aktifkan *virtual environment*:

**Untuk pengguna Linux / macOS:**
```bash
python3 -m venv myenv
source myenv/bin/activate
```

**Untuk pengguna Windows (Command Prompt/PowerShell):**
```cmd
python -m venv myenv
myenv\Scripts\activate
```

### 4. Install Dependencies
Dengan *virtual environment* yang sudah aktif, instal semua *library* yang dibutuhkan:
```bash
pip install -r requirements.txt
```
*(Catatan: Proses ini juga akan menginstal `rembg`. Jika aplikasi dijalankan untuk pertama kali, ia akan men-download file model U^2-Net sebesar ~176MB secara otomatis).*

### 5. Setup Environment Variables (.env)
Aplikasi membutuhkan kunci API Gemini untuk berfungsi.
1. Salin (copy) file `.env.example` menjadi `.env`.
   ```bash
   cp .env.example .env
   ```
2. Buka file `.env` di text editor pilihan Anda.
3. Masukkan API Key Anda:
   ```env
   GEMINI_API_KEY=KODE_API_ANDA_DI_SINI
   ```

### 6. Jalankan Server FastAPI
Jalankan perintah ini untuk menyalakan server:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 7. Akses Aplikasi
Buka web browser favorit Anda (Google Chrome direkomendasikan) dan kunjungi: **http://127.0.0.1:8000**

---

## 🛠️ Tips & Troubleshooting

- **Server tidak bisa dinyalakan?** Pastikan *virtual environment* Anda aktif (biasanya ada teks `(myenv)` di awal baris terminal).
- **Error API Key?** Pastikan Anda telah mengedit file `.env` dengan format yang benar tanpa tanda kutip di sekitar kuncinya.
- **Ingin mencoba Custom Animation?** Klik tombol "🎬 Generate Animation Frames", pilih opsi "Custom" di bagian bawah, dan ketik instruksi animasi Anda (contoh: *"karakter melakukan sihir bola api"*).

---
*Dibuat untuk memenuhi proyek Sistem Multimedia dan Eksplorasi Generative AI.*
