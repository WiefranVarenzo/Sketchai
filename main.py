from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types

from config import CORS_ORIGINS, GEMINI_API_KEY, GEMINI_MODEL
from utils import decode_base64_image, encode_image_to_data_url

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

client = genai.Client(api_key=GEMINI_API_KEY)


class SketchRequest(BaseModel):
    image: str  # Base64 data-URL from the canvas
    prompt: str


@app.post("/api/generate-from-sketch")
async def generate_ai_image(request: SketchRequest):
    try:
        image_bytes = decode_base64_image(request.image)

        sketch_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                sketch_part,
                (
                    "Transform this rough sketch into a high-quality, "
                    "production-ready image. Adhere to the sketch's layout. "
                    f"User instruction: {request.prompt}"
                ),
            ],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )

        generated_bytes = response.candidates[0].content.parts[0].inline_data.data
        generated_data_url = encode_image_to_data_url(generated_bytes, "image/jpeg")

        return {"status": "success", "generated_image": generated_data_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
