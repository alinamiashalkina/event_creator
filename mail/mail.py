from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

from jinja2 import Template
from dotenv import load_dotenv
import os

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.environ["MAIL_USERNAME"],
    MAIL_PASSWORD=os.environ["MAIL_PASSWORD"],
    MAIL_FROM=os.environ["MAIL_FROM"],
    MAIL_PORT=int(os.environ["MAIL_PORT"]),
    MAIL_SERVER=os.environ["MAIL_SERVER"],
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    MAIL_DEBUG=0,
    TEMPLATE_FOLDER="mail/templates",
)

fm = FastMail(conf)


async def send_email(to: str, subject: str, template_name: str, context: dict):
    template_path = f"{conf.TEMPLATE_FOLDER}/{template_name}"
    with open(template_path, "r", encoding="utf-8") as file:
        template = Template(file.read())
    html_content = template.render(**context)

    message = MessageSchema(
        subject=subject,
        recipients=[to],
        body=html_content,
        subtype="html"
    )

    await fm.send_message(message)
