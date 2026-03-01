# Platform/api/app/services/email_service.py
"""
Transactional email service via SendGrid.

If SENDGRID_API_KEY is not set, emails are logged instead of sent
(safe for local dev).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
_FROM_EMAIL = os.getenv("FROM_EMAIL", "no-reply@apterfinancial.com")
_FROM_NAME = os.getenv("FROM_NAME", "Apter Financial")


def _send_via_sendgrid(to_email: str, subject: str, html_body: str) -> bool:
    """Send an email via the SendGrid v3 API. Returns True on success."""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content

        message = Mail(
            from_email=Email(_FROM_EMAIL, _FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_body),
        )

        sg = SendGridAPIClient(_SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in (200, 201, 202):
            logger.info("Email sent to %s (status %s)", to_email, response.status_code)
            return True

        logger.warning(
            "SendGrid returned %s for %s: %s",
            response.status_code, to_email, response.body,
        )
        return False

    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """
    Send a password reset email. Falls back to logging if SendGrid
    is not configured.
    """
    subject = "Reset your Apter Financial password"

    html_body = f"""\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px;">
  <div style="margin-bottom: 24px;">
    <strong style="font-size: 16px;">Apter Financial</strong>
  </div>
  <h2 style="font-size: 20px; font-weight: 600; margin: 0 0 12px;">Reset your password</h2>
  <p style="color: #6b7280; font-size: 14px; line-height: 1.6; margin: 0 0 24px;">
    We received a request to reset the password for your account. Click the button
    below to choose a new password. This link expires in 15 minutes.
  </p>
  <a href="{reset_url}"
     style="display: inline-block; background: #111827; color: #ffffff; text-decoration: none;
            padding: 12px 24px; border-radius: 6px; font-size: 14px; font-weight: 500;">
    Reset Password
  </a>
  <p style="color: #9ca3af; font-size: 12px; line-height: 1.6; margin: 24px 0 0;">
    If you didn&rsquo;t request this, you can safely ignore this email. Your password
    will not change.
  </p>
  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;" />
  <p style="color: #9ca3af; font-size: 11px;">
    Apter Financial &mdash; Analytical signals only. Not investment advice.
  </p>
</div>"""

    if not _SENDGRID_API_KEY:
        logger.warning(
            "SENDGRID_API_KEY not set — password reset email NOT sent to %s. "
            "Reset URL: %s",
            to_email, reset_url,
        )
        return False

    return _send_via_sendgrid(to_email, subject, html_body)
