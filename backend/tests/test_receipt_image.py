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
