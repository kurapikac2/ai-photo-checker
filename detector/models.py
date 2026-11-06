import uuid
from django.db import models


def upload_image_path(instance, filename):
    ext = filename.split('.')[-1].lower() if '.' in filename else 'bin'
    return f'uploads/{uuid.uuid4().hex}.{ext}'


class ImageCheck(models.Model):
    STATUS_CHOICES = [
        ('likely_real', 'Likely real'),
        ('suspicious', 'Suspicious'),
        ('likely_ai_generated', 'Likely AI-generated'),
        ('likely_edited', 'Likely edited'),
        ('uncertain', 'Uncertain'),
    ]

    original_filename = models.CharField(max_length=255, blank=True)
    owner_token = models.CharField(max_length=64, blank=True, default='', db_index=True, editable=False)
    original_image = models.ImageField(upload_to=upload_image_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    verdict = models.CharField(max_length=50, choices=STATUS_CHOICES, blank=True)
    confidence = models.IntegerField(default=0)
    ai_generation_probability = models.IntegerField(default=0)
    manipulation_probability = models.IntegerField(default=0)

    metadata_score = models.IntegerField(default=0)
    ela_score = models.IntegerField(default=0)
    artifact_score = models.IntegerField(default=0)
    final_score = models.IntegerField(default=0)

    reasons = models.JSONField(default=list, blank=True)
    visual_signs = models.JSONField(default=list, blank=True)
    local_analysis = models.JSONField(default=dict, blank=True)
    model_raw_response = models.JSONField(default=dict, blank=True)
    processing_status = models.CharField(max_length=30, default='pending')
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.original_filename or self.original_image.name} - {self.verdict or "pending"}'

    def delete_with_image(self):
        # Keep the row for retry if storage raises an error.
        self.original_image.delete(save=False)
        self.delete()
