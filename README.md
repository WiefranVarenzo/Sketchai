# Sketch.ai - AI Sketch to Image

Sketch.ai adalah proyek web sederhana yang dapat mengubah gambar sketsa kasar yang kamu buat di kanvas menjadi gambar berkualitas tinggi dan siap produksi. Aplikasi ini menggunakan model **Google Gemini (GenAI)** untuk memproses sketsa dan *prompt* (instruksi teks) yang kamu berikan.

---

## 🚀 Fitur
- **Kanvas Menggambar**: Gambar sketsa langsung di browser.
- **Kustomisasi**: Atur warna dan ukuran kuas (brush) sesukamu.
- **AI Generation**: Integrasi dengan API Google GenAI untuk mengubah sketsamu menjadi gambar *super realistic* atau gaya apapun sesuai prompt yang kamu tulis.

---

## 🛠️ Persiapan dan Instalasi (Untuk Fork / Clone)

Jika kamu ingin melakukan *fork* atau menjalankan proyek ini di komputermu sendiri, ikuti langkah-langkah mudah berikut:

### 1. Clone Repository
Pertama, clone repository ini ke komputer lokal kamu:
```bash
git clone https://github.com/WiefranVarenzo/Sketchai.git
cd Sketchai
```

### 2. Buat Virtual Environment
Dianjurkan untuk menggunakan *virtual environment* agar library yang di-install tidak bentrok dengan proyek Python kamu yang lain.

**Di Windows:**
```bash
python -m venv myenv
myenv\Scripts\activate
```

**Di Mac/Linux:**
```bash
python3 -m venv myenv
source myenv/bin/activate
```

### 3. Install Library yang Dibutuhkan
Setelah environment (`myenv`) aktif (biasanya ditandai dengan tulisan `(myenv)` di terminal), install semua *library* (dependencies) yang dibutuhkan menggunakan file `requirements.txt`:

```bash
pip install -r requirements.txt
```
*Note: Ini akan menginstal framework seperti FastAPI, Uvicorn, dan library Google GenAI secara otomatis.*

### 4. Konfigurasi API Key (.env)
Agar aman, API Key tidak disimpan langsung di dalam kode. 
1. Buat file baru bernama `.env` di _root_ proyek (selevel dengan `main.py`).
2. Kamu bisa melihat contoh formatnya di file `.env.example`.
3. Isi `.env` dengan Google Gemini API Key milikmu:
```env
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxx
```

---

## ▶️ Cara Menjalankan Aplikasi

Aplikasi ini terdiri dari dua bagian: **Backend** (API Python) dan **Frontend** (HTML sederhana).

### Menjalankan Backend (FastAPI)
Pastikan kamu masih berada di dalam terminal dengan `myenv` yang aktif. Jalankan perintah berikut:

```bash
uvicorn main:app --reload
```
Akan muncul keterangan bahwa server berjalan di `http://127.0.0.1:8000`. Biarkan terminal ini tetap terbuka.

### Menjalankan Frontend (Web)
Cukup buka file `index.html` menggunakan browser favoritmu (Chrome, Firefox, Safari, dll).
1. Gambar sketsa di kanvas yang tersedia.
2. Masukkan instruksi (*prompt*) di kolom teks (contoh: "make it a realistic cyberpunk city").
3. Klik tombol **Generate AI Image**.
4. Tunggu beberapa detik, dan gambar hasil AI akan muncul!

---

## ⚠️ Catatan Penting
- **API Key**: Proyek ini membutuhkan API Key dari Google AI Studio. Pastikan kamu sudah menaruh API Key milikmu ke dalam file `.env` (lihat langkah 4). Karena kita sudah menggunakan `.env`, kodenya jauh lebih aman dan API Key-mu tidak akan bocor ke GitHub.
