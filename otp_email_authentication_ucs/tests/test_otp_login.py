# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessDenied


class TestOTPLoginFlow(TransactionCase):

    def setUp(self):
        super().setUp()
        self.user = self.env['res.users'].create({
            'name': 'Test Login Flow User',
            'login': 'test_login_flow',
            'email': 'loginflow@example.com',
            'otp_enabled': True,
        })
        self.ICP = self.env['ir.config_parameter'].sudo()
        self.OtpModel = self.env['company.auth.otp']

    def test_activation_rules(self):
        """Test activation matrix logic (Global OTP & User OTP settings)."""
        # Case 1: Global OTP Disabled
        self.ICP.set_param('otp_email_authentication_ucs.enable_otp_login', 'False')
        self.user.otp_enabled = True
        self.assertIsNone(self.user._mfa_type())
        self.assertIsNone(self.user._mfa_url())

        # Case 2: Global OTP Enabled + User OTP Disabled
        self.ICP.set_param('otp_email_authentication_ucs.enable_otp_login', 'True')
        self.user.otp_enabled = False
        self.assertIsNone(self.user._mfa_type())
        self.assertIsNone(self.user._mfa_url())

        # Case 3: Global OTP Enabled + User OTP Enabled
        self.user.otp_enabled = True
        self.assertEqual(self.user._mfa_type(), 'email_otp')
        self.assertEqual(self.user._mfa_url(), '/web/otp/verify')

    def test_check_credentials_email_otp(self):
        """Test res.users._check_credentials for email_otp type."""
        self.ICP.set_param('otp_email_authentication_ucs.enable_otp_login', 'True')
        challenge, plain_otp = self.OtpModel._create_otp_challenge(self.user)

        # Valid token
        res = self.user._check_credentials({'type': 'email_otp', 'token': plain_otp, 'challenge_id': challenge.id}, self.env)
        self.assertEqual(res['auth_method'], 'email_otp')
        self.assertEqual(challenge.state, 'verified')

        # Invalid token
        challenge2, plain_otp2 = self.OtpModel._create_otp_challenge(self.user)
        with self.assertRaises(AccessDenied):
            self.user._check_credentials({'type': 'email_otp', 'token': '000000', 'challenge_id': challenge2.id}, self.env)
