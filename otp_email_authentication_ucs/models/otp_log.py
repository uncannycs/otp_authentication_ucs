# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AuthOtpLog(models.Model):
    _name = 'auth.otp.log'
    _description = 'OTP & Email Authentication Audit Log'
    _order = 'id desc'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        index=True
    )
    date = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now,
        required=True,
        index=True
    )
    ip_address = fields.Char(
        string='IP Address'
    )
    user_agent = fields.Char(
        string='User Agent'
    )
    event = fields.Selection([
        ('otp_generated', 'OTP Generated'),
        ('otp_sent', 'OTP Sent'),
        ('otp_resent', 'OTP Resent'),
        ('otp_verified', 'OTP Verified'),
        ('invalid_otp', 'Invalid OTP Attempt'),
        ('otp_expired', 'OTP Expired'),
        ('max_attempts_exceeded', 'Maximum Attempts Exceeded'),
        ('auth_failed', 'Authentication Failed'),
        ('email_failed', 'Email Sending Failed')
    ], string='Event', required=True, index=True)

    result = fields.Selection([
        ('success', 'Success'),
        ('failure', 'Failure')
    ], string='Result', required=True)

    failure_reason = fields.Text(
        string='Failure Reason'
    )
    attempt_count = fields.Integer(
        string='Attempt Count',
        default=0
    )

    @api.model
    def _log_event(self, user, event, result, ip_address=None, user_agent=None, failure_reason=None, attempt_count=0):
        """Create a security audit log record without sensitive token data."""
        if not user:
            return False

        return self.sudo().create({
            'user_id': user.id,
            'date': fields.Datetime.now(),
            'ip_address': ip_address or '',
            'user_agent': user_agent or '',
            'event': event,
            'result': result,
            'failure_reason': failure_reason or '',
            'attempt_count': attempt_count,
        })

    @api.model
    def _cron_cleanup_audit_logs(self, days=90):
        """Cron job to clean up audit logs older than retention period."""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        logs = self.sudo().search([('date', '<', cutoff_date)])
        _logger.info("Cleaning up %s old OTP audit log records.", len(logs))
        logs.unlink()
