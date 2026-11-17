from django.conf import settings
from django.core.mail import send_mail


def send_account_activation_email(email, email_token):
    subject = 'My_Ecommerce.'
    email_from = settings.EMAIL_HOST_USER
    message = f"Hi, click on the link to activate your account {settings.SITE_URL}/account/activate/{email_token}"
    send_mail(subject, message, email_from, [email], fail_silently=False)


def send_success_email(email, email_token=None):
    subject = 'Your payment was successful.'
    email_from = settings.EMAIL_HOST_USER
    message = "Thanks for using our services."
    send_mail(subject, message, email_from, [email], fail_silently=False)