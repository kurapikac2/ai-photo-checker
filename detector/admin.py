from django.contrib import admin
from .models import ImageCheck


@admin.register(ImageCheck)
class ImageCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_filename', 'verdict', 'confidence', 'final_score', 'processing_status', 'uploaded_at')
    list_filter = ('verdict', 'processing_status', 'uploaded_at')
    search_fields = ('original_filename', 'error_message')
    readonly_fields = ('uploaded_at', 'model_raw_response', 'local_analysis', 'reasons', 'visual_signs')
