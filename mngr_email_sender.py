import os
from dotenv import load_dotenv
from pydantic import EmailStr

from email_service.email_sender import EmailSender

# SMTP Credentials (to be passed dynamically)


# Initialize email sender
load_dotenv()
email_sender = EmailSender(smtp_server=os.getenv("SMTP_ADDR"),
                           smtp_port=int(os.getenv("SMTP_PORT")),
                           smtp_username=os.getenv("MAIL_LGIN"),
                           smtp_password=os.getenv("MAIL_PSSW"))


# Define email details
sender = "register@cadenabitcoin.com"
recipient = "szillerke@gmail.com"
subject = "Test-Email"
template_path = "./email_service/templates/default_email.txt"  # Path to email text file


template_vars = {"user": "User of Mine",
                 "website": "https://sziller.eu"}


if __name__ == "__main__":
    # Send email
    email_sender.send_email(sender=sender,
                            recipient=recipient,
                            subject=subject,
                            template_path=template_path,
                            **template_vars)
    
