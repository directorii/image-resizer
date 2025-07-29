from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

app = FastAPI(title="Thumbnail Service")

# ---------------------------
# 1. Thumbnail size presets
# ---------------------------
class AttachmentSize(str, Enum):
    list  = "list"
    card  = "card"
    big   = "big"
    large = "large"
    xlarge = "xlarge"

SIZE_MAP: Dict[AttachmentSize, int] = {
    AttachmentSize.list:   80,
    AttachmentSize.card:   180,
    AttachmentSize.big:    320,
    AttachmentSize.large:  640,
    AttachmentSize.xlarge: 1024,
}

# ---------------------------
# 2. Ensure output folders and static serving
# ---------------------------
BASE_DIR = Path(__file__).parent
THUMB_DIR = BASE_DIR / "thumbnails"
THUMB_DIR.mkdir(exist_ok=True)

app.mount("/thumbnails", StaticFiles(directory=THUMB_DIR), name="thumbnails")

# ---------------------------
# 3. Helper: generate thumbnail in memory
# ---------------------------
def generate_thumbnail(data: bytes, max_side: int, fmt: str) -> bytes:
    if fmt.lower() not in {"png", "webp"}:
        raise ValueError("Unsupported target format")

    with Image.open(BytesIO(data)) as img:
        img = img.convert("RGBA")  # universal mode
        img.thumbnail((max_side, max_side), Image.LANCZOS)

        out = BytesIO()
        save_kwargs = dict(format=fmt.upper())
        if fmt.lower() == "webp":
            save_kwargs.update(quality=90, method=6)
        else:  # png
            save_kwargs.update(optimize=True)
        img.save(out, **save_kwargs)
        return out.getvalue()

# ---------------------------
# 4. Upload endpoint – generate ALL sizes
# ---------------------------
@app.post("/upload/", summary="Upload an image and create thumbnails for all sizes")
async def upload_image(
    file: UploadFile = File(..., description="Any common raster format"),
):
    if file.content_type.split("/")[0] != "image":
        raise HTTPException(status_code=415, detail="File is not an image")

    raw = await file.read()
    stem = Path(file.filename).stem

    result: Dict[str, Dict[str, str]] = {}

    for size_name, max_side in SIZE_MAP.items():
        try:
            png_bytes  = generate_thumbnail(raw, max_side, "png")
            webp_bytes = generate_thumbnail(raw, max_side, "webp")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed at {size_name}: {e}")

        # Persist under thumbnails/{max_side}/
        subdir = THUMB_DIR / str(max_side)
        subdir.mkdir(parents=True, exist_ok=True)

        png_path  = subdir / f"{stem}.png"
        webp_path = subdir / f"{stem}.webp"
        png_path.write_bytes(png_bytes)
        webp_path.write_bytes(webp_bytes)

        result[str(max_side)] = {
            "png":  f"/thumbnails/{max_side}/{png_path.name}",
            "webp": f"/thumbnails/{max_side}/{webp_path.name}",
        }

    return result


# ---------------------------
# 5. Convenience route to view a thumbnail in browser
# ---------------------------
@app.get("/view/{size}/{name}", response_class=FileResponse)
def view_thumbnail(size: int, name: str):
    file_path = THUMB_DIR / str(size) / name
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(file_path)
