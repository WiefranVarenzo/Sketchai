from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # <-- PASTIKAN BARIS INI ADA
from pydantic import BaseModel
from google import genai
from google.genai import types
import base64
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# --- TAMBAHKAN BLOK CORS INI ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Mengizinkan semua origin (untuk development)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Inisialisasi Client AI Studio
# API Key sekarang diambil dari file .env untuk keamanan
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY tidak ditemukan. Pastikan file .env sudah diisi sesuai .env.example")

client = genai.Client(api_key=api_key)

# Struktur data dari frontend
class SketchRequest(BaseModel):
    image: str  # Format Base64 dari canvas
    prompt: str # Instruksi tambahan, misal: "make it 3D, realistic lighting"

@app.post("/api/generate-from-sketch")
async def generate_ai_image(request: SketchRequest):
    try:
        # 1. Bersihkan header Base64 dari frontend (data:image/png;base64,...)
        if "," in request.image:
            clean_base64 = request.image.split(",")[1]
        else:
            clean_base64 = request.image
            
        image_bytes = base64.b64decode(clean_base64)
        
        # 2. Siapkan objek "Part" gambar untuk SDK Gemini
        sketch_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png"
        )
        
        # 3. Panggil model Gemini Image (Nano Banana 2 / Flash Image)
        # Model ini menerima gambar sketsa dan teks secara bersamaan
        response = client.models.generate_content(
            model='gemini-3.1-flash-image-preview',
            contents=[
                sketch_part,
                f"Transform this rough sketch into a high-quality, production-ready image. Adhere to the sketch's layout. User instruction: {request.prompt}"
            ],
            config=types.GenerateContentConfig(
                # Pastikan AI mengembalikan format gambar, bukan teks
                response_modalities=["IMAGE"],
            )
        )
        
        # 4. Ekstrak hasil gambar dari response (dikembalikan dalam bentuk bytes oleh SDK)
        # Lalu ubah kembali ke Base64 agar mudah ditampilkan di frontend
        generated_bytes = response.candidates[0].content.parts[0].inline_data.data
        generated_base64 = base64.b64encode(generated_bytes).decode('utf-8')
        
        return {
            "status": "success",
            "generated_image": f"data:image/jpeg;base64,{generated_base64}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))