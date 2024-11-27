import os
from dotenv import load_dotenv
from email.message import EmailMessage
import ssl
import smtplib

load_dotenv()

email_sender = os.getenv("SMTP_ADDRESS")
email_password = os.getenv("SMTP_PASSWORD")
smtp_server = os.getenv("SMTP_SERVER")
smtp_port = os.getenv("SMTP_PORT")

def send_email(to, subject, body):
    email_receiver = to
    email_subject = subject
    email_body = body
    response = "N/A"

    em=EmailMessage()
    em['From'] = email_sender
    em['To'] = email_receiver
    em['Subject'] = email_subject
    em.set_content(email_body)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
        try:
            server.login(email_sender, email_password)
            try:
                server.sendmail(email_sender, email_receiver, em.as_string())
                response = "Email to "+email_receiver+" sent."
            except:
                response = "Sending email from "+email_sender+" failed!"
        except:
            response = "Login to SMTP "+smtp_server+" failed!"
        return response
