import warnings

from django import forms
from django.conf import settings
from PIL import Image, UnidentifiedImageError

from .models import ImageCheck


class ValidatedImageField(forms.ImageField):
    def to_python(self, data):
        uploaded = forms.FileField.to_python(self, data)
        if uploaded is None:
            return None
        if uploaded.size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise forms.ValidationError('Файл превышает допустимый размер.')

        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                uploaded.seek(0)
                with Image.open(uploaded) as image:
                    if image.format not in {'JPEG', 'PNG', 'WEBP'}:
                        raise forms.ValidationError('Допустимы только JPG, JPEG, PNG или WEBP.')
                    if image.width * image.height > settings.MAX_UPLOAD_PIXELS:
                        raise forms.ValidationError('Изображение содержит слишком много пикселей.')
                    image.verify()
                uploaded.seek(0)
                with Image.open(uploaded) as image:
                    image.load()
                uploaded.seek(0)
                uploaded = super().to_python(uploaded)
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
                Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
            raise forms.ValidationError('Изображение повреждено или небезопасно для обработки.') from exc
        finally:
            uploaded.seek(0)
        return uploaded


class ImageUploadForm(forms.ModelForm):
    original_image = ValidatedImageField()
    allow_external_analysis = forms.BooleanField(required=False)

    class Meta:
        model = ImageCheck
        fields = ['original_image']

    def save(self, commit=True):
        instance = super().save(commit=False)
        image = self.cleaned_data['original_image']
        instance.original_filename = image.name
        if commit:
            instance.save()
        return instance
