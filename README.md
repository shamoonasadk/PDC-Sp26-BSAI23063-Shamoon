Shamoon — BSAI-23063

# PDC Assignment 2 — Building Resilient Distributed Systems

**Student:** Shamoon  
**Student ID:** BSAI-23063  
**Course:** Parallel and Distributed Computing  
**Problem Solved:** Problem 3 — Circuit Breaker for LLM Fault Tolerance

## What This Does

Implements a Circuit Breaker pattern in FastAPI that protects the application
when an external LLM API hangs or goes down. Instead of freezing all server
threads, the breaker trips after 3 failures and returns an instant fallback.

## How to Run

### 1. Clone the repo
git clone https://github.com/shamoonasadk/PDC-Sp26-BSAI23063-Shamoon.git
cd PDC-Sp26-BSAI23063-Shamoon

### 2. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate       # Windows
source venv/bin/activate      # Mac/Linux

### 3. Install dependencies
pip install fastapi uvicorn httpx

### 4. Start the server
uvicorn main:app --reload

### 5. Run the test (in a second terminal)
python test_circuit_breaker.py

## API Endpoints

| Endpoint          | Description                              |
|-------------------|------------------------------------------|
| GET /             | Health check                             |
| GET /llm/healthy  | Normal LLM call (works fine)             |
| GET /llm/broken   | Simulates hanging LLM (triggers breaker) |
| GET /breaker/status | View current breaker state             |
| GET /breaker/reset  | Reset breaker to CLOSED                |

## Custom Header

Every response includes: X-Student-ID: BSAI-23063
