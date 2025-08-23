from celery import shared_task
from time import sleep
import logging
from core.workers import worker


@worker(queue="emails")  # Uses rabbitmq as broker
def send_email(to_email="Hi", subject="hola", message="Hola"):
    sleep(3)
    # Aquí iría la lógica para enviar el correo
    print(f"Enviando correo a {to_email} con asunto: {subject}")
    # Lógica para enviar el email (por ejemplo, usando Django Email)
    print("Email enviado con éxito: ", message)
    logging.info(f"Enviando correo a {to_email} con asunto: {subject}")
