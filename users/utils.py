from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_email(
    to_email,
    subject,
    template_name,
    context=None,
    text_content=None,
):
    """
    Global email sender
    """

    context = context or {}

    # Render HTML template
    html_content = render_to_string(template_name, context)

    # Optional plain text fallback
    if not text_content:
        text_content = "Please view this email in an HTML-supported client."

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )

    msg.attach_alternative(html_content, "text/html")
    msg.send()
def send_credentials_email(email, password):
    subject = "Your Kigali Microloans Account"

    html_content = render_to_string(
        "emails/credentials.html",
        {"email": email, "password": password}
    )

    msg = EmailMultiAlternatives(
        subject,
        "",
        settings.DEFAULT_FROM_EMAIL,
        [email]
    )

    msg.attach_alternative(html_content, "text/html")
    msg.send()