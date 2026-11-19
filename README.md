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
%%{init: {'theme': 'dark', 'themeVariables': { 'darkMode': true, 'background': '#0d1117', 'lineColor': '#38bdf8', 'textColor': '#f8fafc', 'clusterBkg': '#161b22', 'clusterBorder': '#30363d' }}}%%
flowchart TD
    classDef clientBox fill:#0c2d48,stroke:#38bdf8,stroke-width:2px,color:#f0f9ff,rx:8,ry:8;
    classDef gatewayBox fill:#082f49,stroke:#06b6d4,stroke-width:2px,color:#ecfeff,rx:8,ry:8;
    classDef brokerBox fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#eef2ff,rx:8,ry:8;
    classDef workerBox fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#ecfdf5,rx:8,ry:8;
    classDef resultBox fill:#451a03,stroke:#f59e0b,stroke-width:2px,color:#fffbeb,rx:8,ry:8;

    subgraph ClientLayer ["🌐 Client Layer"]
        Customer["👤 Customer / API Client<br/>• Submits Order JSON<br/>• Polls Tracking Status"]:::clientBox
    end

    subgraph IngestionGateway ["⚡ Ingestion Gateway"]
        API["🚀 FastAPI Application<br/>• Pydantic Payload Validation<br/>• Generates ORD & Task IDs<br/>• Non-Blocking Dispatcher"]:::gatewayBox
    end

    subgraph MessageBroker ["📦 Message Broker & Queue"]
        Broker[("⚡ Redis DB 0<br/>• Celery Message Broker<br/>• Task Queue & Signatures")]:::brokerBox
    end

    subgraph AsyncExecution ["⚙️ Async Execution Engine"]
        Worker["🧵 Celery Workers<br/>• Thread Pool (--concurrency=4)<br/>• Canvas Workflow Runner"]:::workerBox
    end

    subgraph ResultStorage ["💾 State & Result Backend"]
        Backend[("🗄️ Redis DB 1<br/>• Task Lifecycle States<br/>• Final Delivery Payloads")]:::resultBox
    end

    Customer -->|"1. HTTP POST /orders"| API
    API -->|"2. Enqueue Canvas Workflow"| Broker
    Broker -->|"3. Consume Task"| Worker
    Worker -->|"4. Persist State & Result"| Backend
    API <-->|"5. Poll AsyncResult(task_id)"| Backend
    API -->|"6. Return Receipt / Status"| Customer
```

**Component responsibilities**

| Component | Responsibility |
| :--- | :--- |
| **FastAPI** | Validates incoming orders, creates tracking identifiers, queues background work, and exposes order-status endpoints. |
| **Redis DB 0** | Acts as the Celery message broker and stores queued task messages. |
| **Celery Worker** | Consumes queued work and executes the order workflow in the background. |
| **Redis DB 1** | Acts as the Celery result backend for task states and final results. |
| **Docker** | Provides a containerization layer for packaging and running the application services. |

---

### Detailed order-processing flow

The workflow uses Celery Canvas primitives to combine sequential steps with parallel work.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'darkMode': true, 'background': '#0d1117', 'lineColor': '#38bdf8', 'textColor': '#f8fafc', 'clusterBkg': '#161b22', 'clusterBorder': '#30363d' }}}%%
flowchart TD
    classDef gateway fill:#082f49,stroke:#06b6d4,stroke-width:2px,color:#ecfeff,rx:8,ry:8;
    classDef payment fill:#3b0764,stroke:#c084fc,stroke-width:2px,color:#faf5ff,rx:8,ry:8;
    classDef parallel fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#ecfdf5,rx:8,ry:8;
    classDef pipeline fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#eef2ff,rx:8,ry:8;
    classDef storage fill:#451a03,stroke:#f59e0b,stroke-width:2px,color:#fffbeb,rx:8,ry:8;

    subgraph API_Layer ["⚡ FastAPI Non-Blocking Ingestion (<100ms)"]
        Start["Customer submits POST /orders"]:::gateway
        Validate["Validate Payload & Generate IDs"]:::gateway
        Response["Return Immediate Order Receipt"]:::gateway
        Start --> Validate --> Response
    end

    subgraph Payment_Stage ["💳 Fault-Tolerant Payment"]
        Payment["process_payment<br/>• Charges Customer Gateway"]:::payment
        Retry["🔄 self.retry(countdown=3)<br/>• Max 3 Retries"]:::payment
        Payment -->|"Transient Failure"| Retry
        Retry --> Payment
    end

    subgraph Kitchen_Chord ["👨‍🍳 Parallel Fan-Out & Synchronization (chord)"]
        Group["group() Parallel Fan-Out"]:::parallel
        Item1["🍕 prepare_item 1"]:::parallel
        Item2["🥖 prepare_item 2"]:::parallel
        ItemN["☕ prepare_item N"]:::parallel
        Wait{"⏱️ Chord Barrier<br/>All items cooked?"}:::parallel

        Group --> Item1 & Item2 & ItemN
        Item1 & Item2 & ItemN --> Wait
    end

    subgraph Fulfillment_Chain ["🛵 Sequential Delivery & Engagement (chain)"]
        Pack["📦 pack_order<br/>• Aggregates Cooked Items"]:::pipeline
        Dispatch["🛵 dispatch_delivery<br/>• Hands off to Courier"]:::pipeline
        Schedule["⏳ apply_async(countdown=15)<br/>• Non-Blocking Delay"]:::pipeline
        Feedback["✉️ send_feedback_email<br/>• Post-Delivery Follow-up"]:::pipeline

        Pack --> Dispatch --> Schedule --> Feedback
    end

    Backend[("🗄️ Redis DB 1 Result Backend")]:::storage

    Validate -->|"Enqueue Workflow"| Payment
    Payment -->|"Payment Success"| Group
    Wait -->|"Yes"| Pack

    Payment -. "State" .-> Backend
    Item1 -. "State" .-> Backend
    Item2 -. "State" .-> Backend
    ItemN -. "State" .-> Backend
    Pack -. "Result" .-> Backend
    Dispatch -. "Result" .-> Backend
    Feedback -. "Result" .-> Backend
```

---

## 🔄 Order Processing Workflow

| Stage | Task | What happens |
| :--- | :--- | :--- |
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
- Add monitoring and metrics (e.g., Flower or Prometheus) for queue length, task duration, retries, and worker health.

---

## 🏷️ Keywords

`Food Order Tracking System` · `FastAPI Project` · `Python Backend Project` · `Celery Task Queue` · `Redis Message Broker` · `Redis Result Backend` · `Asynchronous Processing` · `Background Tasks` · `Distributed Task Processing` · `Celery Canvas` · `Parallel Task Execution` · `Dockerized Python Application` · `REST API` · `Microservices Architecture`

---

⭐ **If you find this project useful, consider giving the repository a star!**



