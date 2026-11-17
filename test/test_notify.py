"""Unit tests for the lakeFS -> Airflow shim.

Run: PYTHONPATH=src python -m pytest test/test_notify.py -q
"""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

main = pytest.importorskip("DugLakefsEventListeners.main")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "HOOK_TOKEN", "s3cret")
    main.app.config.update(TESTING=True)
    return main.app.test_client()


def fake_runner(returncode=0, stderr="", stdout=""):
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=returncode, stderr=stderr,
                               stdout=stdout)

    runner.calls = calls
    return runner


def test_run_id_is_keyed_by_commit():
    """One run per commit. Re-delivery of the same event must land on the
    same run id (idempotent), and a new commit must get its own run --
    time-bucketing them could drop a commit that arrived while the window's
    run was already executing."""
    a = main.run_id_for("heal-cdes", "abc123def4567890")
    again = main.run_id_for("heal-cdes", "abc123def4567890")
    other = main.run_id_for("heal-cdes", "ffff1111222233334")
    assert a == again
    assert a != other
    assert a == "lakefs__heal-cdes__abc123def456"


def test_run_id_falls_back_when_payload_has_no_commit():
    now = datetime(2026, 8, 26, 14, 3, 9, tzinfo=timezone.utc)
    assert main.run_id_for("r", None, now) == "lakefs__r__20260826T140309"


def test_dag_map_routes_kgx_repos_elsewhere(monkeypatch):
    """KGX repos feed knowledge_graph_build, not annotate_and_index."""
    monkeypatch.setattr(main, "DAG_MAP",
                        {"heal-mds-kgx": "knowledge_graph_build"})
    monkeypatch.setattr(main, "DEFAULT_DAG", "annotate_and_index")
    assert main.dag_for("heal-mds-kgx") == "knowledge_graph_build"
    assert main.dag_for("heal-mds-studies") == "annotate_and_index"


def test_conf_asks_for_incremental_and_no_commit_range():
    """Passing repository_id/commitid_from/commitid_to would send roger down
    its manual-override path and bypass the per-task incremental state."""
    runner = fake_runner()
    ok, _ = main.trigger("annotate_and_index", "rid", {"incremental": True},
                         runner=runner)
    assert ok
    cmd = runner.calls[0]
    conf = json.loads(cmd[cmd.index("--conf") + 1])
    assert conf["incremental"] is True
    assert "commitid_from" not in conf and "commitid_to" not in conf


def test_duplicate_run_id_is_success():
    "Second webhook in the same window must not fail the lakeFS action."
    runner = fake_runner(returncode=1,
                         stderr="DagRunAlreadyExists: run id already exists")
    ok, detail = main.trigger("annotate_and_index", "rid", {}, runner=runner)
    assert ok and "already queued" in detail


def test_real_trigger_failure_is_reported():
    runner = fake_runner(returncode=1, stderr="boom: no such dag")
    ok, detail = main.trigger("nope", "rid", {}, runner=runner)
    assert not ok and "boom" in detail


def test_notify_requires_token(client):
    r = client.post("/lakefs/notify", json={"repository_id": "x"})
    assert r.status_code == 403


def test_notify_rejects_payload_without_repo(client):
    r = client.post("/lakefs/notify", json={"event_type": "post-commit"},
                    headers={"X-Roger-Token": "s3cret"})
    assert r.status_code == 400


def test_notify_triggers(monkeypatch, client):
    runner = fake_runner()
    monkeypatch.setattr(main.subprocess, "run", runner)
    r = client.post("/lakefs/notify",
                    json={"event_type": "post-commit",
                          "repository_id": "heal-mds-studies",
                          "branch_id": "main", "commit_id": "abc123"},
                    headers={"X-Roger-Token": "s3cret"})
    assert r.status_code == 200, r.data
    body = r.get_json()
    assert body["dag_id"] == "annotate_and_index"
    assert body["dag_run_id"].startswith("lakefs__heal-mds-studies__")
    conf = json.loads(runner.calls[0][runner.calls[0].index("--conf") + 1])
    assert conf["source_commit"] == "abc123"
    assert body["dag_run_id"] == "lakefs__heal-mds-studies__abc123"
