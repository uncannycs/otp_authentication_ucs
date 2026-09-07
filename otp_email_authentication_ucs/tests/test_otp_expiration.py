# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase


class TestOTPExpiration(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = self.env['res.users'].create({
            'name': 'Test Expiry User',
            'login': 'test_expiry_user',
            'email': 'expiry@example.com',
            'otp_enabled': True,
        })
        self.OtpModel = self.env['company.auth.otp']

    def test_otp_valid_before_expiry(self):
        """Test challenge is valid prior to expiry timestamp."""
        challenge, plain_otp = self.OtpModel._create_otp_challenge(self.user)
        self.assertFalse(challenge._is_expired())
        self.assertTrue(challenge._verify_otp(plain_otp))

    def test_otp_invalid_after_expiry(self):
        """Test challenge becomes invalid post expiry timestamp."""
        challenge, plain_otp = self.OtpModel._create_otp_challenge(self.user)

        # Force expiration in past
        past_time = fields.Datetime.now() - timedelta(minutes=5)
        challenge.sudo().write({'expires_at': past_time})

        self.assertTrue(challenge._is_expired())
        self.assertFalse(challenge._verify_otp(plain_otp))
        self.assertEqual(challenge.state, 'expired')
