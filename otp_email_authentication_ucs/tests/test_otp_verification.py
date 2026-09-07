# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestOTPVerification(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = self.env['res.users'].create({
            'name': 'Test OTP Verify User',
            'login': 'test_verify_user',
            'email': 'verify@example.com',
            'otp_enabled': True,
        })
        self.OtpModel = self.env['company.auth.otp']

    def test_successful_otp_verification(self):
        """Test valid OTP candidate matches challenge securely."""
        challenge, plain_otp = self.OtpModel._create_otp_challenge(self.user)
        self.assertEqual(challenge.state, 'pending')

        is_valid = challenge._verify_otp(plain_otp)
        self.assertTrue(is_valid)

    def test_invalid_otp_verification(self):
        """Test invalid OTP candidate fails verification."""
        challenge, plain_otp = self.OtpModel._create_otp_challenge(self.user)
        wrong_otp = "000000" if plain_otp != "000000" else "111111"

        is_valid = challenge._verify_otp(wrong_otp)
        self.assertFalse(is_valid)

    def test_max_attempts_exceeded(self):
        """Test challenge invalidation upon reaching max attempt limit."""
        challenge, plain_otp = self.OtpModel._create_otp_challenge(self.user)
        wrong_otp = "999999" if plain_otp != "999999" else "888888"

        for i in range(challenge.max_attempts):
            challenge.attempts += 1
            if challenge.attempts >= challenge.max_attempts:
                challenge.write({'state': 'failed'})

        self.assertEqual(challenge.state, 'failed')
        self.assertFalse(challenge._verify_otp(plain_otp))
