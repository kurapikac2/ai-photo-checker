import io
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from PIL import Image

from detector.models import ImageCheck


class AnalysisPrivacyTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        settings = override_settings(MEDIA_ROOT=self.media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.owner = Client()
        self.stranger = Client()
        self.local = patch('detector.views.run_local_analysis', return_value={
            'metadata_score': 0, 'ela_score': 0, 'artifact_score': 0,
            'details': {}, 'reasons': [],
        })
        self.local.start()
        self.addCleanup(self.local.stop)
        self.remote = patch('detector.views.analyze_with_openrouter', return_value={
            'verdict': 'uncertain', 'confidence': 0, 'reasons': [],
            'visual_signs': [], 'raw': {'private': 'upstream-data'},
        })
        self.api = self.remote.start()
        self.addCleanup(self.remote.stop)

    def upload(self, client=None, **data):
        stream = io.BytesIO()
        Image.new('RGB', (8, 8), 'blue').save(stream, format='PNG')
        data['original_image'] = SimpleUploadedFile('private.png', stream.getvalue(), 'image/png')
        response = (client or self.owner).post('/check/', data)
        self.assertEqual(response.status_code, 302)
        return ImageCheck.objects.latest('pk')

    def test_only_uploading_session_can_read_result_and_history(self):
        record = self.upload()
        self.assertEqual(self.owner.get(f'/result/{record.pk}/').status_code, 200)
        self.assertEqual(self.stranger.get(f'/result/{record.pk}/').status_code, 404)
        self.assertContains(self.owner.get('/history/'), 'private.png')
        self.assertNotContains(self.stranger.get('/history/'), 'private.png')

    def test_image_route_checks_owner_and_disables_caching(self):
        record = self.upload()
        response = self.owner.get(f'/image/{record.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertTrue(b''.join(response.streaming_content).startswith(b'\x89PNG'))
        response.close()
        self.assertEqual(self.stranger.get(f'/image/{record.pk}/').status_code, 404)
        with override_settings(DEBUG=True):
            self.assertEqual(self.owner.get(record.original_image.url).status_code, 404)
        self.assertIn('no-store', self.owner.get(f'/result/{record.pk}/')['Cache-Control'])

    def test_expired_records_are_not_accessible(self):
        record = self.upload()
        ImageCheck.objects.filter(pk=record.pk).update(uploaded_at=timezone.now() - timedelta(hours=25))
        self.assertEqual(self.owner.get(f'/result/{record.pk}/').status_code, 404)
        self.assertEqual(self.owner.get(f'/image/{record.pk}/').status_code, 404)
        self.assertNotContains(self.owner.get('/history/'), 'private.png')

    def test_legacy_records_are_not_public(self):
        record = ImageCheck.objects.create(original_filename='legacy-private.png', original_image='uploads/legacy.png')
        self.assertEqual(self.stranger.get(f'/result/{record.pk}/').status_code, 404)
        self.assertNotContains(self.stranger.get('/history/'), 'legacy-private.png')

    def test_external_analysis_requires_explicit_opt_in(self):
        self.upload()
        self.api.assert_not_called()
        record = self.upload(allow_external_analysis='on')
        self.api.assert_called_once()
        self.assertEqual(record.model_raw_response, {})

    def test_processing_errors_do_not_expose_internal_details(self):
        with patch('detector.views.run_local_analysis', side_effect=RuntimeError('sensitive-server-path')):
            record = self.upload()
        response = self.owner.get(f'/result/{record.pk}/')
        self.assertNotContains(response, 'sensitive-server-path')
        self.assertNotIn('sensitive-server-path', record.error_message)

    def test_upstream_errors_are_not_stored_or_shown(self):
        self.api.return_value = {'error': 'upstream', 'reasons': ['secret-upstream-body']}
        record = self.upload(allow_external_analysis='on')
        self.assertNotIn('secret-upstream-body', str(record.reasons))
        self.assertNotContains(self.owner.get(f'/result/{record.pk}/'), 'secret-upstream-body')

    def test_retention_cleanup_defaults_to_dry_run(self):
        expired = self.upload()
        fresh = self.upload()
        ImageCheck.objects.filter(pk=expired.pk).update(uploaded_at=timezone.now() - timedelta(hours=25))
        output = io.StringIO()
        call_command('purge_expired_analyses', stdout=output)
        self.assertTrue(ImageCheck.objects.filter(pk=expired.pk).exists())
        self.assertTrue(expired.original_image.storage.exists(expired.original_image.name))
        call_command('purge_expired_analyses', delete=True, stdout=output)
        self.assertFalse(ImageCheck.objects.filter(pk=expired.pk).exists())
        self.assertFalse(expired.original_image.storage.exists(expired.original_image.name))
        self.assertTrue(ImageCheck.objects.filter(pk=fresh.pk).exists())
        self.assertTrue(fresh.original_image.storage.exists(fresh.original_image.name))

    def test_owner_can_delete_with_valid_csrf_token(self):
        record = self.upload()
        client = Client(enforce_csrf_checks=True)
        client.cookies = self.owner.cookies
        client.get(f'/result/{record.pk}/')
        response = client.post(f'/delete/{record.pk}/', {
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ImageCheck.objects.filter(pk=record.pk).exists())

    def test_delete_is_owner_only_post_and_removes_file(self):
        record = self.upload()
        name, storage = record.original_image.name, record.original_image.storage
        self.assertEqual(self.owner.get(f'/delete/{record.pk}/').status_code, 405)
        self.assertEqual(self.stranger.post(f'/delete/{record.pk}/').status_code, 404)
        self.assertTrue(storage.exists(name))
        self.assertEqual(self.owner.post(f'/delete/{record.pk}/').status_code, 302)
        self.assertFalse(ImageCheck.objects.filter(pk=record.pk).exists())
        self.assertFalse(storage.exists(name))

    def test_delete_requires_csrf(self):
        record = self.upload()
        client = Client(enforce_csrf_checks=True)
        client.cookies = self.owner.cookies
        self.assertEqual(client.post(f'/delete/{record.pk}/').status_code, 403)
        self.assertTrue(ImageCheck.objects.filter(pk=record.pk).exists())

    def test_deleting_during_analysis_does_not_resurrect_record(self):
        self.upload()
        def finish_after_deletion(path):
            processing = ImageCheck.objects.latest('pk')
            self.assertEqual(self.owner.post(f'/delete/{processing.pk}/').status_code, 302)
            return {'metadata_score': 0, 'ela_score': 0, 'artifact_score': 0,
                    'details': {}, 'reasons': []}
        with patch('detector.views.run_local_analysis', side_effect=finish_after_deletion):
            self.upload()
        self.assertEqual(ImageCheck.objects.count(), 1)
