# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime, timedelta

from odoo import fields, http, _
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request
from odoo.addons.web.controllers import home as web_home

_logger = logging.getLogger(__name__)


def mask_email(email):
    """Mask email address for privacy display (e.g. lo****@company.com)."""
    if not email or '@' not in email:
        return '****@****'
    name, domain = email.split('@', 1)
    if len(name) <= 2:
        masked_name = name[0] + '*' * 3
    else:
        masked_name = name[:2] + '*' * (len(name) - 2)
    return f"{masked_name}@{domain}"


class AuthOTPController(web_home.Home):

    def _get_otp_config(self):
        """Retrieve module configuration settings."""
        ICP = request.env['ir.config_parameter'].sudo()
        try:
            length = int(ICP.get_param('otp_email_authentication_ucs.otp_length', '6'))
        except ValueError:
            length = 6

        try:
            exp_minutes = int(ICP.get_param('otp_email_authentication_ucs.otp_expiration_minutes', '1'))
        except ValueError:
            exp_minutes = 1

        try:
            cooldown = int(ICP.get_param('otp_email_authentication_ucs.otp_resend_cooldown', '60'))
        except ValueError:
            cooldown = 60

        try:
            max_attempts = int(ICP.get_param('otp_email_authentication_ucs.otp_max_attempts', '5'))
        except ValueError:
            max_attempts = 5

        try:
            max_resend = int(ICP.get_param('otp_email_authentication_ucs.otp_max_resend', '3'))
        except ValueError:
            max_resend = 3

        return {
            'length': length,
            'expiration_minutes': exp_minutes,
            'cooldown_seconds': cooldown,
            'max_attempts': max_attempts,
            'max_resend': max_resend,
        }

    def _send_otp_email(self, user, challenge, otp_code):
        """Send OTP verification code to user registered email via mail.template."""
        template = request.env.ref('otp_email_authentication_ucs.email_template_auth_otp', raise_if_not_found=False)
        if not template:
            _logger.error("Email template otp_email_authentication_ucs.email_template_auth_otp not found!")
            return False

        try:
            email_values = {
                'email_to': user.email.strip(),
            }
            ctx = {
                'otp_code': otp_code,
                'exp_minutes': challenge.sudo().expires_at,
                'user_name': user.name,
            }
            template.sudo().with_context(**ctx).send_mail(
                challenge.id,
                force_send=True,
                email_values=email_values,
                email_layout_xmlid='mail.mail_notification_light'
            )
            return True
        except Exception as e:
            _logger.exception("Failed to send Email OTP to user %s: %s", user.login, str(e))
            return False

    @http.route(
        '/web/otp/verify',
        type='http', auth='public', methods=['GET', 'POST'], sitemap=False,
        website=True, csrf=True
    )
    def web_otp_verify(self, redirect=None, **kwargs):
        if request.session.uid:
            return request.redirect(self._login_redirect(request.session.uid, redirect=redirect))

        pre_uid = request.session.get('pre_uid')
        if not pre_uid:
            return request.redirect('/web/login')

        user = request.env['res.users'].sudo().browse(pre_uid)
        if not user.exists():
            return request.redirect('/web/login')

        ip_address = request.httprequest.remote_addr or ''
        user_agent = request.httprequest.user_agent.string if request.httprequest.user_agent else ''

        # Email validation check
        if not user.email or not user.email.strip():
            request.env['auth.otp.log']._log_event(
                user, 'auth_failed', 'failure',
                ip_address=ip_address, user_agent=user_agent,
                failure_reason=_("User account does not have a valid email configured.")
            )
            error_msg = _("Email OTP authentication is enabled for your account, but no valid email address is configured. Please contact your administrator.")
            return request.render('otp_email_authentication_ucs.otp_error_page', {
                'error': error_msg,
                'user': user,
            })

        config = self._get_otp_config()
        challenge_model = request.env['company.auth.otp'].sudo()
        log_model = request.env['auth.otp.log'].sudo()

        # Find existing active pending challenge
        challenge = challenge_model.search([
            ('user_id', '=', user.id),
            ('state', '=', 'pending')
        ], limit=1)

        error = kwargs.get('error')
        notice = kwargs.get('notice')

        # GET request handling
        if request.httprequest.method == 'GET':
            if not challenge or challenge._is_expired():
                if challenge and challenge._is_expired():
                    challenge.write({'state': 'expired'})
                    log_model._log_event(
                        user, 'otp_expired', 'failure',
                        ip_address=ip_address, user_agent=user_agent
                    )

                try:
                    challenge, otp_code = challenge_model._create_otp_challenge(
                        user,
                        session_identifier=request.session.sid,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    log_model._log_event(
                        user, 'otp_generated', 'success',
                        ip_address=ip_address, user_agent=user_agent
                    )
                    sent = self._send_otp_email(user, challenge, otp_code)
                    if sent:
                        log_model._log_event(
                            user, 'otp_sent', 'success',
                            ip_address=ip_address, user_agent=user_agent
                        )
                    else:
                        log_model._log_event(
                            user, 'email_failed', 'failure',
                            ip_address=ip_address, user_agent=user_agent,
                            failure_reason=_("Mail server delivery failure.")
                        )
                        error = _("We could not send the verification email. Please contact your administrator.")
                except Exception as e:
                    _logger.exception("Error generating OTP challenge for user %s: %s", user.login, str(e))
                    error = _("Could not generate OTP challenge. Please contact your administrator.")

        # POST request handling (Submission of OTP token)
        elif request.httprequest.method == 'POST' and kwargs.get('otp_token'):
            submitted_otp = kwargs.get('otp_token', '').strip()

            if not challenge:
                error = _("This verification code has expired. Please request a new code.")
            elif challenge._is_expired():
                challenge.write({'state': 'expired'})
                log_model._log_event(
                    user, 'otp_expired', 'failure',
                    ip_address=ip_address, user_agent=user_agent
                )
                error = _("This verification code has expired. Please request a new code.")
            elif challenge.attempts >= challenge.max_attempts:
                challenge.write({'state': 'failed'})
                log_model._log_event(
                    user, 'max_attempts_exceeded', 'failure',
                    ip_address=ip_address, user_agent=user_agent,
                    attempt_count=challenge.attempts
                )
                error = _("Too many verification attempts. Please request a new verification code.")
            else:
                if challenge._verify_otp(submitted_otp):
                    # Verification Success!
                    challenge.write({
                        'state': 'verified',
                        'verified_at': request.env.cr.now(),
                    })
                    log_model._log_event(
                        user, 'otp_verified', 'success',
                        ip_address=ip_address, user_agent=user_agent
                    )

                    # Finalize session into fully authenticated Odoo session
                    request.session.finalize(request.env)
                    request.update_env(user=request.session.uid)
                    request.update_context(**request.session.context)

                    return request.redirect(self._login_redirect(request.session.uid, redirect=redirect))
                else:
                    # Invalid OTP Attempt
                    challenge.attempts += 1
                    log_model._log_event(
                        user, 'invalid_otp', 'failure',
                        ip_address=ip_address, user_agent=user_agent,
                        attempt_count=challenge.attempts
                    )

                    if challenge.attempts >= challenge.max_attempts:
                        challenge.write({'state': 'failed'})
                        log_model._log_event(
                            user, 'max_attempts_exceeded', 'failure',
                            ip_address=ip_address, user_agent=user_agent,
                            attempt_count=challenge.attempts
                        )
                        error = _("Too many verification attempts. Please request a new verification code.")
                    else:
                        remaining = challenge.max_attempts - challenge.attempts
                        error = _("Invalid verification code. You have %s remaining attempt(s).") % remaining

        # Calculate cooldown seconds for resend button
        cooldown_remaining = 0
        if challenge and challenge.last_sent_at:
            elapsed = (fields.Datetime.now() - challenge.last_sent_at).total_seconds()
            if elapsed < config['cooldown_seconds']:
                cooldown_remaining = int(config['cooldown_seconds'] - elapsed)

        request.session.touch()
        return request.render('otp_email_authentication_ucs.otp_verification_form', {
            'user': user,
            'masked_email': mask_email(user.email),
            'otp_length': config['length'],
            'otp_expiration_minutes': config['expiration_minutes'],
            'cooldown_seconds': config['cooldown_seconds'],
            'cooldown_remaining': cooldown_remaining,
            'max_resend': config['max_resend'],
            'resend_count': challenge.resend_count if challenge else 0,
            'error': error,
            'notice': notice,
            'redirect': redirect,
        })

    @http.route(
        '/web/otp/resend',
        type='http', auth='public', methods=['POST'], sitemap=False,
        website=True, csrf=True
    )
    def web_otp_resend(self, redirect=None, **kwargs):
        if request.session.uid:
            return request.redirect(self._login_redirect(request.session.uid, redirect=redirect))

        pre_uid = request.session.get('pre_uid')
        if not pre_uid:
            return request.redirect('/web/login')

        user = request.env['res.users'].sudo().browse(pre_uid)
        if not user.exists() or not user.email:
            return request.redirect('/web/login')

        ip_address = request.httprequest.remote_addr or ''
        user_agent = request.httprequest.user_agent.string if request.httprequest.user_agent else ''

        config = self._get_otp_config()
        challenge_model = request.env['company.auth.otp'].sudo()
        log_model = request.env['auth.otp.log'].sudo()

        challenge = challenge_model.search([
            ('user_id', '=', user.id),
            ('state', 'in', ['pending', 'expired', 'failed'])
        ], limit=1)

        # Check resend cooldown
        if challenge and challenge.last_sent_at:
            elapsed = (fields.Datetime.now() - challenge.last_sent_at).total_seconds()
            if elapsed < config['cooldown_seconds']:
                error_msg = _("Please wait before requesting another verification code.")
                return request.redirect_query('/web/otp/verify', query={'error': error_msg, 'redirect': redirect})

        # Check max resend limit
        resend_count = challenge.resend_count if challenge else 0
        if resend_count >= config['max_resend']:
            error_msg = _("Maximum resend attempts reached. Please contact your administrator or try logging in again.")
            return request.redirect_query('/web/otp/verify', query={'error': error_msg, 'redirect': redirect})

        try:
            new_challenge, otp_code = challenge_model._create_otp_challenge(
                user,
                session_identifier=request.session.sid,
                ip_address=ip_address,
                user_agent=user_agent
            )
            new_challenge.write({'resend_count': resend_count + 1})

            log_model._log_event(
                user, 'otp_resent', 'success',
                ip_address=ip_address, user_agent=user_agent
            )

            sent = self._send_otp_email(user, new_challenge, otp_code)
            if sent:
                notice_msg = _("A new verification code has been sent to your registered email address.")
                return request.redirect_query('/web/otp/verify', query={'notice': notice_msg, 'redirect': redirect})
            else:
                log_model._log_event(
                    user, 'email_failed', 'failure',
                    ip_address=ip_address, user_agent=user_agent,
                    failure_reason=_("Resend mail delivery failed.")
                )
                error_msg = _("We could not send the verification email. Please contact your administrator.")
                return request.redirect_query('/web/otp/verify', query={'error': error_msg, 'redirect': redirect})

        except Exception as e:
            _logger.exception("Failed to resend OTP for user %s: %s", user.login, str(e))
            error_msg = _("Could not generate a new verification code.")
            return request.redirect_query('/web/otp/verify', query={'error': error_msg, 'redirect': redirect})
