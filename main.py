import asyncio
import time
import enum
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# ─────────────────────────────────────────────────────
# Middleware: stamps X-Student-ID on EVERY response
# Missing this = automatic zero on Part 3
# ─────────────────────────────────────────────────────
class StudentIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Student-ID"] = "BSAI-23063"
        return response


# ─────────────────────────────────────────────────────
# Circuit Breaker States
# ─────────────────────────────────────────────────────
class CBState(enum.Enum):
    CLOSED    = "CLOSED"      # normal, requests go through
    OPEN      = "OPEN"        # tripped, requests short-circuit
    HALF_OPEN = "HALF_OPEN"   # one probe request allowed


# ─────────────────────────────────────────────────────
# Circuit Breaker Class
# ─────────────────────────────────────────────────────
class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=30, request_timeout=5):
        self.state              = CBState.CLOSED
        self.failure_count      = 0
        self.failure_threshold  = failure_threshold  # trip after this many failures
        self.recovery_timeout   = recovery_timeout   # seconds before HALF_OPEN probe
        self.request_timeout    = request_timeout    # max seconds to wait for LLM
        self.last_failure_time  = None

    def _should_attempt_reset(self):
        if self.last_failure_time is None:
            return False
        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def record_success(self):
        self.failure_count      = 0
        self.state              = CBState.CLOSED
        self.last_failure_time  = None

    def record_failure(self):
        self.failure_count     += 1
        self.last_failure_time  = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CBState.OPEN

    async def call(self, func, *args, **kwargs):
        # If OPEN, check if enough time has passed to probe
        if self.state == CBState.OPEN:
            if self._should_attempt_reset():
                self.state = CBState.HALF_OPEN
            else:
                raise Exception(
                    f"Circuit is OPEN. "
                    f"Retry after {self.recovery_timeout}s cooldown."
                )
        # CLOSED or HALF_OPEN: attempt the real call with a timeout
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.request_timeout
            )
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise e


# ─────────────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────────────
app = FastAPI(title="StudySync API — BSAI-23063")
app.add_middleware(StudentIDMiddleware)

# One shared circuit breaker for the LLM dependency
llm_breaker = CircuitBreaker(
    failure_threshold=3,   # trip after 3 consecutive failures
    recovery_timeout=30,   # wait 30s before sending a probe
    request_timeout=5      # give the LLM 5 seconds max per request
)


# ─────────────────────────────────────────────────────
# Simulated LLM call
# broken=True  → simulates API hanging (60s sleep)
# broken=False → simulates healthy response (0.5s)
# ─────────────────────────────────────────────────────
async def call_llm_api(broken: bool = False):
    if broken:
        await asyncio.sleep(60)   # hangs like a dead external API
    await asyncio.sleep(0.5)      # normal healthy latency
    return {"answer": "Here is your AI-generated study summary."}


# ─────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "status":     "StudySync API is running",
        "student_id": "BSAI-23063"
    }


@app.get("/llm/healthy")
async def llm_healthy():
    """Normal LLM call — no failure simulated."""
    try:
        result = await llm_breaker.call(call_llm_api, broken=False)
        return {
            "status":        "success",
            "breaker_state": llm_breaker.state.value,
            "data":          result
        }
    except Exception as e:
        return JSONResponse(status_code=503, content={
            "status":        "fallback",
            "breaker_state": llm_breaker.state.value,
            "message":       "AI features temporarily unavailable. Please try again later.",
            "error":         str(e)
        })


@app.get("/llm/broken")
async def llm_broken():
    """Simulates the LLM hanging — triggers the circuit breaker."""
    try:
        result = await llm_breaker.call(call_llm_api, broken=True)
        return {
            "status":        "success",
            "breaker_state": llm_breaker.state.value,
            "data":          result
        }
    except Exception as e:
        return JSONResponse(status_code=503, content={
            "status":        "fallback",
            "breaker_state": llm_breaker.state.value,
            "message":       "AI features temporarily unavailable. Please try again later.",
            "error":         str(e)
        })


@app.get("/breaker/status")
async def breaker_status():
    """Check current circuit breaker state."""
    return {
        "state":         llm_breaker.state.value,
        "failure_count": llm_breaker.failure_count,
        "threshold":     llm_breaker.failure_threshold,
        "student_id":    "BSAI-23063"
    }


@app.get("/breaker/reset")
async def breaker_reset():
    """Manually reset breaker to CLOSED (for demo use)."""
    llm_breaker.state              = CBState.CLOSED
    llm_breaker.failure_count      = 0
    llm_breaker.last_failure_time  = None
    return {
        "message": "Circuit breaker reset to CLOSED",
        "state":   llm_breaker.state.value
    }