from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
import io
import re

app = FastAPI(title="Game OCR Service")

# =========================
# OCR 初始化
# =========================
ocr = PaddleOCR(
    lang="ch",
    ocr_version="PP-OCRv5",
    device="gpu",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)


# =========================
# OCR 通用函数
# =========================
def run_ocr(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(400, "Invalid image")

    img_array = np.array(image)

    result = ocr.predict(img_array)

    if not result:
        return []

    res = result[0]

    texts = res.get("rec_texts", [])
    scores = res.get("rec_scores", [])

    return list(zip(texts, scores))


# =========================
# 1. 技能识别
# =========================
@app.post("/skills")
async def skills(file: UploadFile = File(...)):

    content = await file.read()
    items = run_ocr(content)

    skills = []

    for text, score in items:

        if score < 0.4:
            continue

        # 只保留中文技能名
        if re.search(r"[\u4e00-\u9fa5]", text):
            if "★" in text:
                continue
            if text.isdigit():
                continue

            skills.append(text)

    return JSONResponse({
        "success": True,
        "skills": skills
    })


# =========================
# 2. 敌方血量（100%）
# =========================
@app.post("/enemy-hp")
async def enemy_hp(file: UploadFile = File(...)):

    content = await file.read()
    items = run_ocr(content)

    hp = None

    for text, score in items:

        if score < 0.4:
            continue

        if re.match(r"^\d{1,3}%$", text):
            hp = text
            break

    return JSONResponse({
        "success": True,
        "enemy_hp": hp
    })


# =========================
# 3. 自身血量（233/233）
# =========================
@app.post("/self-hp")
async def self_hp(file: UploadFile = File(...)):

    content = await file.read()
    items = run_ocr(content)

    hp = None

    for text, score in items:

        if score < 0.4:
            continue

        if re.match(r"^\d+/\d+$", text):
            hp = text
            break

    return JSONResponse({
        "success": True,
        "self_hp": hp
    })


# =========================
# health check
# =========================
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": "PP-OCRv5 (GPU)"
    }