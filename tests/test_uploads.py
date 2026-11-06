import io
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fake_checker.settings')

import django
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from detector.forms import ImageUploadForm


def image_bytes(format='PNG', size=(16, 16)):
    stream = io.BytesIO()
    Image.new('RGB', size, 'blue').save(stream, format=format)
    return stream.getvalue()


def upload_form(content, name='sample.png', content_type='image/png'):
    upload = SimpleUploadedFile(name, content, content_type=content_type)
    return ImageUploadForm(files={'original_image': upload})


class UploadValidationTests(unittest.TestCase):
    def test_supported_formats_remain_readable_for_storage(self):
        for format, extension in [('JPEG', 'jpg'), ('PNG', 'png'), ('WEBP', 'webp')]:
            with self.subTest(format=format):
                content = image_bytes(format)
                form = upload_form(content, f'image.{extension}')
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data['original_image'].read(), content)

    def test_rejects_unsupported_format_even_with_spoofed_mime(self):
        form = upload_form(image_bytes('GIF'), 'image.jpg', 'image/jpeg')
        self.assertFalse(form.is_valid())
        self.assertIn('original_image', form.errors)

    def test_rejects_non_image_and_empty_uploads(self):
        for content in [b'not an image', b'']:
            with self.subTest(content=content):
                self.assertFalse(upload_form(content).is_valid())

    def test_rejects_jpeg_with_truncated_pixel_data(self):
        content = image_bytes('JPEG', (64, 64))[:-10]
        form = upload_form(content, 'truncated.jpg', 'image/jpeg')
        self.assertFalse(form.is_valid())
        self.assertIn('original_image', form.errors)

    def test_rejects_png_with_invalid_chunk_checksum(self):
        content = bytearray(image_bytes())
        chunk_type = content.index(b'IDAT')
        chunk_length = int.from_bytes(content[chunk_type - 4:chunk_type], 'big')
        content[chunk_type + 4 + chunk_length] ^= 1
        form = upload_form(bytes(content))
        self.assertFalse(form.is_valid())
        self.assertIn('original_image', form.errors)

    def test_byte_limit_accepts_boundary_and_rejects_one_byte_over(self):
        content = image_bytes()
        with override_settings(MAX_UPLOAD_SIZE_BYTES=len(content)):
            self.assertTrue(upload_form(content).is_valid())
        with override_settings(MAX_UPLOAD_SIZE_BYTES=len(content) - 1):
            self.assertFalse(upload_form(content).is_valid())

    @override_settings(MAX_UPLOAD_PIXELS=256)
    def test_pixel_limit_accepts_boundary_and_rejects_larger_image(self):
        self.assertTrue(upload_form(image_bytes(size=(16, 16))).is_valid())
        self.assertFalse(upload_form(image_bytes(size=(17, 16))).is_valid())

    def test_rejects_decompression_bomb_warning_and_error(self):
        content = image_bytes(size=(16, 16))
        for limit in [200, 100]:
            with self.subTest(limit=limit), patch.object(Image, 'MAX_IMAGE_PIXELS', limit):
                self.assertFalse(upload_form(content).is_valid())


if __name__ == '__main__':
    unittest.main()
