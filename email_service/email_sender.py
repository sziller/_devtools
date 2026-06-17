"""=== Module: email_sender.py ================================================================================
Low-level email transport and MIME-construction utility.

=== Purpose ===
This module provides the shared infrastructure layer for application-generated emails.
It is intentionally placed below the business/use-case email functions such as:

- `send_registration_email(...)`
- `send_reregistration_email(...)`
- `send_post_offer_email(...)`
- `send_accept_offer_user_email(...)`

Those higher-level functions decide:
- *why* an email is being sent,
- which templates to use,
- which placeholders to pass,
- which sender identity / subject / headers apply.

This module decides:
- how templates are loaded and rendered,
- how HTML and TXT bodies are prepared,
- how the MIME tree is constructed,
- how SMTP transport is performed,
- how sync sending is exposed through an async wrapper.

=== Scope ===
This module is responsible for:

1. Template loading and `str.format(...)` rendering
2. HTML/TXT detection and fallback handling
3. MIME construction for:
   - TXT-only mails
   - HTML+TXT multipart/alternative mails
   - attachment-bearing multipart/mixed mails
4. SMTP transport over:
   - STARTTLS
   - implicit SSL
5. Exception propagation so higher-level orchestration may:
   - retry,
   - switch to fallback providers,
   - centralize error handling and logging

=== Architectural Position ===
Typical runtime flow:

    endpoint / periodic task
        -> business-specific `send_...` function
            -> `email_mngr.send_email_async(...)`
                -> `EmailSender.send_email_async(...)`
                    -> `EmailSender.send_email(...)`
                        -> template rendering
                        -> MIME construction
                        -> SMTP send

This module therefore acts as the **lowest common email engine** used by the application.

=== Design Notes ===
- The module is intentionally generic and business-agnostic.
- It should not know what a “registration” or “DLC acceptance” email means.
- It should raise on failures instead of swallowing them silently.
  This is crucial when the application wants to try one provider first
  (e.g. Resend) and fall back to another one (e.g. Office365).
- MIME trees are built conservatively to maximize compatibility with stricter
  clients such as Outlook.

=== MIME Rules Implemented ===
1. No attachments, text + html:
   - `multipart/alternative`
     - `text/plain`
     - `text/html`

2. With attachments, text + html:
   - `multipart/mixed`
     - `multipart/alternative`
       - `text/plain`
       - `text/html`
     - attachment(s)

3. Single body only:
   - single-body message wrapped in a simple multipart container for consistency

=== Important Compatibility Concern ===
A previous implementation incorrectly produced a double-nested
`multipart/alternative` structure in the common HTML+TXT / no-attachments case.
Some forgiving clients (such as Gmail) still rendered such emails acceptably,
while stricter clients (notably Outlook) could mis-handle the message and show
the plain body while exposing the HTML part as an attachment or separate file.

This module is intended to avoid that malformed structure.

=== Provider Strategy ===
This module represents a single concrete SMTP sender.

It is designed so that higher layers may later compose:
- one primary sender (e.g. Resend),
- one fallback sender (e.g. Office365),
- and a lightweight wrapper/orchestrator that tries primary first and falls back on error.

That fallback logic should generally live **above** this module, not inside each
business-specific email use-case.

=== by Sziller ===
============================================================================================================"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import re
import smtplib
from typing import Optional, List, Dict, Tuple, Any

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pydantic import BaseModel, ValidationError

# -------------------------------------------------------------------------------------------------
# Logger
# -------------------------------------------------------------------------------------------------
lg = logging.getLogger(__name__)


# -------------------------------------------------------------------------------------------------
# Models
# -------------------------------------------------------------------------------------------------
class EmailPayload(BaseModel):
    sender: str
    recipient: str
    subject: str
    template_path: str
    attachments: Optional[List[str]] = None
    template_vars: Optional[Dict[str, str]] = None


# -------------------------------------------------------------------------------------------------
# Sender
# -------------------------------------------------------------------------------------------------
class EmailSender:
    """=== Class: EmailSender =============================================================================
    Low-level email sender handling:

    - template loading and rendering
    - HTML/TXT fallback preparation
    - MIME construction
    - SMTP transport
    - async wrapper over sync sending

    Design goals
    ------------
    - Keep business/use-case email functions thin.
    - Raise on transport/render/send failures so higher layers may:
        * retry,
        * fall back to another provider,
        * log centrally.
    - Build MIME trees correctly for strict mail clients (e.g. Outlook).

    MIME structure
    --------------
    1) No attachments, text + html:
       multipart/alternative
         - text/plain
         - text/html

    2) With attachments, text + html:
       multipart/mixed
         - multipart/alternative
             - text/plain
             - text/html
         - attachment(s)

    3) Single body only:
       multipart/mixed
         - text/plain or text/html

    ==================================================================================== by Sziller ===
    """

    ccn = inspect.currentframe().f_code.co_name

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        *,
        timeout: int = 30,
        use_starttls: Optional[bool] = None,
        use_ssl: Optional[bool] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        """=== Init =======================================================================================
        :param smtp_server: SMTP host
        :param smtp_port: SMTP port
        :param smtp_username: SMTP login username
        :param smtp_password: SMTP login password
        :param timeout: socket timeout in seconds
        :param use_starttls:
            - None  -> infer from port
            - True  -> force STARTTLS
            - False -> do not STARTTLS
        :param use_ssl:
            - None  -> infer from port
            - True  -> implicit SSL (SMTP_SSL)
            - False -> plain SMTP object
        :param default_headers: optional default headers merged into every outgoing email
        ========================================================================================== """
        self.smtp_server: str = smtp_server
        self.smtp_port: int = int(smtp_port)
        self.smtp_username: str = smtp_username
        self.smtp_password: str = smtp_password
        self.timeout: int = int(timeout)

        # Inference rules
        self.use_ssl: bool = (self.smtp_port == 465) if use_ssl is None else bool(use_ssl)
        self.use_starttls: bool = (
            (not self.use_ssl and self.smtp_port in {587, 2525})
            if use_starttls is None
            else bool(use_starttls)
        )

        self.default_headers: Dict[str, str] = {
            "Reply-To": "info@cadenabitcoin.com",
            "List-Unsubscribe": "<https://purabitcoin.com/unsubscribe>",
            "Precedence": "bulk",
            "Auto-Submitted": "auto-generated",
            **(default_headers or {}),
        }

    # ==============================================================================================
    # Template utils
    # ==============================================================================================
    @staticmethod
    def _infer_is_html_from_path_or_content(path: str, content: str) -> bool:
        """Infer whether a rendered template is HTML."""
        if os.path.splitext(path)[1].lower() == ".html":
            return True

        lc = content.lower()
        return (
            "<html" in lc
            or "<body" in lc
            or ("</" in lc and "<" in lc)
        )

    @staticmethod
    def _html_to_text(html_str: str) -> str:
        """Very lightweight HTML -> plain-text conversion without third-party deps."""
        if not html_str:
            return ""

        # Drop script/style blocks
        html_str = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", html_str)

        # Common block-ish boundaries -> newlines
        html_str = re.sub(r"(?i)<br\s*/?>", "\n", html_str)
        html_str = re.sub(
            r"(?i)</(p|div|section|article|h\d|li|tr|table|ul|ol|header|footer|blockquote)>",
            "\n",
            html_str,
        )

        # Strip remaining tags
        text = re.sub(r"(?s)<.*?>", "", html_str)

        # Unescape entities
        import html
        text = html.unescape(text)

        # Normalize whitespace
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)

        return text.strip()

    @staticmethod
    def _stringify_template_vars(template_vars: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Convert template vars to str values for predictable .format() behavior."""
        return {
            str(k): (v if isinstance(v, str) else str(v))
            for k, v in (template_vars or {}).items()
        }

    @staticmethod
    def _load_template(template_path: str, **kwargs: str) -> Tuple[str, bool]:
        """=== Method: _load_template =========================================================================
        Load and render a template file using `str.format(**kwargs)`.

        :returns:
            tuple[str, bool] -> (rendered_content, is_html)
        ================================================================================================ """
        if not template_path:
            raise ValueError("Template path is empty.")

        if not os.path.exists(template_path):
            lg.error(f"Template file not found: {template_path}")
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(template_path, "r", encoding="utf-8") as file:
            template_content = file.read()

        try:
            rendered = template_content.format(**kwargs)
        except KeyError as e:
            lg.error(f"Missing placeholder value for: {e}")
            raise ValueError(f"Missing placeholder value for: {e}") from e

        is_html = EmailSender._infer_is_html_from_path_or_content(template_path, rendered)
        return rendered, is_html

    def _prepare_bodies(
        self,
        *,
        template_path: str,
        template_path_html: Optional[str],
        use_html: bool,
        template_vars: Dict[str, str],
    ) -> Tuple[Optional[str], Optional[str]]:
        """Resolve final TXT/HTML bodies with fallback logic."""
        body_text: Optional[str] = None
        body_html: Optional[str] = None

        if use_html and template_path_html:
            # 1) Try HTML template first
            try:
                rendered_html, is_html = self._load_template(template_path_html, **template_vars)
                if not is_html:
                    lg.warning(f"HTML template did not look like HTML: {template_path_html}")
                body_html = rendered_html
            except Exception as e:
                lg.error(
                    f"Failed to render HTML template '{template_path_html}': {e}. "
                    f"Will try TXT fallback."
                )

            # 2) Try TXT template for the plain alternative part
            if template_path and os.path.exists(template_path):
                try:
                    rendered_txt, txt_is_html = self._load_template(template_path, **template_vars)
                    body_text = rendered_txt if not txt_is_html else self._html_to_text(rendered_txt)
                except Exception as e:
                    lg.error(
                        f"Failed to render TXT template '{template_path}': {e}. "
                        f"Will derive TXT from HTML if possible."
                    )

            # 3) If TXT not available, derive from HTML
            if body_text is None and body_html is not None:
                body_text = self._html_to_text(body_html)

            # 4) If HTML completely failed, fallback to TXT-only
            if body_html is None:
                if template_path and os.path.exists(template_path):
                    rendered_txt, txt_is_html = self._load_template(template_path, **template_vars)
                    if txt_is_html:
                        body_html = rendered_txt
                        body_text = self._html_to_text(rendered_txt)
                    else:
                        body_text = rendered_txt
                else:
                    raise FileNotFoundError("Neither HTML nor TXT template could be loaded.")

        else:
            # Legacy / text-first path
            rendered, is_html = self._load_template(template_path, **template_vars)
            if is_html:
                body_html = rendered
                body_text = self._html_to_text(rendered)
            else:
                body_text = rendered

        return body_text, body_html

    # ==============================================================================================
    # MIME building
    # ==============================================================================================
    @staticmethod
    def _as_text_part(text_val: str) -> MIMEText:
        return MIMEText(text_val or "", "plain", _charset="utf-8")

    @staticmethod
    def _as_html_part(html_val: str) -> MIMEText:
        return MIMEText(html_val or "", "html", _charset="utf-8")

    @staticmethod
    def _attach_attachments(container: MIMEMultipart, attachments: Optional[List[str]]) -> None:
        """Attach files to a multipart/mixed container."""
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
                        f'attachment; filename="{os.path.basename(file_path)}"',
                    )
                    container.attach(part)
            except Exception as e:
                lg.error(f"Error attaching file {file_path}: {e}")
                raise

    def _build_message(
        self,
        *,
        sender: str,
        recipient: str,
        subject: str,
        body_text: Optional[str],
        body_html: Optional[str],
        attachments: Optional[List[str]],
        headers: Optional[Dict[str, str]],
    ) -> MIMEMultipart:
        """=== Method: _build_message =========================================================================
        Build a standards-friendly MIME structure.

        Important:
        - NO double-nested multipart/alternative for the simple text+html case.
        - Attachments force outer multipart/mixed.
        ================================================================================================ """
        has_attachments = bool(attachments)
        has_text = body_text is not None
        has_html = body_html is not None

        merged_headers = {**self.default_headers, **(headers or {})}

        # ---------- Case 1: attachments -> outer mixed ----------
        if has_attachments:
            outer = MIMEMultipart("mixed")
            outer["From"] = sender
            outer["To"] = recipient
            outer["Subject"] = subject

            for k, v in merged_headers.items():
                outer[k] = v

            if has_text and has_html:
                alt = MIMEMultipart("alternative")
                alt.attach(self._as_text_part(body_text))
                alt.attach(self._as_html_part(body_html))
                outer.attach(alt)
            elif has_text:
                outer.attach(self._as_text_part(body_text))
            elif has_html:
                outer.attach(self._as_html_part(body_html))
            else:
                outer.attach(self._as_text_part("(no content)"))

            self._attach_attachments(outer, attachments)
            return outer

        # ---------- Case 2: no attachments, both text+html ----------
        if has_text and has_html:
            outer = MIMEMultipart("alternative")
            outer["From"] = sender
            outer["To"] = recipient
            outer["Subject"] = subject

            for k, v in merged_headers.items():
                outer[k] = v

            outer.attach(self._as_text_part(body_text))
            outer.attach(self._as_html_part(body_html))
            return outer

        # ---------- Case 3: no attachments, single body ----------
        outer = MIMEMultipart("mixed")
        outer["From"] = sender
        outer["To"] = recipient
        outer["Subject"] = subject

        for k, v in merged_headers.items():
            outer[k] = v

        if has_text:
            outer.attach(self._as_text_part(body_text))
        elif has_html:
            outer.attach(self._as_html_part(body_html))
        else:
            outer.attach(self._as_text_part("(no content)"))

        return outer

    # ==============================================================================================
    # SMTP transport
    # ==============================================================================================
    def _send_via_smtp(self, *, sender: str, recipient: str, msg: MIMEMultipart) -> None:
        """Send a fully prepared MIME message over SMTP."""
        if self.use_ssl:
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=self.timeout) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(sender, recipient, msg.as_string())
            return

        with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.timeout) as server:
            server.ehlo()

            if self.use_starttls:
                server.starttls()
                server.ehlo()

            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(sender, recipient, msg.as_string())

    # ==============================================================================================
    # Public API
    # ==============================================================================================
    def send_email(
        self,
        sender: str,
        recipient: str,
        subject: str,
        template_path: str,
        attachments: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        *,
        template_path_html: Optional[str] = None,
        use_html: bool = False,
        **template_vars,
    ) -> None:
        """=== Method: send_email ============================================================================
        Synchronous email send with TXT / HTML fallback support.

        Important behavior
        ------------------
        - Raises on failure.
        - Does NOT swallow SMTP/template/render errors.
        - Higher layers may catch these and attempt fallback provider logic.
        ================================================================================================ """
        cmn = inspect.currentframe().f_code.co_name

        # Prevent accidental leakage into template vars
        template_vars.pop("use_html", None)

        template_vars_str = self._stringify_template_vars(template_vars)

        try:
            payload = EmailPayload(
                sender=sender,
                recipient=recipient,
                subject=subject,
                template_path=template_path,
                attachments=attachments or [],
                template_vars=template_vars_str,
            )
        except ValidationError as e:
            lg.error(f"Invalid email payload: {e}")
            raise ValueError("Email validation failed") from e

        try:
            body_text, body_html = self._prepare_bodies(
                template_path=template_path,
                template_path_html=template_path_html,
                use_html=use_html,
                template_vars=payload.template_vars or {},
            )

            msg = self._build_message(
                sender=payload.sender,
                recipient=payload.recipient,
                subject=payload.subject,
                body_text=body_text,
                body_html=body_html,
                attachments=payload.attachments,
                headers=headers,
            )

            self._send_via_smtp(
                sender=payload.sender,
                recipient=payload.recipient,
                msg=msg,
            )

            lg.info(
                f"send email: successfully to: {payload.recipient:>53} "
                f"- says {cmn} at {self.ccn}"
            )

        except smtplib.SMTPAuthenticationError as e:
            lg.error(
                f"Authentication failed for SMTP server={self.smtp_server}:{self.smtp_port} | {e}"
            )
            raise
        except smtplib.SMTPException as e:
            lg.error(
                f"SMTP error on server={self.smtp_server}:{self.smtp_port} "
                f"recipient={recipient}: {e}"
            )
            raise
        except Exception as e:
            lg.error(
                f"Unexpected email error on server={self.smtp_server}:{self.smtp_port} "
                f"recipient={recipient}: {e}"
            )
            raise

    async def send_email_async(
        self,
        sender: str,
        recipient: str,
        subject: str,
        template_path: str,
        attachments: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        *,
        template_path_html: Optional[str] = None,
        use_html: bool = False,
        **template_vars,
    ) -> None:
        """Async wrapper around `send_email()` using a thread executor."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self.send_email(
                sender=sender,
                recipient=recipient,
                subject=subject,
                template_path=template_path,
                attachments=attachments,
                headers=headers,
                template_path_html=template_path_html,
                use_html=use_html,
                **template_vars,
            ),
        )
