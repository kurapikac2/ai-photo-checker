import imghdr
from django import forms
from django.conf import settings
from .models import ImageCheck


class ImageUploadForm(forms.ModelForm):
    class Meta:
        model = ImageCheck
        fields = ['original_image']

    def clean_original_image(self):
        uploaded = self.cleaned_data['original_image']
        if uploaded.size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise forms.ValidationError('Файл слишком большой. Максимум 10 МБ.')

        header = uploaded.read(512)
        uploaded.seek(0)
        image_type = imghdr.what(None, header)
        allowed = {'jpeg', 'png', 'webp'}
        if image_type not in allowed:
            raise forms.ValidationError('Допустимы только JPG, JPEG, PNG или WEBP.')
        return uploaded

    def save(self, commit=True):
        instance = super().save(commit=False)
        image = self.cleaned_data['original_image']
        instance.original_filename = image.name
        if commit:
            instance.save()
        return instance
