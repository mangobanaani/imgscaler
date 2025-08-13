"""Utility helpers for image I/O and pre/post processing."""
from __future__ import annotations

from io import BytesIO
from typing import Tuple
from PIL import Image


def load_image_bytes(data: bytes) -> Image.Image:
    return Image.open(BytesIO(data))


def ensure_rgb(img: Image.Image) -> Image.Image:
    if img.mode not in ("RGB", "RGBA"):
        return img.convert("RGB")
    return img


def clamp_large_image(img: Image.Image, max_pixels: int) -> Image.Image:
    if img.width * img.height > max_pixels:
        scale = (max_pixels / (img.width * img.height)) ** 0.5
        new_size: Tuple[int, int] = (int(img.width * scale), int(img.height * scale))
        return img.resize(new_size, Image.BICUBIC)
    return img
