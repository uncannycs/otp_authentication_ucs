# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import logging
import secrets
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CompanyAuthOtp(models.Model):
    _name = 'company.auth.otp'
    _description = 'OTP & Email Authentication Request'
    _order = 'id desc'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        index=True
    )
    email = fields.Char(
        string='Recipient Email',
        required=True
    )
    otp_hash = fields.Char(
        string='OTP Hash',
        required=True,
        groups='base.group_system'
    )
    otp_salt = fields.Char(
        string='OTP Salt',
        required=True,
        groups='base.group_system'
    )
    created_at = fields.Datetime(
        string='Created At',
        default=fields.Datetime.now,
        required=True
    )
    expires_at = fields.Datetime(
        string='Expires At',
        required=True,
        index=True
    )
    verified_at = fields.Datetime(
        string='Verified At'
    )
    attempts = fields.Integer(
        string='Verification Attempts',
        default=0,
        required=True
    )
    max_attempts = fields.Integer(
        string='Maximum Attempts',
        default=5,
        required=True
    )
    resend_count = fields.Integer(
        string='Resend Count',
        default=0,
        required=True
    )
    last_sent_at = fields.Datetime(
        string='Last Sent At',
        default=fields.Datetime.now,
        required=True
    )
    ip_address = fields.Char(
        string='IP Address'
    )
    user_agent = fields.Char(
        string='User Agent'
    )
    session_identifier = fields.Char(
        string='Session Identifier'
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], string='State', default='pending', required=True, index=True)

    @api.model
    def _generate_otp_code(self, length=6):
        """Generate a cryptographically secure numeric OTP string of specified length."""
        valid_lengths = [4, 6, 8]
        if length not in valid_lengths:
            length = 6
        digits = '0123456789'
        return ''.join(secrets.choice(digits) for _ in range(length))

    @api.model
    def _hash_otp(self, otp_code, salt):
        """Compute SHA-256 hash of OTP code with given salt."""
        payload = f"{salt}:{otp_code}".encode('utf-8')
        return hashlib.sha256(payload).hexdigest()

    @api.model
    def _create_otp_challenge(self, user, session_identifier=None, ip_address=None, user_agent=None):
        """Create a secure OTP challenge for the given user.
        
        Returns:
            tuple: (company.auth.otp record, plain_otp_code string)
        """
        if not user.email or not user.email.strip():
            raise UserError(_("User does not have a valid email address configured."))

        ICP = self.env['ir.config_parameter'].sudo()
        try:
            length = int(ICP.get_param('otp_email_authentication_ucs.otp_length', '6'))
        except ValueError:
            length = 6

        try:
            exp_minutes = int(ICP.get_param('otp_email_authentication_ucs.otp_expiration_minutes', '1'))
        except ValueError:
            exp_minutes = 1

        try:
            max_attempts = int(ICP.get_param('otp_email_authentication_ucs.otp_max_attempts', '5'))
        except ValueError:
            max_attempts = 5

        # Cancel existing pending challenges for user
        domain = [('user_id', '=', user.id), ('state', '=', 'pending')]
        if session_identifier:
            domain.append(('session_identifier', '=', session_identifier))
        existing_challenges = self.sudo().search(domain)
        if existing_challenges:
            existing_challenges.write({'state': 'cancelled'})

        # Generate secure random code and salt
        otp_code = self._generate_otp_code(length=length)
        salt = secrets.token_hex(16)
        otp_hash = self._hash_otp(otp_code, salt)

        now = fields.Datetime.now()
        expires_at = now + timedelta(minutes=exp_minutes)

        challenge = self.sudo().create({
            'user_id': user.id,
            'email': user.email.strip(),
            'otp_hash': otp_hash,
            'otp_salt': salt,
            'created_at': now,
            'expires_at': expires_at,
            'max_attempts': max_attempts,
            'last_sent_at': now,
            'ip_address': ip_address or '',
            'user_agent': user_agent or '',
            'session_identifier': session_identifier or '',
            'state': 'pending',
        })

        return challenge, otp_code

    def _verify_otp(self, candidate_token):
        """Verify if the provided candidate OTP matches the challenge securely."""
        self.ensure_one()
        if self.state != 'pending':
            return False

        if fields.Datetime.now() > self.expires_at:
            self.sudo().write({'state': 'expired'})
            return False

        candidate_hash = self._hash_otp(str(candidate_token).strip(), self.otp_salt)
        return secrets.compare_digest(candidate_hash, self.otp_hash)

    def _is_expired(self):
        """Check if challenge has expired."""
        self.ensure_one()
        return fields.Datetime.now() > self.expires_at

    @api.model
    def _cron_cleanup_otp_records(self, days=7):
        """Cron job to clean up old OTP challenge records."""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        records = self.sudo().search([
            ('created_at', '<', cutoff_date),
            ('state', 'in', ['verified', 'expired', 'failed', 'cancelled'])
        ])
        _logger.info("Cleaning up %s expired/completed OTP challenge records.", len(records))
        records.unlink()
