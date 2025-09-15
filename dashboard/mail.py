from flask import g

import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import log


def send_email(email_receiver: str, email_subject: str, email_body_plain: str, email_body_html: str) -> str:
    email_sender = g.settings["smtp"]["SMTP_ADDRESS"]
    email_password = g.settings["smtp"]["SMTP_PASSWORD"]
    smtp_server = g.settings["smtp"]["SMTP_SERVER"]
    smtp_port = g.settings["smtp"]["SMTP_PORT"]
    if email_sender is None or email_password is None or smtp_server is None or smtp_port is None:
        print("SMTP variables not set in settings, couldn't send email!")
        log.write(msg="SMTP variables not set in settings, couldn't send email", level=log.error)
        return "SMTP variables not set in settings, couldn't send email!"
    em = MIMEMultipart("alternative")
    em['Subject'] = email_subject
    em['From'] = email_sender
    em['To'] = email_receiver

    msg1 = MIMEText(email_body_plain, "plain")
    msg2 = MIMEText(email_body_html, "html")
    em.attach(msg1)
    em.attach(msg2)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
        try:
            server.login(email_sender, email_password)
            try:
                server.sendmail(email_sender, email_receiver, em.as_string())
                response = f"Email to {email_receiver} sent."
                log.write(msg="Successfully sent email!", extra_info=f"Email to {email_receiver} sent", level=log.info)
            except:
                log.write(msg="Failed to send email",
                          extra_info=f"Sending email from {email_sender} failed!",
                          level=log.error)
                response = f"Sending email from {email_sender} failed!"
        except:
            log.write(msg="Failed to send email", extra_info=f"Login to SMTP {smtp_server} failed", level=log.error)
            response = f"Login to SMTP {smtp_server} failed!"
        return response
