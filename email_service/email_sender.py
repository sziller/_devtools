from __future__ import annotations

import smtplib
import asyncio
import inspect
import os
import re
import html as html_unescape
import logging
from typing import Optional, List, Dict, Tuple

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pydantic import BaseModel, ValidationError

# Setting up logger                                         logger                      -   START   -
lg = logging.getLogger(__name__)
# Setting up logger                                         logger                      -   ENDED   -


class EmailPayload(BaseModel):
    sender: str
    recipient: str
    subject: str
    template_path: str
    attachments: Optional[List[str]] = None
    template_vars: Optional[Dict[str, str]] = None


class EmailSender:
    """Class to manage emails (HTML/Text with proper multipart handling)."""
    ccn = inspect.currentframe().f_code.co_name

    def __init__(self,
                 smtp_server: str,
                 smtp_port: int,
                 smtp_username: str,
                 smtp_password: str):
        """
        Initialize the EmailSender with dynamic SMTP server settings.

        :param smtp_server: SMTP server address
        :param smtp_port: SMTP server port (587 for STARTTLS, 465 for implicit SSL)
        :param smtp_username: SMTP username
        :param smtp_password: SMTP password
        """
        self.smtp_server: str = smtp_server
        self.smtp_port: int = smtp_port
        self.smtp_username: str = smtp_username
        self.smtp_password: str = smtp_password

    # ------------------------ Template utils ------------------------

    @staticmethod
    def _infer_is_html_from_path_or_content(path: str, content: str) -> bool:
        """Infer HTML-ness from extension or simple tag checks."""
        if os.path.splitext(path)[1].lower() == ".html":
            return True
        lc = content.lower()
        return ("<html" in lc) or ("<body" in lc) or ("</" in content and "<" in content)

    @staticmethod
    def _html_to_text(html_str: str) -> str:
        """Lightweight HTML→plain conversion (no external deps)."""
        # strip scripts/styles
        html_str = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", html_str)
        # replace <br> and block endings with newlines
        html_str = re.sub(r"(?i)<br\s*/?>", "\n", html_str)
        html_str = re.sub(r"(?i)</(p|div|section|article|h\d|li|tr|table)>", "\n", html_str)
        # remove all tags
        text = re.sub(r"(?s)<.*?>", "", html_str)
        # unescape entities
        text = html_unescape.unescape(text)
        # collapse excessive blank lines/spaces
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()
        return text

    @staticmethod
    def _load_template(template_path: str, **kwargs: str) -> Tuple[str, bool]:
        """
        Loads and formats a template file.

        Returns:
            (rendered_content, is_html)
        """
        if not os.path.exists(template_path):
            lg.error(f"Template file not found: {template_path}")
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(template_path, "r", encoding="utf-8") as file:
            template_content = file.read()

        try:
            rendered = template_content.format(**kwargs)
            is_html = EmailSender._infer_is_html_from_path_or_content(template_path, rendered)
            return rendered, is_html
        except KeyError as e:
            lg.error(f"Missing placeholder value for: {e}")
            raise ValueError(f"Missing placeholder value for: {e}")

    # ------------------------ MIME building ------------------------

    @staticmethod
    def _attach_attachments(container: MIMEMultipart, attachments: Optional[List[str]]) -> None:
        if not attachments:
            return
        for file_path in attachments:
            if not file_path or not os.path.exists(file_path):
                lg.error(f"Attachment not found, skipping: {file_path}")
                continue
            try:
                with open(file_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{os.path.basename(file_path)}"'
                    )
                    container.attach(part)
            except Exception as e:
                lg.error(f"Error attaching file {file_path}: {e}")

    @staticmethod
    def _build_message(sender: str,
                       recipient: str,
                       subject: str,
                       body_text: Optional[str],
                       body_html: Optional[str],
                       attachments: Optional[List[str]],
                       headers: Optional[Dict[str, str]]) -> MIMEMultipart:
        """
        Construct the correct MIME structure:

        - If attachments exist → multipart/mixed
            - First part: either multipart/alternative (text + html) or a single text/html or text/plain
            - Then attachments
        - If no attachments:
            - If both text and html → multipart/alternative
            - Else single-part (we still return a multipart container for consistency)
        """
        has_attachments = bool(attachments)
        has_text = body_text is not None
        has_html = body_html is not None

        # Default headers (let email package set MIME-Version/Content-Type on parts/containers)
        default_headers = {
            "Reply-To": "info@cadenabitcoin.com",
            "List-Unsubscribe": "<https://purabitcoin.com/unsubscribe>",
            "Precedence": "bulk",
            "Auto-Submitted": "auto-generated",
        }
        headers = {**default_headers, **(headers or {})}

        # Choose outer container
        if has_attachments:
            outer = MIMEMultipart("mixed")
        else:
            outer = MIMEMultipart("alternative" if (has_text and has_html) else "mixed")

        outer["From"] = sender
        outer["To"] = recipient
        outer["Subject"] = subject
        for k, v in headers.items():
            outer[k] = v

        def _as_text_part(text_val: str) -> MIMEText:
            return MIMEText(text_val or "", "plain", _charset="utf-8")

        def _as_html_part(html_val: str) -> MIMEText:
            return MIMEText(html_val or "", "html", _charset="utf-8")

        # Build body
        if has_text and has_html:
            alt = MIMEMultipart("alternative")
            alt.attach(_as_text_part(body_text))
            alt.attach(_as_html_part(body_html))
            outer.attach(alt)
        else:
            if has_text:
                outer.attach(_as_text_part(body_text))
            elif has_html:
                outer.attach(_as_html_part(body_html))
            else:
                outer.attach(_as_text_part("(no content)"))  # Safety net

        # Attach files
        if has_attachments:
            EmailSender._attach_attachments(outer, attachments)

        return outer

    # ------------------------ SMTP transport ------------------------

    def _send_via_smtp(self, sender: str, recipient: str, msg: MIMEMultipart) -> None:
        """Send the prepared message over SMTP with SSL/STARTTLS as appropriate."""
        if self.smtp_port == 465:
            # Implicit SSL
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(sender, recipient, msg.as_string())
        else:
            # STARTTLS
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(sender, recipient, msg.as_string())

    # ------------------------ Public API ------------------------

    def send_email(self,
                   sender: str,
                   recipient: str,
                   subject: str,
                   template_path: str,
                   attachments: Optional[List[str]] = None,
                   headers: Optional[Dict[str, str]] = None,
                   *,
                   template_path_html: Optional[str] = None,
                   use_html: bool = False,
                   **template_vars):
        """
        Sends an email synchronously using templates with HTML/Text selection and fallback.

        Args:
            sender, recipient, subject: obvious.
            template_path: path to the plain-text template (also used as TXT fallback).
            attachments: optional file paths.
            headers: additional headers (merged with defaults).
            template_path_html: path to the HTML template (optional).
            use_html: if True, prefer HTML and send multipart/alternative (HTML + TXT) when possible.
            **template_vars: dynamic placeholders for .format().
        """
        cmn = inspect.currentframe().f_code.co_name

        # Guard: ensure bools like use_html do not leak into template_vars
        template_vars.pop("use_html", None)

        # Ensure EmailPayload.template_vars are strings (model expects Dict[str, str])
        template_vars = {k: (v if isinstance(v, str) else str(v))
                         for k, v in (template_vars or {}).items()}

        # Prepare bodies
        body_text: Optional[str] = None
        body_html: Optional[str] = None

        try:
            if use_html and template_path_html:
                # Try HTML first
                try:
                    rendered_html, is_html = self._load_template(template_path_html, **template_vars)
                    if not is_html:
                        lg.warning(f"HTML template didn't look like HTML: {template_path_html}")
                    body_html = rendered_html
                except Exception as e:
                    lg.error(f"Failed to render HTML template '{template_path_html}': {e}. Will try TXT fallback.")

                # TXT part for multipart/alternative (if TXT exists)
                if os.path.exists(template_path):
                    try:
                        rendered_txt, txt_is_html = self._load_template(template_path, **template_vars)
                        body_text = rendered_txt if not txt_is_html else self._html_to_text(rendered_txt)
                    except Exception as e:
                        lg.error(f"Failed to render TXT template '{template_path}': {e}. Will derive from HTML if possible.")

                # If no explicit TXT or it failed, derive from HTML
                if body_text is None and body_html:
                    body_text = self._html_to_text(body_html)

                # If HTML failed entirely, fallback to TXT only
                if body_html is None:
                    if os.path.exists(template_path):
                        rendered_txt, txt_is_html = self._load_template(template_path, **template_vars)
                        if txt_is_html:
                            body_html = rendered_txt
                            body_text = self._html_to_text(rendered_txt)
                        else:
                            body_text = rendered_txt
                    else:
                        raise FileNotFoundError("Neither HTML nor TXT template could be loaded.")
            else:
                # Text-first / legacy path
                rendered, is_html = self._load_template(template_path, **template_vars)
                if is_html:
                    body_html = rendered
                    body_text = self._html_to_text(rendered)
                else:
                    body_text = rendered

            # Build payload (template_path is kept for compatibility/logging; use provided TXT path)
            try:
                payload = EmailPayload(
                    sender=sender,
                    recipient=recipient,
                    subject=subject,
                    template_path=template_path,
                    attachments=attachments or [],
                    template_vars=template_vars or {}
                )
            except ValidationError as e:
                lg.error(f"Invalid email data: {e}")
                raise ValueError("Email validation failed")

            # Build message with proper MIME structure
            msg = self._build_message(
                sender=payload.sender,
                recipient=payload.recipient,
                subject=payload.subject,
                body_text=body_text,
                body_html=body_html,
                attachments=payload.attachments,
                headers=headers
            )

            # Send
            self._send_via_smtp(payload.sender, payload.recipient, msg)
            lg.info(f"send email: successfully to: {payload.recipient:>53} - says {cmn} at {self.ccn}")

        except smtplib.SMTPAuthenticationError as e:
            lg.error(f"Authentication failed: {e}. Ensure SMTP authentication is enabled.")
        except smtplib.SMTPException as e:
            lg.error(f"SMTP error occurred: {e}")
        except Exception as e:
            lg.error(f"Unexpected error: {e}")

    async def send_email_async(self,
                               sender: str,
                               recipient: str,
                               subject: str,
                               template_path: str,
                               attachments: Optional[List[str]] = None,
                               headers: Optional[Dict[str, str]] = None,
                               *,
                               template_path_html: Optional[str] = None,
                               use_html: bool = False,
                               **template_vars) -> None:
        """
        Asynchronous version of send_email.

        :param recipient: Recipient email address
        :param subject: Email subject
        :param template_path: Path to the plain-text template (and TXT fallback)
        :param sender: Sender email address
        :param attachments: List of file paths to attach (optional)
        :param headers: Additional headers
        :param template_path_html: Optional path to HTML template
        :param use_html: Prefer HTML + TXT multipart when True
        :param template_vars: Dynamic values to insert into the email template
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.send_email(
                sender=sender,
                recipient=recipient,
                subject=subject,
                template_path=template_path,
                attachments=attachments,
                headers=headers,
                template_path_html=template_path_html,  # NEW
                use_html=use_html,                      # NEW
                **template_vars
            )
        )
