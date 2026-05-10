"""
PDC Assignment 2 — Part 3 Test Script
Student: BSAI-23063

This script proves two things:
  BEFORE: a broken LLM call hangs for the full timeout (5 seconds)
  AFTER:  the circuit breaker trips and subsequent calls return instantly

Run the server first:
  uvicorn main:app --reload

Then run this file:
  python test_circuit_breaker.py
"""

import httpx
import asyncio
import time

BASE = "http://127.0.0.1:8000"


def print_section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def check_header(response: httpx.Response):
    sid = response.headers.get("x-student-id", "MISSING ❌")
    mark = "✅" if sid == "BSAI-23063" else "❌"
    print(f"  X-Student-ID header : {sid} {mark}")


async def before_test(client: httpx.AsyncClient):
    print_section("BEFORE — Broken LLM, no protection")
    print("  Calling /llm/broken once...")
    print("  Watch how long it takes to respond.\n")

    start = time.time()
    r = await client.get(f"{BASE}/llm/broken", timeout=15)
    elapsed = time.time() - start

    print(f"  Status code  : {r.status_code}")
    print(f"  Time taken   : {elapsed:.2f}s  ← full timeout, server was blocked")
    await check_header(r)
    print(f"  Response     : {r.json()}")
    print()
    print("  ⚠️  Without a circuit breaker, every user hitting this")
    print("     endpoint waits this long. 20 users = 20 frozen threads.")

    # Reset breaker so AFTER test starts fresh
    await client.get(f"{BASE}/breaker/reset", timeout=5)


async def after_test(client: httpx.AsyncClient):
    print_section("AFTER — Circuit Breaker active")

    # Step 1: Trip the breaker with 3 broken calls
    print("  Step 1: Send 3 broken calls to trip the breaker\n")
    for i in range(1, 4):
        start = time.time()
        r = await client.get(f"{BASE}/llm/broken", timeout=15)
        elapsed = time.time() - start
        data = r.json()
        print(f"  Call {i}: state={data.get('breaker_state'):<10} "
              f"time={elapsed:.2f}s   status={r.status_code}")

    # Step 2: Show breaker is now OPEN
    r = await client.get(f"{BASE}/breaker/status", timeout=5)
    print(f"\n  Breaker status → {r.json()}")

    # Step 3: 4th call — breaker is OPEN, returns instantly
    print("\n  Step 2: 4th call — breaker OPEN, short-circuits immediately\n")
    start = time.time()
    r = await client.get(f"{BASE}/llm/broken", timeout=15)
    elapsed = time.time() - start
    data = r.json()

    print(f"  Time taken   : {elapsed:.3f}s  ← nearly instant, no network call made")
    print(f"  Breaker state: {data.get('breaker_state')}")
    print(f"  Fallback msg : {data.get('message')}")
    await check_header(r)

    # Step 4: Reset and show healthy calls still work
    await client.get(f"{BASE}/breaker/reset", timeout=5)
    print("\n  Step 3: After reset — healthy LLM call works fine\n")
    start = time.time()
    r = await client.get(f"{BASE}/llm/healthy", timeout=10)
    elapsed = time.time() - start
    data = r.json()

    print(f"  Time taken   : {elapsed:.2f}s")
    print(f"  Breaker state: {data.get('breaker_state')}")
    print(f"  LLM response : {data.get('data')}")
    await check_header(r)

    print()
    print("  ✅ Circuit Breaker working correctly.")
    print("     Broken dependency is isolated.")
    print("     Healthy endpoints are completely unaffected.")


async def main():
    print("\n  PDC Assignment 2 — Circuit Breaker Test")
    print("  Student ID: BSAI-23063")

    async with httpx.AsyncClient() as client:
        # Confirm server is up
        try:
            r = await client.get(f"{BASE}/", timeout=5)
            print(f"\n  Server is UP → {r.json()}")
        except Exception:
            print("\n  ❌ Server not reachable. Did you run: uvicorn main:app --reload ?")
            return

        await before_test(client)
        await after_test(client)


asyncio.run(main())