import pytest
from fastapi.testclient import TestClient
from pytest import approx

from chargeplan.api.app import MAX_BODY_BYTES, app
from chargeplan.scenarios import SCENARIOS

client = TestClient(app)


def example(key="early_departure") -> dict:
    response = client.get(f"/api/examples/{key}")
    assert response.status_code == 200
    return response.json()


def solve(body: dict) -> dict:
    response = client.post("/api/plan", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_examples_list_every_bundled_scenario():
    keys = [e["key"] for e in client.get("/api/examples").json()]
    assert keys == list(SCENARIOS)


def test_example_inputs_use_local_times_without_offsets():
    body = example("hand_checkable")
    assert body["horizon_start"] == "2026-10-15T18:00:00"
    assert body["vehicles"][0]["departure"] == "2026-10-16T08:00:00"
    assert client.get("/api/examples/nope").status_code == 404


def test_example_round_trip_solves_to_the_hand_checked_numbers():
    result = solve(example("hand_checkable"))
    assert result["status"] == "optimal"
    assert result["optimized"]["total_cost"] == approx(4.80)
    assert result["baseline"]["total_cost"] == approx(12.00)
    assert result["slots"][0]["start"] == "2026-10-15T18:00:00-04:00"  # outputs carry the UTC offset


def test_changing_a_departure_changes_the_result():
    body = example("early_departure")
    before = solve(body)["optimized"]["total_cost"]  # Van A leaves 23:00, before cheap hours
    body["vehicles"][0]["departure"] = "2026-10-16T08:00:00"
    after = solve(body)["optimized"]["total_cost"]
    assert before == approx(8.40) and after == approx(4.80)


def test_changing_a_rate_changes_the_result():
    body = example("hand_checkable")
    body["rates"][1]["price_per_kwh"] = 0.30  # cheap period no longer cheap: flat $0.30
    result = solve(body)
    assert result["optimized"]["total_cost"] == approx(12.00)
    assert result["comparison"]["savings"] == 0


def test_domain_problems_come_back_as_issues_not_http_errors():
    body = example()
    body["efficiency"] = 1.5
    body["vehicles"][1]["departure"] = body["vehicles"][1]["arrival"]
    result = solve(body)
    assert result["status"] == "invalid"
    fields = {issue["field"] for issue in result["issues"]}
    assert {"efficiency", "vehicles[1].departure"} <= fields


def test_impossible_plan_is_reported_as_infeasible():
    result = solve(example("not_enough_time"))
    assert result["status"] == "infeasible"
    assert result["infeasibility_reasons"][0].startswith("Van B needs")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b.pop("rates"),  # missing field
        lambda b: b.update(site_limit_kw="ten"),  # wrong type
        lambda b: b.update(surprise=1),  # unknown field
    ],
)
def test_malformed_requests_are_rejected_with_422(mutate):
    body = example()
    mutate(body)
    assert client.post("/api/plan", json=body).status_code == 422


def test_oversized_requests_are_rejected():
    response = client.post("/api/plan", content=b" " * (MAX_BODY_BYTES + 1), headers={"content-type": "application/json"})
    assert response.status_code == 413
