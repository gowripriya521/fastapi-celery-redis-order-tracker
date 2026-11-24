import os
import time
import random
import smtplib
from email.message import EmailMessage
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

app=Celery(
    "task",
    broker=os.getenv("CELERY_BROKER_URL","redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND","redis://localhost:6379/1")
)

SMTP_USER=os.getenv("SMTP_USER")
SMTP_PASSWORD=os.getenv("SMTP_PASSWORD")


@app.task(bind=True,max_retries=3)
def process_order(self,order_data):
    try:
        print("processing payment")
        time.sleep(random.randint(2, 5))
        print("Payment successful")
        return order_data
    except Exception as exc:
        raise self.retry(exc=exc,countdown=5)


@app.task
def prepare_item(item_name,order_id):
    print(f"preparing {item_name} for order {order_id}")
    time.sleep(random.uniform(3.0, 7.0))
    print(f"{item_name} is ready")
    return item_name


@app.task
def pack_order(prepare_items,order_data):
    print("packing order")
    time.sleep(random.randint(2, 4))
    order_data["status"]="Packed"
    order_data["items_cooked"]=prepare_items
    print("order packed")
    return order_data


@app.task
def dispatch_delivery(order_data):
    print("Delivering order")
    time.sleep(random.randint(3, 6))
    order_data["status"]="Delivered"
    print("order successfully delivered")
    return order_data


@app.task(bind=True,max_retries=3)
def send_feedback_email(self,order_data):
    try:
        msg = EmailMessage()
        msg["Subject"]="Order Delivered"
        msg["From"]=SMTP_USER
        msg["To"]=order_data["customer_email"]
        items=", ".join(order_data["items"])
        amount=order_data["total_amount"]
        msg.set_content(
            f"Your order ({order_data['order_id']}) is delivered!\n\n"
            f"Items: {items}\n"
            f"Total Amount: ₹{amount}\n\n"
            f"Thank you have a nice day!"
        )

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"sending email to {order_data['customer_email']}")
        return "Email sent successfully"
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)
