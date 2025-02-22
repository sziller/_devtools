import smtplib
import asyncio
import os
import logging
from typing import Optional, List, Dict
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
    """Class to manage emails"""

    def __init__(self,
                 smtp_server: str,
                 smtp_port: int,
                 smtp_username: str,
                 smtp_password: str):
        """
        Initialize the EmailSender with dynamic SMTP server settings.

        :param smtp_server: SMTP server address
        :param smtp_port: SMTP server port (587 for TLS, 465 for SSL)
        :param smtp_username: SMTP username
        :param smtp_password: SMTP password
        """
        self.smtp_server: str = smtp_server
        self.smtp_port: int = smtp_port
        self.smtp_username: str = smtp_username
        self.smtp_password: str = smtp_password

    @staticmethod
    def _build_email(payload: EmailPayload, body: str, headers: Optional[Dict[str, str]] = None) -> MIMEMultipart:
        """Constructs the email message with optional attachments and headers."""
        msg = MIMEMultipart()
        msg["From"] = payload.sender
        msg["To"] = payload.recipient
        msg["Subject"] = payload.subject

        # Add Anti-Spam Headers
        default_headers = {
            "Reply-To": "info@cadenabitcoin.com",
            "MIME-Version": "1.0",
            "Content-Type": "text/html; charset=UTF-8",
            "List-Unsubscribe": "<https://purabitcoin.com/unsubscribe>",
            "Precedence": "bulk",
            "Auto-Submitted": "auto-generated"
        }

        headers = headers or {}
        for key, value in {**default_headers, **headers}.items():
            msg[key] = value

        msg.attach(MIMEText(body, "html"))  # Ensure HTML emails are sent properly

        if payload.attachments:
            for file_path in payload.attachments:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header("Content-Disposition",
                                            f'attachment; filename="{os.path.basename(file_path)}"')
                            msg.attach(part)
                    except Exception as e:
                        lg.error(f"Error attaching file {file_path}: {e}")

        return msg

    @staticmethod
    def _load_template(template_path: str, **kwargs: str) -> str:
        """Loads and formats an email template from a file, auto-converting plaintext to HTML."""
        if not os.path.exists(template_path):
            lg.error(f"Template file not found: {template_path}")
            raise FileNotFoundError(f"Template file not found: {template_path}")

        with open(template_path, "r", encoding="utf-8") as file:
            template_content = file.read()

        try:
            formatted_content = template_content.format(**kwargs)

            # Auto-detect if it's plain text and convert to HTML
            if "<html" not in formatted_content and "<body" not in formatted_content:
                formatted_content = formatted_content.replace("\n", "<br>")  # Convert newlines to <br>
                formatted_content = f"<html><body>{formatted_content}</body></html>"  # Wrap in HTML structure

            return formatted_content
        except KeyError as e:
            lg.error(f"Missing placeholder value for: {e}")
            raise ValueError(f"Missing placeholder value for: {e}")

    def send_email(self,
                   sender: str,
                   recipient: str,
                   subject: str,
                   template_path: str,
                   attachments: Optional[List[str]] = None,
                   headers: Optional[Dict[str, str]] = None,
                   **template_vars):
        """
        Sends an email synchronously using a template with STARTTLS support.

        :param recipient: Recipient email address
        :param subject: Email subject
        :param template_path: Path to the email template file
        :param sender: Sender email address
        :param attachments: List of file paths to attach (optional)
        :param template_vars: Dynamic values to insert into the email template
        """
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

        body = self._load_template(payload.template_path, **payload.template_vars)
        msg = self._build_email(payload, body, headers)

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.smtp_username, self.smtp_password)

                server.sendmail(str(payload.sender),
                                str(payload.recipient),
                                msg.as_string())
                lg.info(f"Email successfully sent to {payload.recipient}")

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
                               **template_vars: str) -> None:
        """
        Asynchronous version of send_email.

        :param recipient: Recipient email address
        :param subject: Email subject
        :param template_path: Path to the email template file
        :param sender: Sender email address
        :param attachments: List of file paths to attach (optional)
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
                **template_vars
            )
        )
        
