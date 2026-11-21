# Celery app and background task definitions
from celery import Celery
import time

app = Celery('task', broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/1')

@app.task
def process_order(order_data):
    print(f"processing payment")
    time.sleep(2)
    print("Payment successful")
    return order_data

@app.task
def prepare_item(item_name,order_id):
    print(f"preparing {item_name} for order {order_id}")
    time.sleep(3)
    print(f"{item_name} is ready")
    return item_name

@app.task
def pack_order(prepare_items,order_data):
    print("packing order")
    time.sleep(2)
    order_data['status']='Packed'
    order_data["items_cooked"]=prepare_items
    print("order packed")
    return order_data

@app.task
def dispatch_delivery(order_data):
    print('Delivering order')
    time.sleep(2)
    order_data['status']="Delivered"
    print("order successfully deliverd")
    return order_data

@app.task
def send_feedback_email(order_data):
    print(f"sending email to {order_data['customer_email']}")
    return 'Feedback email sent sucessfully'
