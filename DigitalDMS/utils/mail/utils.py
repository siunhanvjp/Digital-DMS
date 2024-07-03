import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.mail.backends.smtp import EmailBackend


LOGGER = logging.getLogger(__name__)

EMAIL_USER = settings.EMAIL_HOST_USER
EMAIL_PASSWORD = settings.EMAIL_HOST_PASSWORD


class EmailThread(threading.Thread):
    def __init__(
        self,
        subject,
        body,
        recipients,
        sender,
        messages,
        port_number,
        timeout,
        use_tls,
        send_type="normal",
        auth_user=None,
        auth_password=None,
        provider=None,
        bcc=None,
        cc=None,
    ):
        self.subject = subject
        self.recipients = recipients
        self.body = body
        self.sender = sender
        self.send_type = send_type
        self.messages = messages
        self.auth_user = auth_user
        self.auth_password = auth_password
        self.provider = provider
        self.timeout = int(timeout)
        self.use_tls = use_tls
        self.port_number = port_number
        self.bcc = bcc
        self.cc = cc
        threading.Thread.__init__(self)

    def send_normal(self):
        try:
            message = EmailMultiAlternatives(
                subject=self.subject,
                body=self.body,
                from_email=self.sender,
                to=self.recipients,
                bcc=self.bcc,
                cc=self.cc,
            )
            message.attach_alternative(self.body, "text/html")

            email_backend = EmailBackend(
                host=self.provider,
                username=self.auth_user,
                password=self.auth_password,
                port=self.port_number,
                use_tls=self.use_tls,
                timeout=self.timeout,
            )
            email_backend.send_messages([message])

        except Exception as e:
            LOGGER.error(e)
            raise e

    def send_mass_mail(self):
        with get_connection(
            username=self.auth_user, password=self.auth_password, fail_silently=False, timeout=self.timeout
        ) as connection:
            for message in self.messages:
                message.connection = connection

            connection.send_messages(self.messages)

    def run(self) -> None:
        if self.send_type == "normal":
            self.send_normal()
        else:
            self.send_mass_mail()
