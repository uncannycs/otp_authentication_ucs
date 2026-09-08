# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'OTP & Email Authentication | Email OTP Authentication | OTP Authentication | Email Authentication | Two-Factor Authentication (2FA)',
    'version': '18.0.1.0.0',
    'category': 'Authentication / Security',
    'summary': 'Secure OTP & Email Authentication / Two-Factor Authentication (2FA) for Odoo 18',
    'description': """
OTP & Email Authentication
================================

Adds secure Email-based One-Time Password (OTP) verification to the Odoo 18 login pipeline.

Key Features:
-------------
* Secure 2FA login verification via registered email.
* Configurable OTP length (4, 6, 8 digits).
* Configurable expiration window, resend cooldown, maximum attempt limits, and maximum resend limits.
* Global toggle and per-user activation options.
* Plaintext OTP never stored in database or logged (SHA-256 with per-challenge salt).
* Responsive OTP verification interface with focus auto-advance and countdown timer.
* Comprehensive audit logging and scheduled cleanup.
    """,
    'author': 'Uncanny Consulting Services LLP',
    'website': 'https://www.uncannycs.com',
    'license': 'Other proprietary',
    'depends': [
        'base',
        'web',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/otp_request_views.xml',
        'views/otp_log_views.xml',
        'views/otp_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'otp_email_authentication_ucs/static/src/css/otp_login.css',
            'otp_email_authentication_ucs/static/src/js/otp_login.js',
        ],
    },
    'images': [
        'static/description/banner.gif',
    ],
    'price': 60,
    'currency': 'USD',
    'installable': True,
    'application': True,
    'auto_install': False,
}
