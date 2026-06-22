from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
import base64
import os
import io
import json
import zipfile
from PIL import Image
import re
from dotenv import load_dotenv

# rembg: AI-based background removal (optional, jauh lebih akurat dari flood-fill)
# Install: pip install rembg
try:
    from rembg import remove as rembg_remove
    REMBG_AVAILABLE = True
    print("✅ rembg tersedia — akan digunakan sebagai primary BG removal")
except ImportError:
    REMBG_AVAILABLE = False
    print("⚠️  rembg tidak tersedia — menggunakan flood-fill fallback")

load_dotenv()

app = FastAPI(title="sketchAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend
app.mount("/static", StaticFiles(directory="."), name="static")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY tidak ditemukan. Pastikan file .env sudah diisi.")

client = genai.Client(api_key=api_key)

# ============================================================
# STYLE PRESETS — Pengganti LoRA, dikunci per-project
# ============================================================
STYLE_PRESETS = {
    "pixel_fantasy": {
        "name": "Pixel Fantasy",
        "description": "pixel art style, 16-bit RPG aesthetic, clear pixel edges, limited color palette, no anti-aliasing, sharp pixel boundaries, fantasy game sprite",
        "locked_descriptor": "thick black pixel outline, fantasy RPG palette, hard pixel edges, no gradients",
    },
    "cartoon_casual": {
        "name": "Cartoon Casual",
        "description": "cartoon style, thick clean black outlines, flat cell-shaded colors, cute and playful, mobile game aesthetic",
        "locked_descriptor": "thick black outline 3px, pastel saturated colors, flat cel-shading, no texture",
    },
    "dark_dungeon": {
        "name": "Dark Dungeon",
        "description": "dark fantasy style, gritty texture, deep shadows, muted dark color palette, gothic game aesthetic, dramatic lighting",
        "locked_descriptor": "dark muted tones, heavy shadow, rough texture, gothic silhouette",
    },
    "flat_vector": {
        "name": "Flat Vector",
        "description": "flat design vector style, minimal shadows, geometric shapes, clean modern colors, UI-friendly game icon aesthetic",
        "locked_descriptor": "flat design, geometric shapes, minimal shadow, clean color blocks, vector clean",
    },
    "chibi_anime": {
        "name": "Chibi Anime",
        "description": "chibi anime style, big head small body proportion, cute round shapes, anime color palette, soft cel shading",
        "locked_descriptor": "chibi proportion, big round head, soft anime shading, bright anime palette",
    },
}

ASSET_TYPE_CONTEXT = {
    "character": "a game character sprite viewed from the front, isolated single entity, idle pose, no background elements",
    "item": "a game item or object, isolated single item, centered, no character, no environment background",
    "environment": "a game environment tile or prop, seamless edge-friendly, architectural or nature element",
    "tile": "a seamless game tile texture, top-down view, repeatable pattern, no characters",
}

GRID_SIZES = [16, 32, 64, 128, 256]

# ============================================================
# REQUEST MODELS
# ============================================================
class GenerateRequest(BaseModel):
    image: str          # Base64 PNG dari canvas
    style_key: str      # Key dari STYLE_PRESETS
    asset_type: str     # character | item | environment | tile
    target_size: int    # 16 | 32 | 64 | 128 | 256
    locked_descriptor: str = ""  # Style descriptor yang dikunci per project
    extra_prompt: str = ""       # Instruksi tambahan dari user
    bg_method: str = "auto"      # "auto"|"rembg"|"ff15"|"ff30"|"ff40"|"none"

class SpriteSheetRequest(BaseModel):
    images: list[str]   # List Base64 PNG asset yang sudah diproses
    names: list[str]    # Nama tiap asset
    columns: int = 4    # Jumlah kolom di sprite sheet

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def build_structured_prompt(style_key: str, asset_type: str, target_size: int, 
                              locked_descriptor: str, extra_prompt: str) -> str:
    style = STYLE_PRESETS.get(style_key, STYLE_PRESETS["cartoon_casual"])
    asset_context = ASSET_TYPE_CONTEXT.get(asset_type, ASSET_TYPE_CONTEXT["character"])
    descriptor = locked_descriptor if locked_descriptor else style["locked_descriptor"]
    
    prompt = f"""Convert this rough sketch into a clean 2D game asset.

Style: {style['description']}.
Asset type: {asset_context}.

Requirements:
- PURE WHITE BACKGROUND (#ffffff) — solid flat white, no gradients, no shadows, no patterns
- Subject fully isolated on the white background, clean sharp edges between subject and background
- Centered composition with even padding on all sides
- Flat clean outline, NO background scenery, NO ground shadow, NO decorative border
- Maintain ALL character details: face, eyes, body markings, colors — do not omit any feature
- Consistent art direction: {descriptor}
- Resolution intent: optimized for {target_size}px game sprite
- Do not add extra elements not present in the sketch
- The subject must be fully visible and centered"""

    if extra_prompt:
        prompt += f"\n\nAdditional instruction: {extra_prompt}"
    
    return prompt


def remove_background_smart(image_bytes: bytes) -> bytes:
    """
    Smart background removal dengan dua strategi:
    1. rembg (AI-based, akurat) — digunakan jika tersedia
    2. Flood-fill fallback (Pillow) — jika rembg tidak ada

    rembg menggunakan model U2Net untuk segmentasi semantik:
    ia "mengerti" mana subjek dan mana background, apapun warnanya.
    """
    if REMBG_AVAILABLE:
        # rembg: AI-based, handles any background color, clean edges
        result = rembg_remove(image_bytes)
        return result
    else:
        return _flood_fill_bg_removal(image_bytes)


def _flood_fill_bg_removal(image_bytes: bytes, tolerance: int = 15) -> bytes:
    """
    Fallback: Flood-fill dari 8 titik pinggir dengan tolerance KONSERVATIF (±15).

    Kenapa ±15 bukan ±40?
    - ±15 aman: hanya hapus piksel yang sangat dekat dengan warna background
    - Anti-aliasing di tepi karakter biasanya berbeda ±10-20 dari background
    - ±40 terlalu agresif: bisa hapus detail terang di karakter (highlight mata, dll)
    - Trade-off: mungkin ada halo tipis tersisa di tepi, tapi karakter tetap utuh

    Cara kerja:
    1. Sample warna background dari 8 titik pinggir gambar
    2. Hitung rata-rata → ini warna background sesungguhnya
    3. Flood-fill dari pinggir dengan tolerance ±15
    4. Hanya piksel TERHUBUNG dari pinggir yang dihapus (aman untuk karakter di tengah)
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = img.size
    pixels = img.load()

    # Sample 8 titik pinggir untuk deteksi warna background
    sample_points = [
        (0, 0), (width-1, 0), (0, height-1), (width-1, height-1),
        (width//2, 0), (width//2, height-1),
        (0, height//2), (width-1, height//2),
    ]
    corner_colors = [pixels[x, y][:3] for x, y in sample_points]
    bg_r = sum(c[0] for c in corner_colors) // len(corner_colors)
    bg_g = sum(c[1] for c in corner_colors) // len(corner_colors)
    bg_b = sum(c[2] for c in corner_colors) // len(corner_colors)

    # Tolerance yang dipakai sesuai pilihan developer
    TOLERANCE = tolerance

    def is_bg_color(r, g, b):
        return (abs(int(r) - bg_r) <= TOLERANCE and
                abs(int(g) - bg_g) <= TOLERANCE and
                abs(int(b) - bg_b) <= TOLERANCE)

    def flood_fill(start_x, start_y):
        if not is_bg_color(*pixels[start_x, start_y][:3]):
            return
        stack = [(start_x, start_y)]
        visited = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            if cx < 0 or cx >= width or cy < 0 or cy >= height:
                continue
            visited.add((cx, cy))
            r, g, b, a = pixels[cx, cy]
            if is_bg_color(r, g, b):
                pixels[cx, cy] = (r, g, b, 0)
                stack.extend([(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)])

    # Flood dari 8 titik pinggir
    for sx, sy in sample_points:
        flood_fill(sx, sy)

    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()


# Alias utama — dipakai jika bg_method tidak diberikan
remove_background_pillow = remove_background_smart


def apply_bg_removal(image_bytes: bytes, bg_method: str = "auto") -> bytes:
    """
    Dispatch ke metode background removal yang dipilih developer.

    bg_method options:
    - "auto"  → rembg jika tersedia, fallback flood-fill ±15
    - "rembg" → paksa pakai rembg (error jika tidak terinstall)
    - "ff15"  → flood-fill tolerance ±15 (konservatif, aman untuk detail)
    - "ff30"  → flood-fill tolerance ±30 (sedang, cocok untuk bg berwarna)
    - "ff40"  → flood-fill tolerance ±40 (agresif, hapus lebih banyak)
    - "none"  → tidak hapus background (output mentah dari Gemini)
    """
    if bg_method == "none":
        # Tidak hapus background — kembalikan gambar apa adanya sebagai RGBA
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()

    elif bg_method == "rembg":
        if not REMBG_AVAILABLE:
            raise RuntimeError("rembg tidak tersedia. Install dengan: pip install 'rembg[cpu]'")
        return rembg_remove(image_bytes)

    elif bg_method == "ff15":
        return _flood_fill_bg_removal(image_bytes, tolerance=15)

    elif bg_method == "ff30":
        return _flood_fill_bg_removal(image_bytes, tolerance=30)

    elif bg_method == "ff40":
        return _flood_fill_bg_removal(image_bytes, tolerance=40)

    else:  # "auto"
        return remove_background_smart(image_bytes)


def auto_crop_and_resize(image_bytes: bytes, target_size: int) -> bytes:
    """
    Auto-crop ke bounding box subjek, lalu resize + center + padding ke grid target.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    
    # Auto-crop: cari bounding box area non-transparan
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    
    # Tambah padding 10% agar subjek tidak mentok pinggir grid
    subject_w, subject_h = img.size
    padding_ratio = 0.1
    pad = int(max(subject_w, subject_h) * padding_ratio)
    
    # Buat canvas persegi dengan ukuran terbesar + padding
    canvas_size = max(subject_w, subject_h) + (pad * 2)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    
    # Tempel subjek di tengah canvas
    paste_x = (canvas_size - subject_w) // 2
    paste_y = (canvas_size - subject_h) // 2
    canvas.paste(img, (paste_x, paste_y), img)
    
    # Resize ke target grid size menggunakan LANCZOS (kualitas terbaik untuk pixel art: NEAREST)
    resample = Image.NEAREST if target_size <= 64 else Image.LANCZOS
    final = canvas.resize((target_size, target_size), resample)
    
    output = io.BytesIO()
    final.save(output, format="PNG")
    return output.getvalue()


def build_sprite_sheet(images_bytes: list[bytes], names: list[str], columns: int = 4) -> tuple[bytes, dict]:
    """
    Gabungkan beberapa PNG asset menjadi satu sprite sheet.
    Return: (sprite_sheet_bytes, metadata_json)
    """
    if not images_bytes:
        raise ValueError("Tidak ada gambar untuk dibuat sprite sheet")
    
    pil_images = [Image.open(io.BytesIO(b)).convert("RGBA") for b in images_bytes]
    
    # Asumsikan semua asset ukurannya sama (sudah di-resize ke grid)
    sprite_w, sprite_h = pil_images[0].size
    
    rows = (len(pil_images) + columns - 1) // columns
    sheet_w = sprite_w * columns
    sheet_h = sprite_h * rows
    
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    
    metadata = {
        "meta": {
            "app": "sketchAI",
            "version": "1.0",
            "format": "RGBA8888",
            "size": {"w": sheet_w, "h": sheet_h},
            "sprite_size": {"w": sprite_w, "h": sprite_h},
        },
        "frames": {}
    }
    
    for idx, (img, name) in enumerate(zip(pil_images, names)):
        col = idx % columns
        row = idx // columns
        x = col * sprite_w
        y = row * sprite_h
        sheet.paste(img, (x, y), img)
        
        # Format metadata kompatibel dengan Godot AtlasTexture & Phaser TextureAtlas
        metadata["frames"][name] = {
            "frame": {"x": x, "y": y, "w": sprite_w, "h": sprite_h},
            "rotated": False,
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": sprite_w, "h": sprite_h},
            "sourceSize": {"w": sprite_w, "h": sprite_h},
            "pivot": {"x": 0.5, "y": 0.5}
        }
    
    output = io.BytesIO()
    sheet.save(output, format="PNG")
    return output.getvalue(), metadata


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return FileResponse("index.html")


@app.get("/api/styles")
async def get_styles():
    """Kembalikan daftar style presets yang tersedia."""
    return {
        "styles": [
            {"key": k, "name": v["name"], "locked_descriptor": v["locked_descriptor"]}
            for k, v in STYLE_PRESETS.items()
        ],
        "asset_types": list(ASSET_TYPE_CONTEXT.keys()),
        "grid_sizes": GRID_SIZES,
    }


@app.post("/api/generate")
async def generate_game_asset(request: GenerateRequest):
    """
    Main endpoint: Sketch → Gemini → Background removal → Resize/grid → Game-ready PNG
    """
    try:
        # 1. Decode base64 sketch dari frontend
        if "," in request.image:
            clean_b64 = request.image.split(",")[1]
        else:
            clean_b64 = request.image
        image_bytes = base64.b64decode(clean_b64)

        # 2. Build structured prompt
        prompt = build_structured_prompt(
            style_key=request.style_key,
            asset_type=request.asset_type,
            target_size=request.target_size,
            locked_descriptor=request.locked_descriptor,
            extra_prompt=request.extra_prompt,
        )

        # 3. Panggil Gemini Image API
        sketch_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[sketch_part, prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        # 4. Ekstrak hasil gambar dari response
        generated_bytes = response.candidates[0].content.parts[0].inline_data.data

        # 5. Pipeline post-processing
        # Step A: Background removal (metode sesuai pilihan developer)
        transparent_bytes = apply_bg_removal(generated_bytes, request.bg_method)
        
        # Step B: Auto-crop + resize ke grid target
        final_bytes = auto_crop_and_resize(transparent_bytes, request.target_size)

        # 6. Encode ke base64 untuk dikembalikan ke frontend
        final_b64 = base64.b64encode(final_bytes).decode("utf-8")
        
        # Generate nama file otomatis
        style_name = STYLE_PRESETS.get(request.style_key, {}).get("name", "custom").replace(" ", "_").lower()
        filename = f"{request.asset_type}_{style_name}_{request.target_size}x{request.target_size}.png"
        
        # Kembalikan juga locked_descriptor untuk dikunci di project berikutnya
        locked = request.locked_descriptor or STYLE_PRESETS.get(request.style_key, {}).get("locked_descriptor", "")

        return {
            "status": "success",
            "image": f"data:image/png;base64,{final_b64}",
            "filename": filename,
            "size": request.target_size,
            "locked_descriptor": locked,
            "raw_image": f"data:image/png;base64,{base64.b64encode(generated_bytes).decode('utf-8')}",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-variation")
async def generate_variation(request: GenerateRequest):
    """
    Image-to-image: Gunakan asset yang sudah ada sebagai referensi untuk generate variasi.
    Style tetap konsisten karena pakai gambar sebelumnya sebagai base.
    """
    try:
        if "," in request.image:
            clean_b64 = request.image.split(",")[1]
        else:
            clean_b64 = request.image
        image_bytes = base64.b64decode(clean_b64)

        # Prompt variasi: minta perubahan spesifik, pertahankan style
        variation_prompt = f"""This is an existing 2D game asset. Generate a variation of this exact asset.

Keep exactly the same: art style, outline thickness, color palette mood, size and proportion.
Change only: {request.extra_prompt if request.extra_prompt else 'create an alternative color variant'}

Requirements:
- TRANSPARENT background
- Same centered composition as the original
- Same art style: {request.locked_descriptor}
- Same asset type, same pose/angle, different color/condition only"""

        sketch_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[sketch_part, variation_prompt],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )

        generated_bytes = response.candidates[0].content.parts[0].inline_data.data
        transparent_bytes = remove_background_pillow(generated_bytes)
        final_bytes = auto_crop_and_resize(transparent_bytes, request.target_size)
        final_b64 = base64.b64encode(final_bytes).decode("utf-8")

        return {
            "status": "success",
            "image": f"data:image/png;base64,{final_b64}",
            "filename": f"variation_{request.asset_type}_{request.target_size}x{request.target_size}.png",
            "size": request.target_size,
            "locked_descriptor": request.locked_descriptor,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export-spritesheet")
async def export_sprite_sheet(request: SpriteSheetRequest):
    """
    Gabungkan beberapa asset PNG menjadi sprite sheet + JSON metadata.
    Format kompatibel: Godot AtlasTexture, Phaser TextureAtlas, Unity Sprite Atlas.
    """
    try:
        if len(request.images) == 0:
            raise ValueError("Minimal 1 gambar dibutuhkan")
        
        # Decode semua images
        images_bytes = []
        for img_b64 in request.images:
            if "," in img_b64:
                clean = img_b64.split(",")[1]
            else:
                clean = img_b64
            images_bytes.append(base64.b64decode(clean))
        
        # Build sprite sheet
        sheet_bytes, metadata = build_sprite_sheet(
            images_bytes, request.names, request.columns
        )
        
        # Buat ZIP yang berisi PNG + JSON
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("spritesheet.png", sheet_bytes)
            zf.writestr("spritesheet.json", json.dumps(metadata, indent=2))
        
        zip_b64 = base64.b64encode(zip_buffer.getvalue()).decode("utf-8")
        sheet_b64 = base64.b64encode(sheet_bytes).decode("utf-8")
        
        return {
            "status": "success",
            "spritesheet": f"data:image/png;base64,{sheet_b64}",
            "metadata": metadata,
            "zip": f"data:application/zip;base64,{zip_b64}",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ANIMATION DEFINITIONS
# ============================================================
ANIMATION_DEFINITIONS = {
    "idle": {
        "name": "Idle (Breathing)",
        "emoji": "😴",
        "description": "Subtle breathing, character standing still",
        "recommended_fps": 6,
        "frames": [
            "neutral standing pose, arms relaxed at sides, normal resting state",
            "chest very slightly raised, beginning of inhale, shoulders imperceptibly up",
            "chest slightly raised at peak inhale, shoulders slightly raised",
            "chest beginning to lower, mid exhale",
            "chest back to neutral position, fully exhaled",
            "slight natural sway, weight shifting subtly",
        ]
    },
    "walk": {
        "name": "Walk Cycle",
        "emoji": "🚶",
        "description": "Standard 8-frame walk cycle",
        "recommended_fps": 8,
        "frames": [
            "contact pose: right foot forward heel touching ground, left foot back toe pushing off, left arm forward right arm back",
            "recoil: body slightly lower, weight transferring to right foot, left leg trailing, arms moving toward center",
            "passing: right leg straight bearing weight, left knee raised and swinging forward, arms at center",
            "high point: body tallest, left leg swinging forward shin extending, arms swinging outward",
            "contact pose: left foot forward heel touching ground, right foot back toe pushing off, right arm forward left arm back",
            "recoil: body slightly lower, weight transferring to left foot, right leg trailing, arms moving toward center",
            "passing: left leg straight bearing weight, right knee raised and swinging forward, arms at center",
            "high point: body tallest, right leg swinging forward shin extending, arms swinging outward",
        ]
    },
    "run": {
        "name": "Run Cycle",
        "emoji": "🏃",
        "description": "Fast 6-frame run cycle",
        "recommended_fps": 12,
        "frames": [
            "contact: right foot strikes ground, left leg powerfully behind, body leaning forward 20 degrees, arms pumping",
            "drive: right leg pushing off, body at lowest, left knee driving forward high, opposite arm pumping",
            "flight: both feet off ground, body almost horizontal, legs spread wide in air",
            "contact: left foot strikes ground, right leg powerfully behind, body leaning forward, arms pumping",
            "drive: left leg pushing off, body at lowest, right knee driving forward high, opposite arm pumping",
            "flight mirror: both feet off ground, body horizontal, legs spread (mirror of frame 3)",
        ]
    },
    "jump": {
        "name": "Jump Arc",
        "emoji": "⬆️",
        "description": "Full jump arc from crouch to landing",
        "recommended_fps": 8,
        "frames": [
            "anticipation: crouching down knees bent 45 degrees, arms pulled back, body compressed ready to spring",
            "launch: just leaving ground, legs pushing off nearly straight, arms swinging upward dynamically",
            "ascending: body rising, knees beginning to tuck toward chest, arms reaching up",
            "peak: at maximum height, knees fully tucked, body at apex of jump",
            "descending: body falling, legs beginning to extend downward for landing",
            "landing impact: feet touching ground, knees deeply bent absorbing impact, arms out for balance",
        ]
    },
    "attack": {
        "name": "Attack (Melee)",
        "emoji": "⚔️",
        "description": "Melee attack swing",
        "recommended_fps": 12,
        "frames": [
            "wind up: dominant arm pulled back and raised, body rotating away from target, weight shifting back",
            "charge: arm fully pulled back at maximum coil, body tensed rotated away, opposite foot stepping forward",
            "swing: arm beginning forward motion fast, body starting to rotate toward target",
            "strike: arm at full forward extension at impact point, body fully rotated, maximum reach",
            "follow through: arm continuing past impact, body momentum carrying forward",
            "recovery: returning to neutral guard stance, arm coming back to ready position",
        ]
    },
    "hurt": {
        "name": "Hurt / Flinch",
        "emoji": "💥",
        "description": "Damage received reaction",
        "recommended_fps": 8,
        "frames": [
            "impact: body lurching backward, head snapping back, arms flailing outward in shock",
            "recoil: body bent backward at peak, arms spread wide",
            "recovery start: body beginning to straighten, arms coming in, guard going up",
            "recovery end: back to guard stance, slightly hunched",
        ]
    },
    "die": {
        "name": "Death",
        "emoji": "💀",
        "description": "Character death sequence",
        "recommended_fps": 8,
        "frames": [
            "hit: character recoiling from fatal blow, body jerking backward dramatically",
            "stagger: body beginning to fall, legs buckling, arms reaching out weakly",
            "falling: body at 45 degrees clearly falling, arms dropping limp",
            "ground contact: body hitting the ground, limbs splaying out",
            "settle: body lying completely flat on ground, final resting position",
        ]
    },
}


class AnimationRequest(BaseModel):
    image: str
    style_key: str
    asset_type: str
    target_size: int
    animation_type: str     # key dari ANIMATION_DEFINITIONS, atau "custom"
    fps: int = 8
    locked_descriptor: str = ""
    extra_prompt: str = ""
    custom_description: str = ""  # Dipakai saat animation_type == "custom"
    custom_frame_count: int = 6   # Jumlah frame untuk custom animation
    bg_method: str = "auto"       # "auto"|"rembg"|"ff15"|"ff30"|"ff40"|"none"


@app.get("/api/animations")
async def get_animations():
    return {
        "animations": [
            {
                "key": k,
                "name": v["name"],
                "emoji": v["emoji"],
                "description": v["description"],
                "recommended_fps": v["recommended_fps"],
                "frame_count": len(v["frames"]),
            }
            for k, v in ANIMATION_DEFINITIONS.items()
        ],
        "fps_options": [6, 8, 12, 24],
    }


@app.post("/api/generate-animation")
async def generate_animation(request: AnimationRequest):
    """
    Generate full animation cycle frame-by-frame.
    Frame 0 from sketch, Frame N from previous frame (image-to-image).
    Returns all frames + horizontal sprite strip + JSON metadata.
    """
    try:
        style = STYLE_PRESETS.get(request.style_key, STYLE_PRESETS["cartoon_casual"])
        descriptor = request.locked_descriptor or style["locked_descriptor"]
        asset_ctx = ASSET_TYPE_CONTEXT.get(request.asset_type, ASSET_TYPE_CONTEXT["character"])

        if request.animation_type == "custom":
            # Pakai Gemini text model untuk generate frame descriptions dari deskripsi developer
            if not request.custom_description:
                raise ValueError("Deskripsi animasi custom tidak boleh kosong")
            n = max(2, min(12, request.custom_frame_count))
            gen_prompt = f"""You are a 2D game animation designer. Generate exactly {n} frame-by-frame pose descriptions for a character animation.

Developer's animation description: "{request.custom_description}"
Character type: {request.asset_type}

Rules:
- Generate EXACTLY {n} lines, one per frame
- Each line describes ONLY the character's pose/body position for that specific frame
- Be specific: mention limb positions, body angle, weight distribution
- Show clear progression of movement through the animation
- Do NOT number the lines, do NOT add headers, do NOT add extra text
- Each description: 1-2 sentences max

Output the {n} frame descriptions now:"""
            text_resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=gen_prompt,
            )
            raw_lines = [l.strip() for l in text_resp.text.strip().split("\n") if l.strip()]
            # Clean any accidental numbering
            frame_descs = [re.sub(r"^\d+[\.)\-]\s*", "", l) for l in raw_lines if l][:n]
            # Pad if model returned fewer lines
            while len(frame_descs) < n:
                frame_descs.append(frame_descs[-1] if frame_descs else "neutral standing pose")
            anim_name = request.custom_description[:60]
            anim_def = {
                "name": f"Custom: {anim_name}",
                "frames": frame_descs,
            }
        else:
            anim_def = ANIMATION_DEFINITIONS.get(request.animation_type)
            if not anim_def:
                raise ValueError(f"Animation type tidak ditemukan: {request.animation_type}")

        frame_descs = anim_def["frames"]
        total = len(frame_descs)

        if "," in request.image:
            sketch_bytes = base64.b64decode(request.image.split(",")[1])
        else:
            sketch_bytes = base64.b64decode(request.image)

        generated_frames = []
        prev_bytes = sketch_bytes

        for i, frame_desc in enumerate(frame_descs):
            if i == 0:
                prompt = f"""Convert this rough sketch into a clean 2D game character asset.
This is FRAME 1 of {total} in a '{anim_def["name"]}' animation cycle.

Style: {style["description"]}.
Asset: {asset_ctx}.
This frame pose: {frame_desc}

REQUIREMENTS:
- PURE WHITE BACKGROUND (#ffffff) — flat solid white, nothing else behind the character
- Clean sharp edges between character and white background
- Centered character with even padding on all sides
- Art style: {descriptor}
- Maintain ALL character details: face, eyes, mouth, body markings, colors — do NOT omit any feature
- Optimized for {request.target_size}px sprite
- No decorative background elements, no ground shadow, no extra objects"""
            else:
                prompt = f"""This is an existing 2D game character frame. Generate FRAME {i+1} of {total} for a '{anim_def["name"]}' animation.

CRITICAL RULES:
- Keep EXACTLY the same art style, character design, color palette, proportions, outline thickness
- Keep ALL character details: face, eyes, mouth, markings — do NOT omit or simplify any feature
- ONLY change the pose/limb positions as described below

This frame pose: {frame_desc}
Previous frame showed: {frame_descs[i-1]}

Style to maintain: {descriptor}
Character type: {asset_ctx}

REQUIREMENTS:
- PURE WHITE BACKGROUND (#ffffff) — flat solid white, nothing behind the character
- Clean sharp edges between character and white background
- Same character size, same art style, same colors as input frame
- No background elements, no shadow, no ground"""

            part = types.Part.from_bytes(data=prev_bytes, mime_type="image/png")
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[part, prompt],
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )
            raw = response.candidates[0].content.parts[0].inline_data.data
            transparent = apply_bg_removal(raw, request.bg_method)
            final = auto_crop_and_resize(transparent, request.target_size)
            generated_frames.append(final)
            prev_bytes = final  # Next frame uses processed frame as reference

        frame_names = [
            f"{request.asset_type}_{request.animation_type}_f{i:02d}_{request.target_size}px.png"
            for i in range(len(generated_frames))
        ]

        # Horizontal sprite strip (all frames side by side)
        strip_bytes, metadata = build_sprite_sheet(
            generated_frames, frame_names, columns=len(generated_frames)
        )
        metadata["animation"] = {
            "type": request.animation_type,
            "name": anim_def["name"],
            "fps": request.fps,
            "frame_count": len(generated_frames),
            "loop": True,
            "sprite_size": {"w": request.target_size, "h": request.target_size},
        }

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            strip_name = f"{request.asset_type}_{request.animation_type}_strip.png"
            json_name = f"{request.asset_type}_{request.animation_type}.json"
            zf.writestr(strip_name, strip_bytes)
            zf.writestr(json_name, json.dumps(metadata, indent=2))
            for name, fb in zip(frame_names, generated_frames):
                zf.writestr(name, fb)

        return {
            "status": "success",
            "frames": [
                f"data:image/png;base64,{base64.b64encode(f).decode()}"
                for f in generated_frames
            ],
            "frame_names": frame_names,
            "spritesheet": f"data:image/png;base64,{base64.b64encode(strip_bytes).decode()}",
            "metadata": metadata,
            "zip": f"data:application/zip;base64,{base64.b64encode(zip_buf.getvalue()).decode()}",
            "fps": request.fps,
            "total_frames": len(generated_frames),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
