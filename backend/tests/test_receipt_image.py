import io
import unittest

from PIL import Image

from app.services.receipt_image import ReceiptImageError, prepare_receipt_image


class ReceiptImageTests(unittest.TestCase):
    def test_a_png_screenshot_is_left_as_a_png(self):
        image = Image.new("RGB", (4, 4), (10, 20, 30))
        out = io.BytesIO()
        image.save(out, format="PNG")
        png = out.getvalue()

        prepared = prepare_receipt_image(png)

        self.assertEqual(prepared, png)
        self.assertEqual(Image.open(io.BytesIO(prepared)).format, "PNG")

    def test_an_iphone_heic_photo_becomes_a_jpeg_the_reader_can_open(self):
        import pillow_heif

        image = Image.new("RGB", (6, 6), (200, 10, 10))
        raw = io.BytesIO()
        pillow_heif.from_pillow(image).save(raw, quality=90)
        heic = raw.getvalue()
        self.assertEqual(heic[4:12], b"ftypheic")

        prepared = prepare_receipt_image(heic)

        opened = Image.open(io.BytesIO(prepared))
        self.assertEqual(opened.format, "JPEG")
        self.assertEqual(opened.size, (6, 6))

    def test_a_file_that_is_not_a_photo_is_refused(self):
        with self.assertRaises(ReceiptImageError):
            prepare_receipt_image(b"this is not a photo")

    def test_an_empty_upload_is_refused(self):
        with self.assertRaises(ReceiptImageError):
            prepare_receipt_image(b"")

    def test_the_heif_decoder_can_read_an_ios_26_hdr_screenshot(self):
        import pillow_heif

        decoder = pillow_heif.libheif_info()["decoders"]["libde265"]
        version = tuple(int(part) for part in decoder.rsplit("version ", 1)[-1].split("."))
        # iOS 26 HDR screenshots are tiled HEIF. libde265 1.0.15 cannot decode them.
        self.assertGreaterEqual(version, (1, 0, 16))
