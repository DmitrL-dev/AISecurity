"""
SafeClaw Router — SSRF Protection Tests.

SEC-09: Validates that SSRF protection correctly
blocks private IPs, metadata endpoints, and
non-HTTP schemes.
"""

from django.test import TestCase

from router.ssrf_protection import (
    is_safe_url,
    validate_provider_url,
)


class SSRFProtectionTest(TestCase):
    """Test SSRF protection for provider URLs."""

    # --- Safe URLs ---

    def test_https_public_url_safe(self):
        self.assertTrue(is_safe_url("https://api.openai.com/v1"))

    def test_http_public_url_safe(self):
        self.assertTrue(is_safe_url("http://api.example.com/v1"))

    def test_public_ip_safe(self):
        self.assertTrue(is_safe_url("https://8.8.8.8/api"))

    # --- Blocked: Private IPs ---

    def test_blocks_localhost(self):
        self.assertFalse(is_safe_url("http://127.0.0.1:5432/"))

    def test_blocks_10_network(self):
        self.assertFalse(is_safe_url("http://10.0.0.1/api"))

    def test_blocks_172_16_network(self):
        self.assertFalse(is_safe_url("http://172.16.0.1/api"))

    def test_blocks_192_168_network(self):
        self.assertFalse(is_safe_url("http://192.168.1.1/api"))

    # --- Blocked: Cloud metadata ---

    def test_blocks_aws_metadata(self):
        self.assertFalse(is_safe_url("http://169.254.169.254/latest/"))

    def test_blocks_alibaba_metadata(self):
        self.assertFalse(is_safe_url("http://100.100.100.200/latest/"))

    # --- Blocked: Non-HTTP schemes ---

    def test_blocks_ftp(self):
        self.assertFalse(is_safe_url("ftp://evil.com/file"))

    def test_blocks_file(self):
        self.assertFalse(is_safe_url("file:///etc/passwd"))

    def test_blocks_gopher(self):
        self.assertFalse(is_safe_url("gopher://evil.com/"))

    # --- Blocked: Edge cases ---

    def test_blocks_empty_url(self):
        self.assertFalse(is_safe_url(""))

    def test_blocks_no_scheme(self):
        self.assertFalse(is_safe_url("evil.com/api"))

    def test_blocks_loopback_ipv6(self):
        self.assertFalse(is_safe_url("http://[::1]/api"))

    # --- validate_provider_url ---

    def test_validate_raises_on_unsafe(self):
        with self.assertRaises(ValueError):
            validate_provider_url("http://169.254.169.254/latest/")

    def test_validate_returns_safe_url(self):
        url = "https://api.openai.com/v1"
        self.assertEqual(validate_provider_url(url), url)
