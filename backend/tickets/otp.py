from django.conf import settings
from django.core.mail import send_mail


def send_otp_email(user, code: str) -> None:
    send_mail(
        subject='Your TriagePilot verification code',
        message=(
            f"Hi {user.username},\n\n"
            f"Your TriagePilot verification code is: {code}\n\n"
            "It expires in 10 minutes. If you didn't request this, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
