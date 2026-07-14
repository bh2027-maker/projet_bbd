"""
Récupération et assemblage de tuiles orthophoto IGN (Géoplateforme WMTS).
Layer : ORTHOIMAGERY.ORTHOPHOTOS - EPSG:3857 (Web Mercator) - JPEG.
"""
import math
import io
import httpx
from PIL import Image

BASE_URL = "https://data.geopf.fr/wmts"


def _latlon_to_tile(lat: float, lon: float, z: int):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def _tile_url(z: int, x: int, y: int) -> str:
    return (f"{BASE_URL}?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile"
            f"&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal"
            f"&FORMAT=image/jpeg&TILEMATRIXSET=PM"
            f"&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}")


async def fetch_ortho_image(lat: float, lon: float, zoom: int = 18,
                            grid: int = 3) -> bytes:
    """
    Retourne un JPEG (bytes) d'une image satellite centrée sur (lat, lon).
    Assemble `grid`x`grid` tuiles (256px chacune). Résultat: 768x768 par défaut.
    """
    x_f, y_f = _latlon_to_tile(lat, lon, zoom)
    x_center, y_center = int(x_f), int(y_f)
    offset_x = x_f - x_center  # 0..1
    offset_y = y_f - y_center

    half = grid // 2
    tiles = {}

    async with httpx.AsyncClient(timeout=20) as client:
        # Fetch all needed tiles in parallel
        import asyncio
        tasks = []
        coords = []
        for dy in range(-half, half + 1):
            for dx in range(-half, half + 1):
                tx, ty = x_center + dx, y_center + dy
                coords.append((dx, dy, tx, ty))
                tasks.append(client.get(_tile_url(zoom, tx, ty)))
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    canvas = Image.new("RGB", (256 * grid, 256 * grid), (30, 30, 30))
    for (dx, dy, tx, ty), resp in zip(coords, responses):
        if isinstance(resp, Exception) or resp.status_code != 200:
            continue
        try:
            tile = Image.open(io.BytesIO(resp.content)).convert("RGB")
        except Exception:  # noqa
            continue
        col = dx + half
        row = dy + half
        canvas.paste(tile, (col * 256, row * 256))

    # Crop to center the target coordinate
    # target pixel in the canvas
    center_px_x = int((half + offset_x) * 256)
    center_px_y = int((half + offset_y) * 256)
    crop_size = 256 * (grid - 1)  # eg. 512 for grid=3
    half_c = crop_size // 2
    left = max(0, center_px_x - half_c)
    top = max(0, center_px_y - half_c)
    right = min(canvas.width, left + crop_size)
    bottom = min(canvas.height, top + crop_size)
    cropped = canvas.crop((left, top, right, bottom))

    buf = io.BytesIO()
    cropped.save(buf, format="JPEG", quality=75)
    return buf.getvalue()
