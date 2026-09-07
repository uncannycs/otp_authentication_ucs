# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestOTPGeneration(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = self.env['res.users'].create({
            'name': 'Test OTP User',
            'login': 'test_otp_user',
            'email': 'test_otp_user@example.com',
            'otp_enabled': True,
        })
        self.OtpModel = self.env['company.auth.otp']

    def test_otp_code_length_and_digits(self):
        """Test OTP generation yields numeric strings of exact requested lengths."""
        for length in [4, 6, 8]:
            code = self.OtpModel._generate_otp_code(length=length)
            self.assertEqual(len(code), length)
            self.assertTrue(code.isdigit())

    def test_otp_unpredictability(self):
        """Test multiple consecutive OTP code generations produce different tokens."""
        codes = {self.OtpModel._generate_otp_code(6) for _ in range(20)}
        self.assertGreater(len(codes), 15, "Generated OTP codes must be cryptographically random and unique.")

    def test_otp_salt_and_hash_storage(self):
        """Test OTP challenge stores salt and SHA-256 hash, never plaintext OTP."""
        challenge, otp_code = self.OtpModel._create_otp_challenge(self.user)
        self.assertIsNotNone(challenge.otp_hash)
        self.assertIsNotNone(challenge.otp_salt)
        self.assertNotEqual(challenge.otp_hash, otp_code)

        # Ensure plaintext code is not stored in any column
        fields_values = challenge.read()[0]
        for field, value in fields_values.items():
            self.assertNotEqual(str(value), otp_code, f"Plaintext OTP found stored in field {field}!")

    def test_missing_email_prevents_challenge(self):
        """Test creating OTP challenge for user without email raises UserError."""
        self.user.email = False
        with self.assertRaises(UserError):
            self.OtpModel._create_otp_challenge(self.user)
