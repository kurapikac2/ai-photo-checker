import math
import unittest
from unittest.mock import Mock, patch

from detector.services.openrouter_client import _normalize_percentage, _run_openrouter_once


class OpenRouterParsingTests(unittest.TestCase):
    def test_nonfinite_values_fall_back_to_zero(self):
        for value in (math.nan, math.inf, -math.inf, 10**1000):
            self.assertEqual(_normalize_percentage(value), 0)

    @patch('detector.services.openrouter_client.requests.post')
    def test_malformed_model_fields_are_sanitized(self, post):
        response = Mock(ok=True)
        response.json.return_value = {'choices': [{'message': {'content':
            '{"verdict":"unknown","confidence":"NaN","reasons":{"secret":"body"},'
            '"visual_signs":["  valid tag  ",42],"ai_generation_probability":"Infinity"}'
        }}]}
        post.return_value = response
        result = _run_openrouter_once('encoded', 'key')
        self.assertEqual(result['verdict'], 'uncertain')
        self.assertEqual(result['confidence'], 0)
        self.assertEqual(result['ai_generation_probability'], 0)
        self.assertEqual(result['reasons'], [])
        self.assertEqual(result['visual_signs'], ['valid tag'])
        self.assertNotIn('raw', result)
        self.assertNotIn('raw_text', result)

    @patch('detector.services.openrouter_client.requests.post')
    def test_non_string_verdict_keeps_other_valid_fields(self, post):
        response = Mock(ok=True)
        response.json.return_value = {'choices': [{'message': {'content':
            '{"verdict":[],"confidence":25,"reasons":["visible detail"]}'
        }}]}
        post.return_value = response
        result = _run_openrouter_once('encoded', 'key')
        self.assertEqual(result['verdict'], 'uncertain')
        self.assertEqual(result['confidence'], 25)
        self.assertEqual(result['reasons'], ['visible detail'])

    @patch('detector.services.openrouter_client.requests.post')
    def test_http_failure_does_not_reveal_upstream_body(self, post):
        post.return_value = Mock(ok=False, status_code=502, text='secret-upstream-body')
        result = _run_openrouter_once('encoded', 'key')
        self.assertEqual(result['error'], 'openrouter_failure')
        self.assertNotIn('secret-upstream-body', str(result))

    @patch('detector.services.openrouter_client.requests.post')
    def test_transport_error_does_not_reveal_exception(self, post):
        post.side_effect = RuntimeError('private-request-context')
        result = _run_openrouter_once('encoded', 'key')
        self.assertEqual(result['error'], 'openrouter_failure')
        self.assertNotIn('private-request-context', str(result))


if __name__ == '__main__':
    unittest.main()
