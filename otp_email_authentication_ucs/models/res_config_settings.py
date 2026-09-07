# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_otp_login = fields.Boolean(
        string="Enable OTP & Email Authentication",
        config_parameter='otp_email_authentication_ucs.enable_otp_login',
        default=False,
        help="Global setting to activate Email OTP authentication on login."
    )
    otp_length = fields.Selection(
        selection=[
            ('4', '4 Digits'),
            ('6', '6 Digits'),
            ('8', '8 Digits'),
        ],
        string="OTP Code Length",
        config_parameter='otp_email_authentication_ucs.otp_length',
        default='6',
        required=True,
        help="Number of digits in the generated OTP code."
    )
    otp_expiration_minutes = fields.Integer(
        string="OTP Expiration",
        config_parameter='otp_email_authentication_ucs.otp_expiration_minutes',
        default=1,
        help="Time in minutes before an issued OTP code expires."
    )
    otp_resend_cooldown = fields.Integer(
        string="Resend Cooldown",
        config_parameter='otp_email_authentication_ucs.otp_resend_cooldown',
        default=60,
        help="Cooldown period in seconds before a user can request another OTP code."
    )
    otp_max_attempts = fields.Integer(
        string="Maximum Verification Attempts",
        config_parameter='otp_email_authentication_ucs.otp_max_attempts',
        default=5,
        help="Maximum allowed invalid OTP code attempts before the challenge is invalidated."
    )
    otp_max_resend = fields.Integer(
        string="Maximum Resend Attempts",
        config_parameter='otp_email_authentication_ucs.otp_max_resend',
        default=3,
        help="Maximum times a user can resend an OTP code per authentication session."
    )
