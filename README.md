# Food Order Tracker \| FastAPI, Celery, Redis & Docker

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Async%20API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-Distributed%20Tasks-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-Message%20Broker%20%26%20Backend-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Containerization-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

A **distributed, asynchronous food order tracking system** built with
**Python, FastAPI, Celery, Redis, and Docker**. The API accepts an order
and quickly returns tracking identifiers, while Celery workers process
payment, prepare food items concurrently, pack the order, dispatch
delivery, and schedule a follow-up feedback email in the background.

> **Project focus:** asynchronous task processing, distributed task
> queues, parallel execution, workflow orchestration, retries, and
> background job status tracking.

------------------------------------------------------------------------

## Table of Contents

-   [Overview](#overview)
-   [Architecture](#architecture)
-   [Order Processing Workflow](#order-processing-workflow)
-   [Technology Stack](#technology-stack)
-   [Key Features](#key-features)
-   [Prerequisites](#prerequisites)
-   [Getting Started](#getting-started)
-   [API Documentation](#api-documentation)
-   [Example API Requests](#example-api-requests)
-   [Celery Task Orchestration](#celery-task-orchestration)
-   [Monitoring Task Status](#monitoring-task-status)
-   [Docker](#docker)
-   [Project Structure](#project-structure)
-   [Learning Outcomes](#learning-outcomes)
-   [Future Improvements](#future-improvements)

## Overview

The Food Order Tracker demonstrates how to move long-running work out of
an HTTP request/response cycle.

1.  A customer submits an order through the FastAPI endpoint.
2.  FastAPI validates the request and creates an order ID.
3.  The API sends the workflow to Celery through Redis and immediately
    returns a task ID.
4.  Celery workers execute the order-processing workflow asynchronously.
5.  Redis stores task state and results so the API can report progress
    to the client.

The background workflow includes payment processing with retries,
parallel food preparation, item aggregation and packing, delivery
dispatch, and delayed customer engagement.

## Architecture

### High-level system architecture

```mermaid
flowchart LR
    Customer["Customer / API Client"]
    API["FastAPI Application"]
    Broker[("Redis DB 0<br/>Celery Broker")]
    Worker["Celery Worker"]
    Backend[("Redis DB 1<br/>Result Backend")]

    Customer -->|"1. POST /orders"| API
    API -->|"2. Enqueue workflow"| Broker
    Broker -->|"3. Deliver task"| Worker
    Worker -->|"4. Store progress and results"| Backend
    API -->|"5. Read task status"| Backend
    Backend -->|"Return task state"| API
    API -->|"6. Return order receipt or status"| Customer
```

**Component responsibilities**

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  FastAPI                             Validates incoming orders, creates
                                      tracking identifiers, queues
                                      background work, and exposes
                                      order-status endpoints.

  Redis DB 0                          Acts as the Celery message broker
                                      and stores queued task messages.

  Celery worker                       Consumes queued work and executes
                                      the order workflow in the
                                      background.

  Redis DB 1                          Acts as the Celery result backend
                                      for task states and final results.

  Docker                              Provides a containerization layer
                                      for packaging and running the
                                      application services.
  -----------------------------------------------------------------------

### Detailed order-processing flow

The workflow uses Celery Canvas primitives to combine sequential steps
with parallel work.

```mermaid
flowchart TD
    Start["Customer submits POST /orders"]
    Validate["FastAPI validates the order"]
    IDs["Generate order ID and task ID"]
    Queue["Submit workflow to Redis"]
    Response["Return order receipt"]

    Start --> Validate --> IDs --> Queue --> Response

    Queue --> Payment["process_payment"]

    Payment -->|"Temporary failure"| Retry["Retry after 3 seconds<br/>Maximum 3 retries"]
    Retry --> Payment
    Payment -->|"Payment successful"| Group["Prepare food items in parallel"]

    Group --> Item1["Prepare item 1"]
    Group --> Item2["Prepare item 2"]
    Group --> ItemN["Prepare item N"]

    Item1 --> Wait{"All preparation tasks complete?"}
    Item2 --> Wait
    ItemN --> Wait

    Wait -->|"Yes"| Pack["pack_order"]
    Pack --> Dispatch["dispatch_delivery"]
    Dispatch --> Schedule["Schedule feedback email<br/>15 seconds later"]
    Schedule --> Feedback["send_feedback_email"]

    Backend[("Redis result backend")]
    Payment -. "Task state" .-> Backend
    Item1 -. "Task state" .-> Backend
    Item2 -. "Task state" .-> Backend
    ItemN -. "Task state" .-> Backend
    Pack -. "Task result" .-> Backend
    Dispatch -. "Task result" .-> Backend
    Feedback -. "Task result" .-> Backend
```

## Order Processing Workflow

  -----------------------------------------------------------------------
  Stage                   Task                    What happens
  ----------------------- ----------------------- -----------------------
  1                       `process_payment`       Processes payment and
                                                  retries transient
                                                  failures after a
                                                  3-second countdown, up
                                                  to 3 retries.

  2                       `prepare_item`          Prepares each food item
                                                  as an independent task,
                                                  allowing parallel
                                                  execution.

  3                       `pack_order`            Waits for all
                                                  preparation tasks and
                                                  aggregates their
                                                  outputs into a packed
                                                  order.

  4                       `dispatch_delivery`     Receives the
                                                  packed-order summary
                                                  and dispatches the
                                                  order for delivery.

  5                       `send_feedback_email`   Runs as a delayed task
                                                  15 seconds after
                                                  delivery dispatch.
  -----------------------------------------------------------------------

## Technology Stack

-   **Language:** Python 3.9+
-   **API framework:** FastAPI
-   **ASGI server:** Uvicorn
-   **Task queue:** Celery
-   **Message broker:** Redis (Database 0)
-   **Task result backend:** Redis (Database 1)
-   **Containerization:** Docker
-   **API testing:** Postman or cURL

## Key Features

-   **Non-blocking order API:** returns an order receipt without waiting
    for the complete workflow.
-   **Asynchronous background processing:** Celery workers handle
    long-running operations outside the API request.
-   **Parallel task execution:** uses `group()` to prepare multiple food
    items concurrently.
-   **Workflow synchronization:** uses `chord()` to call the packing
    task after all parallel preparation tasks finish.
-   **Sequential task pipeline:** uses `chain()` to pass the
    packed-order result into delivery dispatch.
-   **Automatic task retries:** uses `bind=True`, `max_retries`, and
    `self.retry()` for transient payment failures.
-   **Delayed task scheduling:** uses `apply_async(countdown=15)` for
    post-delivery feedback.
-   **Task state and result tracking:** uses `AsyncResult(task_id)` with
    Redis as the result backend.

## Prerequisites

-   Python 3.9 or newer
-   Redis running and accessible at `localhost:6379`
-   Required Python packages: `fastapi`, `uvicorn`, `celery`, and
    `redis`
-   Docker, if you want to run the services in containers
-   Postman or cURL for testing the API

Redis is configured with two logical databases:

```text
redis://localhost:6379/0  # Celery message broker
redis://localhost:6379/1  # Celery result backend
```

## Getting Started

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_PROJECT_DIRECTORY>
```

Replace the placeholders with your Git repository URL and project
directory.

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn celery redis
```

### 4. Start Redis

Start a Redis instance and confirm that it is listening on port `6379`.
The application expects the broker and result backend URLs shown above.

### 5. Start the Celery worker

Open a terminal in the project root and run:

```bash
celery -A tasks worker --loglevel=info --pool=threads --concurrency=4 -n worker1@%h
```

The thread pool is used in the supplied practice setup for
Windows-compatible worker execution.

### 6. Start the FastAPI server

Open another terminal and run:

```bash
uvicorn main:api --reload
```

The command assumes the FastAPI application instance is named `api` in
`main.py`.

### 7. Open the API documentation

Visit:

```text
http://127.0.0.1:8000/docs
```

Use the interactive Swagger UI to submit an order and check its status.

## API Documentation

  -----------------------------------------------------------------------
  Method                  Endpoint                Description
  ----------------------- ----------------------- -----------------------
  `POST`                  `/orders`               Submit a new food order
                                                  and start the
                                                  background workflow.

  `GET`                   `/orders/{task_id}`     Retrieve the Celery
                                                  task state and result
                                                  for an order workflow.
  -----------------------------------------------------------------------

### Place an order

**Endpoint:** `POST /orders`

**Content-Type:** `application/json`

Request body:

```json
{
  "customer_email": "rahul@example.com",
  "items": [
    "Margherita Pizza",
    "Garlic Bread",
    "Cold Coffee"
  ],
  "total_amount": 599.0
}
```

Example immediate response:

```json
{
  "order_id": "ORD-A1B2C3",
  "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "message": "Order placed successfully. Tracking workflow initiated."
}
```

The identifiers above are illustrative. Your application will generate
its own IDs.

### Check order status

**Endpoint:** `GET /orders/{task_id}`

Use the `task_id` returned by `POST /orders`.

Example in-progress response:

```json
{
  "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "state": "PENDING",
  "result": "Still in progress..."
}
```

Example successful response:

```json
{
  "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "state": "SUCCESS",
  "result": {
    "order_id": "ORD-A1B2C3",
    "status": "DELIVERED",
    "details": "Order ORD-A1B2C3 packed with ['Margherita Pizza', 'Garlic Bread', 'Cold Coffee']"
  }
}
```

The exact response depends on the task state and the result returned by
your implementation.

## Example API Requests

Submit an order:

```bash
curl -X POST "http://127.0.0.1:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "rahul@example.com",
    "items": ["Margherita Pizza", "Garlic Bread", "Cold Coffee"],
    "total_amount": 599.0
  }'
```

Check its status (replace the task ID):

```bash
curl "http://127.0.0.1:8000/orders/<TASK_ID>"
```

You can also send the same requests through Postman.

## Celery Task Orchestration

This project demonstrates common Celery Canvas patterns:

  -----------------------------------------------------------------------
  Celery feature                      Role in this project
  ----------------------------------- -----------------------------------
  `chain()`                           Runs dependent workflow steps
                                      sequentially.

  `group()`                           Runs independent food-preparation
                                      tasks in parallel.

  `chord()`                           Waits for all tasks in a group
                                      before running the packing
                                      callback.

  `.si()`                             Creates an immutable task signature
                                      where required by the workflow.

  `self.retry()`                      Retries a task after a temporary
                                      failure.

  `apply_async(countdown=15)`         Schedules the feedback task for
                                      later execution.

  `AsyncResult(task_id)`              Reads the state and result
                                      associated with a task ID.
  -----------------------------------------------------------------------

## Monitoring Task Status

The status endpoint reads the task information using Celery's
`AsyncResult` and the Redis result backend.

Common Celery states include:

-   `PENDING` --- the task is waiting, or its state is not yet known to
    the result backend.
-   `STARTED` --- the worker has started executing the task (when
    started-state tracking is enabled).
-   `SUCCESS` --- the task completed successfully.
-   `FAILURE` --- the task raised an exception and failed.

Check the Celery worker terminal to follow payment, retry, parallel
preparation, packing, delivery, and feedback task logs.

## Docker

Docker is part of the project's technology stack and can be used to
package the API, worker, and Redis services as containers.

The supplied practice guide specifies the local Python/Uvicorn/Celery
startup commands, but does not define Dockerfile or Docker Compose
configuration. If your repository contains a `Dockerfile` and
`compose.yaml` (or `docker-compose.yml`), add the verified container
startup command here. For example, `docker compose up --build` is
appropriate only after a working Compose configuration has been added.

## Project Structure

The exact file layout depends on your repository. A possible
organization is:

```text
food-order-tracker/
├── main.py              # FastAPI application and order endpoints
├── tasks.py             # Celery app and background task definitions
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container image definition (if included)
├── compose.yaml         # Multi-container setup (if included)
└── README.md
```

Adjust this tree to match the files that actually exist in your
repository.

## Learning Outcomes

By building this project, you can practice:

-   Designing a decoupled producer--broker--consumer architecture.
-   Building REST APIs with FastAPI.
-   Processing background jobs with Celery and Redis.
-   Combining sequential pipelines with parallel fan-out/fan-in
    workflows.
-   Handling transient failures with automatic task retries.
-   Scheduling delayed background jobs without blocking worker
    execution.
-   Tracking asynchronous task lifecycle states and results.
-   Understanding how Docker can package application services for
    repeatable deployment.

## Future Improvements

-   Add input validation and consistent error responses for invalid
    orders.
-   Add persistent order records in a database.
-   Add authentication and authorization for customer order tracking.
-   Add structured logging and health-check endpoints.
-   Add Docker Compose configuration with health checks and service
    dependencies.
-   Add automated tests for API endpoints and Celery tasks.
-   Add monitoring and metrics for queue length, task duration, retries,
    and worker health.

------------------------------------------------------------------------

## Keywords

`Food Order Tracking System` · `FastAPI Project` ·
`Python Backend Project` · `Celery Task Queue` · `Redis Message Broker`
· `Redis Result Backend` · `Asynchronous Processing` ·
`Background Tasks` · `Distributed Task Processing` · `Celery Canvas` ·
`Parallel Task Execution` · `Dockerized Python Application` · `REST API`
· `Microservices Architecture`

------------------------------------------------------------------------

**If you find this project useful, consider giving the repository a
star.**





# 🍕 Food Order Tracker | FastAPI, Celery, Redis & Docker

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Async%20API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-Distributed%20Tasks-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-Message%20Broker%20%26%20Backend-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Containerization-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

A **distributed, asynchronous food order tracking system** built with **Python, FastAPI, Celery, Redis, and Docker**. The API accepts an order and quickly returns tracking identifiers, while Celery workers process payment, prepare food items concurrently, pack the order, dispatch delivery, and schedule a follow-up feedback email in the background.

> **Project focus:** asynchronous task processing, distributed task queues, parallel execution, workflow orchestration, retries, and background job status tracking.

---

## 📑 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Order Processing Workflow](#order-processing-workflow)
- [Technology Stack](#technology-stack)
- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Example API Requests](#example-api-requests)
- [Celery Task Orchestration](#celery-task-orchestration)
- [Monitoring Task Status](#monitoring-task-status)
- [Docker](#docker)
- [Project Structure](#project-structure)
- [Learning Outcomes](#learning-outcomes)
- [Future Improvements](#future-improvements)

---

## 🔍 Overview

The Food Order Tracker demonstrates how to move long-running work out of an HTTP request/response cycle.

1. A customer submits an order through the FastAPI endpoint.
2. FastAPI validates the request and creates an order ID.
3. The API sends the workflow to Celery through Redis and immediately returns a task ID.
4. Celery workers execute the order-processing workflow asynchronously.
5. Redis stores task state and results so the API can report progress to the client.

The background workflow includes payment processing with retries, parallel food preparation, item aggregation and packing, delivery dispatch, and delayed customer engagement.

---

## 🏗️ Architecture

### High-level system architecture

```mermaid
flowchart LR
    classDef client fill:#FFB74D,stroke:#F57C00,stroke-width:2px,color:#fff;
    classDef api fill:#009688,stroke:#00796B,stroke-width:2px,color:#fff;
    classDef broker fill:#DC382D,stroke:#B71C1C,stroke-width:2px,color:#fff;
    classDef worker fill:#37814A,stroke:#2E7D32,stroke-width:2px,color:#fff;
    classDef backend fill:#E53935,stroke:#C62828,stroke-width:2px,color:#fff;

    Customer["👤 Customer / API Client"]:::client
    API["⚡ FastAPI Application"]:::api
    Broker[("🗄️ Redis DB 0<br/>Celery Broker")]:::broker
    Worker["⚙️ Celery Worker"]:::worker
    Backend[("💾 Redis DB 1<br/>Result Backend")]:::backend

    Customer -->|"1. POST /orders"| API
    API -->|"2. Enqueue workflow"| Broker
    Broker -->|"3. Deliver task"| Worker
    Worker -->|"4. Store progress and results"| Backend
    API -->|"5. Read task status"| Backend
    Backend -->|"Return task state"| API
    API -->|"6. Return order receipt or status"| Customer
```

**Component responsibilities**

| Component | Responsibility |
| :--- | :--- |
| **FastAPI** | Validates incoming orders, creates tracking identifiers, queues background work, and exposes order-status endpoints. |
| **Redis DB 0** | Acts as the Celery message broker and stores queued task messages. |
| **Celery Worker** | Consumes queued work and executes the order workflow in the background. |
| **Redis DB 1** | Acts as the Celery result backend for task states and final results. |
| **Docker** | Provides a containerization layer for packaging and running the application services. |

### Detailed order-processing flow

The workflow uses Celery Canvas primitives to combine sequential steps with parallel work.

```mermaid
flowchart TD
    classDef step fill:#E0F7FA,stroke:#00ACC1,stroke-width:2px,color:#006064;
    classDef payment fill:#FFF9C4,stroke:#FBC02D,stroke-width:2px,color:#F57F17;
    classDef groupTask fill:#E8F5E9,stroke:#43A047,stroke-width:2px,color:#1B5E20;
    classDef action fill:#EDE7F6,stroke:#7E57C2,stroke-width:2px,color:#311B92;
    classDef db fill:#FFEBEE,stroke:#E53935,stroke-width:2px,color:#B71C1C;

    Start["Customer submits POST /orders"]:::step
    Validate["FastAPI validates the order"]:::step
    IDs["Generate order ID and task ID"]:::step
    Queue["Submit workflow to Redis"]:::step
    Response["Return order receipt (<100ms)"]:::step

    Start --> Validate --> IDs --> Queue --> Response

    Queue --> Payment["💳 process_payment"]:::payment

    Payment -->|"Temporary failure"| Retry["🔄 Retry after 3 seconds<br/>Maximum 3 retries"]:::payment
    Retry --> Payment
    Payment -->|"Payment successful"| Group["👨‍🍳 Prepare food items in parallel"]:::groupTask

    Group --> Item1["🍕 Prepare item 1"]:::groupTask
    Group --> Item2["🥖 Prepare item 2"]:::groupTask
    Group --> ItemN["☕ Prepare item N"]:::groupTask

    Item1 --> Wait{"⏱️ All preparation tasks complete?"}:::groupTask
    Item2 --> Wait
    ItemN --> Wait

    Wait -->|"Yes"| Pack["📦 pack_order"]:::action
    Pack --> Dispatch["🛵 dispatch_delivery"]:::action
    Dispatch --> Schedule["⏳ Schedule feedback email<br/>15 seconds later"]:::action
    Schedule --> Feedback["✉️ send_feedback_email"]:::action

    Backend[("💾 Redis result backend")]:::db
    Payment -. "Task state" .-> Backend
    Item1 -. "Task state" .-> Backend
    Item2 -. "Task state" .-> Backend
    ItemN -. "Task state" .-> Backend
    Pack -. "Task result" .-> Backend
    Dispatch -. "Task result" .-> Backend
    Feedback -. "Task result" .-> Backend
```

---

## 🔄 Order Processing Workflow

| Stage | Task | What happens |
| :---: | :--- | :--- |
| **1** | `process_payment` | Processes payment and retries transient failures after a 3-second countdown, up to 3 retries. |
| **2** | `prepare_item` | Prepares each food item as an independent task, allowing parallel execution across threads. |
| **3** | `pack_order` | Waits for all preparation tasks (`chord` callback) and aggregates their outputs into a packed order. |
| **4** | `dispatch_delivery` | Receives the packed-order summary (`chain`) and dispatches the order for delivery. |
| **5** | `send_feedback_email` | Runs as a delayed background task 15 seconds after delivery dispatch (`apply_async`). |

---

## 🛠️ Technology Stack

- **Language:** Python 3.9+
- **API framework:** FastAPI
- **ASGI server:** Uvicorn
- **Task queue:** Celery
- **Message broker:** Redis (Database 0)
- **Task result backend:** Redis (Database 1)
- **Containerization:** Docker
- **API testing:** Postman or cURL

---

## ✨ Key Features

- **Non-blocking order API:** returns an order receipt in under 100ms without waiting for the complete workflow.
- **Asynchronous background processing:** Celery workers handle long-running operations outside the API request cycle.
- **Parallel task execution:** uses `group()` to prepare multiple food items concurrently.
- **Workflow synchronization:** uses `chord()` to trigger the packing task only after all parallel preparation tasks finish.
- **Sequential task pipeline:** uses `chain()` to pass the packed-order result directly into delivery dispatch.
- **Automatic task retries:** uses `bind=True`, `max_retries`, and `self.retry()` for transient payment failures.
- **Delayed task scheduling:** uses `apply_async(countdown=15)` for post-delivery customer feedback.
- **Task state and result tracking:** uses `AsyncResult(task_id)` with Redis as the result backend.

---

## 📋 Prerequisites

- Python 3.9 or newer
- Redis running and accessible at `localhost:6379`
- Required Python packages: `fastapi`, `uvicorn`, `celery`, and `redis`
- Docker, if you want to run the services in containers
- Postman or cURL for testing the API

Redis is configured with two logical databases:

```text
redis://localhost:6379/0  # Celery message broker
redis://localhost:6379/1  # Celery result backend
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_PROJECT_DIRECTORY>
```

*Replace the placeholders with your Git repository URL and project directory.*

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn celery redis
```

### 4. Start Redis

Start a Redis instance and confirm that it is listening on port `6379`. The application expects the broker and result backend URLs shown above.

### 5. Start the Celery worker

Open a terminal in the project root and run:

```bash
celery -A tasks worker --loglevel=info --pool=threads --concurrency=4 -n worker1@%h
```

*The thread pool (`--pool=threads`) is used in this setup for cross-platform, Windows-compatible worker execution.*

### 6. Start the FastAPI server

Open another terminal and run:

```bash
uvicorn main:api --reload
```

*The command assumes the FastAPI application instance is named `api` in `main.py`.*

### 7. Open the API documentation

Visit:

```text
http://127.0.0.1:8000/docs
```

Use the interactive Swagger UI to submit an order and check its status.

---

## 📡 API Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/orders` | Submit a new food order and start the background workflow. |
| `GET` | `/orders/{task_id}` | Retrieve the Celery task state and result for an order workflow. |

### Place an order

- **Endpoint:** `POST /orders`
- **Content-Type:** `application/json`

**Request body:**

```json
{
  "customer_email": "rahul@example.com",
  "items": [
    "Margherita Pizza",
    "Garlic Bread",
    "Cold Coffee"
  ],
  "total_amount": 599.0
}
```

**Example immediate response:**

```json
{
  "order_id": "ORD-A1B2C3",
  "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "message": "Order placed successfully. Tracking workflow initiated."
}
```

*The identifiers above are illustrative. Your application will generate its own UUIDs.*

### Check order status

- **Endpoint:** `GET /orders/{task_id}` (Use the `task_id` returned by `POST /orders`)

**Example in-progress response:**

```json
{
  "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "state": "PENDING",
  "result": "Still in progress..."
}
```

**Example successful response:**

```json
{
  "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "state": "SUCCESS",
  "result": {
    "order_id": "ORD-A1B2C3",
    "status": "DELIVERED",
    "details": "Order ORD-A1B2C3 packed with ['Margherita Pizza', 'Garlic Bread', 'Cold Coffee']"
  }
}
```

---

## 💻 Example API Requests

**Submit an order:**

```bash
curl -X POST "http://127.0.0.1:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "rahul@example.com",
    "items": ["Margherita Pizza", "Garlic Bread", "Cold Coffee"],
    "total_amount": 599.0
  }'
```

**Check its status (replace `<TASK_ID>`):**

```bash
curl "http://127.0.0.1:8000/orders/<TASK_ID>"
```

*You can also send the same requests through Postman.*

---

## 🧩 Celery Task Orchestration

This project demonstrates common Celery Canvas patterns:

| Celery feature | Role in this project |
| :--- | :--- |
| `chain()` | Runs dependent workflow steps sequentially. |
| `group()` | Runs independent food-preparation tasks in parallel. |
| `chord()` | Waits for all tasks in a group before running the packing callback. |
| `.si()` | Creates an immutable task signature where required by the workflow. |
| `self.retry()` | Retries a task after a temporary failure. |
| `apply_async(countdown=15)` | Schedules the feedback task for later execution. |
| `AsyncResult(task_id)` | Reads the state and result associated with a task ID. |

---

## 📊 Monitoring Task Status

The status endpoint reads the task information using Celery's `AsyncResult` and the Redis result backend.

Common Celery states include:

- `PENDING` — the task is waiting, or its state is not yet known to the result backend.
- `STARTED` — the worker has started executing the task (when started-state tracking is enabled).
- `SUCCESS` — the task completed successfully.
- `FAILURE` — the task raised an exception and failed.

Check the Celery worker terminal to follow payment, retry, parallel preparation, packing, delivery, and feedback task logs.

---

## 🐳 Docker

Docker is part of the project's technology stack and can be used to package the API, worker, and Redis services as containers.

If your repository contains a `Dockerfile` and `compose.yaml` (or `docker-compose.yml`), you can spin up the entire stack with:

```bash
docker compose up --build
```

---

## 📁 Project Structure

```text
food-order-tracker/
├── main.py              # FastAPI application and order endpoints
├── tasks.py             # Celery app and background task definitions
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container image definition
├── compose.yaml         # Multi-container setup
└── README.md
```

---

## 🎓 Learning Outcomes

By building this project, you can practice:

- Designing a decoupled **producer–broker–consumer** architecture.
- Building high-throughput REST APIs with **FastAPI**.
- Processing background jobs with **Celery** and **Redis**.
- Combining sequential pipelines with parallel fan-out/fan-in workflows.
- Handling transient failures with automatic task retries.
- Scheduling delayed background jobs without blocking worker execution.
- Tracking asynchronous task lifecycle states and results.
- Packaging application services with **Docker** for repeatable deployment.

---

## 🔮 Future Improvements

- Add input validation and consistent error responses for invalid orders.
- Add persistent order records in a relational database (e.g., PostgreSQL).
- Add authentication and authorization for customer order tracking.
- Add structured logging and health-check endpoints.
- Add Docker Compose configuration with health checks and service dependencies.
- Add automated unit and integration tests for API endpoints and Celery tasks.
- Add monitoring and metrics (e.g., Flower or Prometheus) for queue length, task duration, and worker health.

---

## 🏷️ Keywords

`Food Order Tracking System` · `FastAPI Project` · `Python Backend Project` · `Celery Task Queue` · `Redis Message Broker` · `Redis Result Backend` · `Asynchronous Processing` · `Background Tasks` · `Distributed Task Processing` · `Celery Canvas` · `Parallel Task Execution` · `Dockerized Python Application` · `REST API` · `Microservices Architecture`

---

⭐ **If you find this project useful, consider giving the repository a star!**



