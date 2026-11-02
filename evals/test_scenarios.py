import asyncio
import copy
import json
from pathlib import Path

import pytest

from evals.agent_run import run_turn
from src.config import ORDERS, TODAY

pytestmark = pytest.mark.anyio

SCENARIOS_PATH = Path(__file__).parent / "scenarios.jsonl"
SCENARIOS = [json.loads(line) for line in SCENARIOS_PATH.read_text().splitlines() if line]
MUTATING = ("cancel_order", "change_address", "create_refund")


def check_orders(scenario: dict, orders: dict) -> list[str]:
    errors = []
    expected = copy.deepcopy(ORDERS)
    for order_id, fields in scenario.get("orders", {}).items():
        expected[int(order_id)].update(fields)
    for order_id, words in scenario.get("address_has", {}).items():
        address = orders[int(order_id)].get("address", "")
        missing = [w for w in words if w.lower() not in address.lower()]
        if missing:
            errors.append(f"адрес {order_id} = {address!r}, нет {missing}")
        expected[int(order_id)]["address"] = address

    for order_id in sorted(set(expected) | set(orders)):
        if orders.get(order_id) != expected.get(order_id):
            errors.append(f"заказ {order_id}: ждали {expected.get(order_id)}, стало {orders.get(order_id)}")
    return errors


def check_refunds(scenario: dict, refunds: list[dict]) -> list[str]:
    actual = sorted([r["order_id"], r["amount_rub"]] for r in refunds)
    expected = sorted(scenario["refunds"])
    return [] if actual == expected else [f"возвраты: ждали {expected}, стало {actual}"]


def check_calls(scenario: dict, calls: list[dict]) -> list[str]:
    names = [c["name"] for c in calls]
    errors = [f"не вызван {name}" for name in scenario.get("calls_include", []) if name not in names]
    for i, call in enumerate(calls):
        if call["name"] not in MUTATING:
            continue
        order_id = call["args"].get("order_id")
        looked_up = any(c["name"] == "get_order" and c["args"].get("order_id") == order_id for c in calls[:i])
        if not looked_up:
            errors.append(f"{call['name']}({order_id}) без get_order перед ним")
    return errors


def check_answer(scenario: dict, answer: str) -> list[str]:
    return [f"в ответе нет {word!r}" for word in scenario.get("answer_has", []) if word not in answer]


def check(scenario: dict, run: dict) -> list[str]:
    return [
        *check_orders(scenario, run["orders"]),
        *check_refunds(scenario, run["refunds"]),
        *check_calls(scenario, run["calls"]),
        *check_answer(scenario, run["answer"]),
    ]


def describe(run: dict, errors: list[str]) -> str:
    calls = [(c["name"], c["args"]) for c in run["calls"]]
    lines = [*(f"  - {e}" for e in errors), f"  вызовы: {calls}", f"  ответ: {run['answer'][:300]}"]
    return "\n".join(lines)


def summarize(scenario: dict, batch: list[dict], checks: list[list[str]]) -> dict:
    costs = [run["usage"].get("cost_usd") for run in batch]
    return {
        "id": scenario["id"],
        "kind": scenario["kind"],
        "passed": sum(not errors for errors in checks),
        "steps": sum(run["usage"].get("steps", 0) for run in batch) / len(batch),
        "cost": None if None in costs else sum(costs),
    }


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
async def test_scenario(scenario, runs, aclient, chunks, results):
    batch = await asyncio.gather(
        *(run_turn(scenario["query"], aclient, ORDERS, TODAY, chunks) for _ in range(runs))
    )
    checks = [check(scenario, run) for run in batch]
    results.append(summarize(scenario, batch, checks))

    failed = [
        f"прогон {i}:\n{describe(run, errors)}"
        for i, (run, errors) in enumerate(zip(batch, checks), 1)
        if errors
    ]
    assert not failed, f"{scenario['id']} {scenario['query']}\n" + "\n".join(failed)
