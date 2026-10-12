"""Turn an uploaded receipt into bytes the reader can open.

A normal iPhone screenshot is a PNG, which opens directly. Photos from the
library are often HEIC. An iOS 26 HDR screenshot is a tiled HEIF file, and
that file needs a current HEIF decoder before it can be turned into a JPEG.
"""
import io

from PIL import Image, ImageOps, UnidentifiedImageError

HEIF_BRANDS = {
    b"heic",
    b"heix",
    b"heim",
    b"heis",
    b"hevc",
    b"hevx",
    b"mif1",
    b"msf1",
    b"avif",
    b"avis",
}


class ReceiptImageError(Exception):
    pass


def prepare_receipt_image(data: bytes) -> bytes:
    """Return the original bytes when Pillow can open them, otherwise a JPEG."""
    if not data:
        raise ReceiptImageError("The photo was empty.")
    if _decode(data) is not None:
        return data
    if _looks_like_heif(data):
        _register_heif()
        image = _decode(data)
        if image is not None:
            return _jpeg(image)
    header = data[:16]
    print(f"Receipt image could not be opened: {len(data)} bytes, header {header!r}")
    raise ReceiptImageError("The reader could not open that photo.")


def _looks_like_heif(data: bytes) -> bool:
    return len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in HEIF_BRANDS


def _register_heif() -> None:
    import pillow_heif

    pillow_heif.register_heif_opener()


def _decode(data: bytes):
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        return image
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return None


def _jpeg(image: Image.Image) -> bytes:
    turned = ImageOps.exif_transpose(image) or image
    if turned.mode != "RGB":
        turned = turned.convert("RGB")
    out = io.BytesIO()
    turned.save(out, format="JPEG", quality=90)
    return out.getvalue()
