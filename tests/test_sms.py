import os
import unittest
from unittest.mock import Mock, patch

from messaging.sms import send_sms


class SmsTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "TWILIO_ACCOUNT_SID": "ACtest",
            "TWILIO_AUTH_TOKEN": "test-token",
            "TWILIO_FROM_NUMBER": "+15005550006",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_missing_credentials_fails_closed(self):
        for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"):
            os.environ.pop(key, None)
        result = send_sms("+2348012345678", "SILKOUS test")
        self.assertFalse(result.sent)
        self.assertIn("not configured", result.message)

    def test_invalid_destination_fails_closed(self):
        result = send_sms("08012345678", "SILKOUS test")
        self.assertFalse(result.sent)
        self.assertIn("E.164", result.message)

    def test_empty_message_fails_closed(self):
        result = send_sms("+2348012345678", "   ")
        self.assertFalse(result.sent)
        self.assertIn("empty", result.message)

    @patch("messaging.sms.requests.post")
    def test_successful_provider_acceptance(self, mock_post):
        mock_post.return_value = Mock(status_code=201)
        result = send_sms("+2348012345678", "SILKOUS setup test")
        self.assertTrue(result.sent)
        self.assertIn("accepted by provider", result.message)
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.kwargs["timeout"], 12)

    @patch("messaging.sms.requests.post")
    def test_provider_rejection_is_not_reported_as_sent(self, mock_post):
        mock_post.return_value = Mock(status_code=400)
        result = send_sms("+2348012345678", "SILKOUS setup test")
        self.assertFalse(result.sent)
        self.assertIn("HTTP 400", result.message)


if __name__ == "__main__":
    unittest.main()
