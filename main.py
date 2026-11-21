# # from fastapi import FastAPI
# from flask import Flask,request,jsonify
# # from pydantic import BaseModel
# from celery import chain,group,chord
# from celery.result import AsyncResult
# from task import app,process_order,prepare_item,pack_order,dispatch_delivery,send_feedback_email
# import uuid

# # app=FastAPI(title="Food Order Tracker")
# app=Flask(__name__)

# # class OrderSchema(BaseModel):
# #     customer_email:str
# #     items:list[str]
# #     total_amount:float

# @app.post("/orders")
# def place_order():
#     order=request.get_json()
#     if not order:
#         return jsonify({"error":"invalid JSON data"}),400
#     order_id=str(uuid.uuid4())
#     order_data={
#         "order_id":order_id,
#         "customer_email":order["customer_email"],
#         "items":order["items"],
#         "total_amount":order["total_amount"]
#     }
#     cooking=group(
#         prepare_item.s(item,order_id)
#         for item in order["items"]
#     )
#     workflow=chain(
#         process_order.s(order_data),
#         chord(cooking,pack_order.s(order_data)),
#         dispatch_delivery.s(),
#         send_feedback_email.s().set(countdown=15)
#     )
#     result = workflow.apply_async()
#     return jsonify({
#         "order_id":order_id,
#         "task_id":result.id,
#         "message":"Order placed successfully"
#     })

# @app.get("/orders/{task_id}")
# def get_order_status(task_id:str):
#     result=AsyncResult(task_id,app=app)
#     return{
#         "task_id":task_id,
#         "status":result.state,
#         "result":result.result if result.ready() 
#         else "Order is processing"
#     }

# if __name__=="__main__":
#     app.run(host='0.0.0.0',port=8001,debug=True)


from fastapi import FastAPI
from pydantic import BaseModel
from celery import chain,group,chord
from celery.result import AsyncResult
from task import app as celery_app,process_order,prepare_item,pack_order,dispatch_delivery,send_feedback_email
import uuid

app = FastAPI(title="Food Order Tracker")

class OrderSchema(BaseModel):
    customer_email:str
    items:list[str]
    total_amount:float

@app.post("/orders")
def place_order(order:OrderSchema):
    order_id=str(uuid.uuid4())
    order_data={
        "order_id":order_id,
        "customer_email":order.customer_email,
        "items":order.items,
        "total_amount":order.total_amount
    }
    cooking=group(
        prepare_item.si(item,order_id)
        for item in order.items
    )
    workflow=chain(
        process_order.s(order_data),
        chord(cooking,pack_order.s(order_data)),
        dispatch_delivery.s(),
        send_feedback_email.s().set(countdown=15)
    )
    result = workflow.apply_async()
    return{
        "order_id":order_id,
        "task_id":result.id,
        "message":"Order placed successfully"
    }

@app.get("/orders/{task_id}")
def get_order_status(task_id: str):
    result=AsyncResult(task_id,app=celery_app)
    return{
        "task_id":task_id,
        "status":result.state,
        "result":result.result 
        if result.ready() 
        else "Order is processing"
    }