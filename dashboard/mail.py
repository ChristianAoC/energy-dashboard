from flask import current_app

import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import log


def send_email(email_receiver, email_subject, email_body_plain, email_body_html):
    email_sender = current_app.config["SMTP_ADDRESS"]
    email_password = current_app.config["SMTP_PASSWORD"]
    smtp_server = current_app.config["SMTP_SERVER"]
    smtp_port = current_app.config["SMTP_PORT"]
    if email_sender == None or email_password == None or smtp_server == None or smtp_port == None:
        print("SMTP variables not set in .env, couldn't send email!")
        log.create_log(msg="SMTP variables not set in .env, couldn't send email", level=log.error)
        return "SMTP variables not set in .env, couldn't send email!"
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
                response = "Email to "+email_receiver+" sent."
            except:
                response = "Sending email from "+email_sender+" failed!"
        except:
            response = "Login to SMTP "+smtp_server+" failed!"
        return response
