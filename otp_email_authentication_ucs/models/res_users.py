# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, _
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    otp_enabled = fields.Boolean(
        string="Require OTP & Email Authentication",
        default=False,
        copy=False,
        help="Enables Email OTP verification for this user during login."
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['otp_enabled']

    def _mfa_type(self):
        """Hook into Odoo 18 MFA pipeline to declare email_otp type."""
        r = super()._mfa_type()
        if r is not None:
            return r

        ICP = self.env['ir.config_parameter'].sudo()
        global_enabled = ICP.get_param('otp_email_authentication_ucs.enable_otp_login', 'False').lower() in ('true', '1')

        # Check if user has OTP enabled and global setting is active
        if global_enabled and self.sudo().otp_enabled:
            return 'email_otp'

        return None

    def _mfa_url(self):
        """Return verification URL for email_otp MFA type."""
        r = super()._mfa_url()
        if r is not None:
            return r

        if self._mfa_type() == 'email_otp':
            return '/web/otp/verify'

        return None

    def _rpc_api_keys_only(self):
        """Password-based RPC authentication disabled when OTP is active for the user."""
        return self._mfa_type() == 'email_otp' or super()._rpc_api_keys_only()

    def _check_credentials(self, credentials, env):
        """Validate credentials for email_otp MFA type."""
        if isinstance(credentials, dict) and credentials.get('type') == 'email_otp':
            user = self.sudo()
            token = credentials.get('token')
            challenge_id = credentials.get('challenge_id')

            domain = [('user_id', '=', user.id), ('state', '=', 'pending')]
            if challenge_id:
                domain.append(('id', '=', int(challenge_id)))

            challenge = env['company.auth.otp'].sudo().search(domain, limit=1)
            if not challenge or not challenge._verify_otp(token):
                _logger.warning("Email OTP verification failed for user %s", user.login)
                raise AccessDenied(_("Invalid verification code."))

            challenge.sudo().write({
                'state': 'verified',
                'verified_at': fields.Datetime.now(),
            })

            _logger.info("Email OTP verified successfully for user %s", user.login)
            return {
                'uid': self.env.user.id,
                'auth_method': 'email_otp',
                'mfa': 'default',
            }

        return super()._check_credentials(credentials, env)
