from django.db import migrations, models
import detector.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ImageCheck',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_filename', models.CharField(blank=True, max_length=255)),
                ('original_image', models.ImageField(upload_to=detector.models.upload_image_path)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('verdict', models.CharField(blank=True, choices=[('likely_real', 'Likely real'), ('suspicious', 'Suspicious'), ('likely_ai_generated', 'Likely AI-generated'), ('likely_edited', 'Likely edited'), ('uncertain', 'Uncertain')], max_length=50)),
                ('confidence', models.IntegerField(default=0)),
                ('ai_generation_probability', models.IntegerField(default=0)),
                ('manipulation_probability', models.IntegerField(default=0)),
                ('metadata_score', models.IntegerField(default=0)),
                ('ela_score', models.IntegerField(default=0)),
                ('artifact_score', models.IntegerField(default=0)),
                ('final_score', models.IntegerField(default=0)),
                ('reasons', models.JSONField(blank=True, default=list)),
                ('visual_signs', models.JSONField(blank=True, default=list)),
                ('local_analysis', models.JSONField(blank=True, default=dict)),
                ('model_raw_response', models.JSONField(blank=True, default=dict)),
                ('processing_status', models.CharField(default='pending', max_length=30)),
                ('error_message', models.TextField(blank=True)),
            ],
            options={'ordering': ['-uploaded_at']},
        ),
    ]
