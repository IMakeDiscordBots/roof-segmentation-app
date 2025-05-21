from typing import List, Tuple
import numpy as np, cv2
from shapely.geometry import Polygon, mapping


def pix_to_geo(x: int, y: int, bbox: List[float], img_size: int) -> Tuple[float, float]:
    lon_left, lat_bottom, lon_right, lat_top = bbox
    lon = lon_left + (lon_right - lon_left) * (x / img_size)
    lat = lat_top - (lat_top - lat_bottom) * (y / img_size)
    return lon, lat


def mask_to_geojson(mask: np.ndarray, bbox: List[float]) -> dict:
    img_size = mask.shape[0]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    features = []
    for cnt in contours:
        if len(cnt) < 3:
            continue
        pts = [pix_to_geo(int(x), int(y), bbox, img_size) for [[x, y]] in cnt]
        # close the ring
        if pts[0] != pts[-1]:
            pts.append(pts[0])
        poly = Polygon(pts).simplify(1e-6)
        if not poly.is_valid or poly.area == 0:
            continue
        features.append({
            "type": "Feature",
            "properties": {},
            "geometry": mapping(poly)
        })
    return {"type": "FeatureCollection", "features": features}