# backend/app/inventory/qrcodes.py
# This file contains QR code generation utilities for inventory management.
import qrcode
from io import BytesIO

def generate_qr_code(data: str) -> BytesIO:
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
