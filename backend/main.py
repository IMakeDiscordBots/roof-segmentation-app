from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel, conlist
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np, tensorflow as tf, httpx, cv2, io, os
from backend.main import mask_to_geojson
from typing import List

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
MODEL_PATH = os.getenv("MODEL_PATH", "model/roof_seg")
IMG_SIZE = 512

app = FastAPI(title="Roof‑Seg API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

model = tf.keras.models.load_model(MODEL_PATH)

class SegRequest(BaseModel):
    bbox: conlist(float, min_items=4, max_items=4)  # [minLon, minLat, maxLon, maxLat]
    imgSize: int = IMG_SIZE

@app.post("/segment")
async def segment(req: SegRequest):
    min_lon, min_lat, max_lon, max_lat = req.bbox
    # centre & approximate zoom (simple heuristic)
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2
    lon_span = max_lon - min_lon
    zoom = max(18, int(  8 - np.log2(lon_span) ))

    url = (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"{center_lon},{center_lat},{zoom}/{req.imgSize}x{req.imgSize}"
        f"?access_token={MAPBOX_TOKEN}"
    )
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        r.raise_for_status()
        img = np.frombuffer(r.content, np.uint8)
        img = cv2.imdecode(img, cv2.IMREAD_COLOR)

    # prepare for model
    x = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    x = cv2.resize(x, (256, 256))
    x = x.astype(np.float32) / 255.0
    x = np.expand_dims(x, 0)
    pred = model.predict(x)[0]  # HxW  mask
    mask = (cv2.resize(pred, (IMG_SIZE, IMG_SIZE)) > 0.5).astype(np.uint8) * 255

    geojson = mask_to_geojson(mask, req.bbox)
    return JSONResponse(content=geojson)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)