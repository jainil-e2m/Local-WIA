"""2.B5 on a real database: every verified moment has an embedding under the archive's contract, and re-running embeds nothing new.

Synthetic moments; the embeddings come from an offline provider. No network."""
from __future__ import annotations

import json

import psycopg
import pytest

from backend_pipeline import settings_store, storage_cli
from backend_pipeline.llm.run_plans import create_sql_plan
from backend_pipeline.moments import embedding
from backend_pipeline.sql_pipeline import SQLWorker
from backend_pipeline.startup import OVERRIDE
from backend_pipeline.storage_config import StorageSettings
from backend_pipeline.tests.ledger_fixtures import MODEL, Embedder, embed_everything, ledger  # noqa: F401 (fixtures)
from backend_pipeline.tests.platform_db import platform_setup, platform_url  # noqa: F401 (fixtures)

SEARCHABLE = {"m_reply", "m_price", "m_pricing_beta", "m_praise_beta", "m_gamma", "m_staff", "m_slack"}


def vectors(repo):
    with repo.connection() as conn:
        return {r["moment_id"]: r for r in conn.execute(
            "SELECT moment_id, embedding IS NOT NULL AS embedded, embedding_model, embedding_input_hash FROM key_moments")}


def job_of(repo):
    with repo.connection() as conn:
        # The newest by its run, whose dating is in order (repository.DATED_IN_ORDER); a job's own created_at may step back.
        return conn.execute("""SELECT j.* FROM pipeline_jobs j JOIN pipeline_runs r USING(run_id) WHERE j.stage='moment_embedding'
            ORDER BY r.created_at DESC,j.created_at DESC""").fetchone()


def test_every_verified_current_moment_is_embedded_under_the_contract_and_no_other(ledger):
    repo, models, _, embedder = ledger
    queued = embed_everything(repo, models, embedder)
    assert queued["queued"] == 7 and queued["input_set_hash"].startswith("sha256:")
    state = vectors(repo)
    assert {m for m, r in state.items() if r["embedded"]} == SEARCHABLE
    assert all(state[m]["embedding_model"] == MODEL and state[m]["embedding_input_hash"] for m in SEARCHABLE)
    assert not state["m_unverified"]["embedded"] and not state["m_old"]["embedded"], "unverified and superseded moments are never embedded"
    job = job_of(repo)
    assert job["status"] == "completed" and job["queue"] == "bulk" and job["result_refs"]["embedded"] == 7
    with repo.connection() as conn:
        report = embedding.report(conn, models)
    assert report["complete"] is True and report["searchable"] == 7 and report["embedded"] == 7 and report["unverified_with_vector"] == 0


def test_the_database_itself_refuses_a_vector_on_an_unverified_moment(ledger):
    repo, models, _, embedder = ledger
    with repo.connection() as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("UPDATE key_moments SET embedding=%s, embedding_model=%s, embedding_input_hash='x' WHERE moment_id='m_unverified'",
                         ([0.1] * 1536, MODEL))


def test_running_again_embeds_nothing_new(ledger):
    repo, models, _, embedder = ledger
    embed_everything(repo, models, embedder)
    spent = list(embedder.embedded)
    again = embedding.queue(repo, models, mode="cached")
    assert again["queued"] == 0 and again["moments"] == 0
    with repo.connection() as conn:
        assert embedding.estimate(conn, models)["moments"] == 0
    assert embedder.embedded == spent, "no text was sent a second time"


def test_only_a_moment_whose_text_changed_is_embedded_again(ledger):
    repo, models, _, embedder = ledger
    embed_everything(repo, models, embedder)
    before = vectors(repo)
    with repo.connection() as conn:
        conn.execute("UPDATE key_moments SET moment_body = jsonb_set(moment_body, '{proposition}', '\"Dana described the speed of replies\"') "
                     "WHERE moment_id='m_reply'")
    with repo.connection() as conn:
        pending, _ = embedding.pending(conn, models)
    assert [p["moment_id"] for p in pending] == ["m_reply"]
    sent = len(embedder.embedded)
    embed_everything(repo, models, embedder)
    after = vectors(repo)
    assert len(embedder.embedded) == sent + 1
    assert after["m_reply"]["embedding_input_hash"] != before["m_reply"]["embedding_input_hash"]
    assert all(after[m]["embedding_input_hash"] == before[m]["embedding_input_hash"] for m in SEARCHABLE - {"m_reply"})


def test_a_moment_that_is_superseded_or_unverified_after_queueing_is_left_alone(ledger):
    repo, models, _, embedder = ledger
    queued = embedding.queue(repo, models, mode="cached")
    assert queued["queued"] == 7
    with repo.connection() as conn:
        conn.execute("UPDATE key_moments SET is_current=false WHERE moment_id='m_slack'")
        conn.execute("""UPDATE key_moments SET quote_verified=false, unverified_reason='A person unverified it' WHERE moment_id='m_gamma'""")
    assert SQLWorker(repo.settings, models, provider=embedder).once()
    state = vectors(repo)
    assert not state["m_slack"]["embedded"] and not state["m_gamma"]["embedded"]
    assert job_of(repo)["result_refs"]["skipped"]["changed"] == 2 and job_of(repo)["result_refs"]["embedded"] == 5


def test_requests_are_batched_by_the_setting(ledger):
    repo, models, _, embedder = ledger
    with repo.connection() as conn:
        settings_store.set_value(conn, "moments.embedding.batch_size", 3, "tester@example.invalid")
    embed_everything(repo, models, embedder)
    assert embedder.batches == [3, 3, 1]


def test_the_estimate_states_count_tokens_cost_and_the_plan_input_and_makes_no_call(ledger):
    repo, models, _, embedder = ledger
    with repo.connection() as conn:
        estimate = embedding.estimate(conn, models)
    assert estimate["moments"] == 7 and estimate["estimated_tokens"] > 0 and estimate["estimated_cost_usd"] > 0
    assert estimate["requests"] == 1 and estimate["embedding_model"] == MODEL
    assert estimate["run_plan"] == {"stage": "embedding", "model": MODEL, "input_set_hash": estimate["input_set_hash"], "max_calls": 1}
    assert embedder.embedded == [] and job_of(repo) is None, "an estimate sends and queues nothing"


def test_the_embedding_text_is_the_quote_the_record_and_the_setup_and_is_deterministic():
    body = {"quote": "We reply  within five minutes.", "proposition": "Dana described the reply time", "context_summary": "A check-in"}
    text = embedding.embedding_text(body)
    assert text == "Quote: We reply within five minutes.\nScene: Dana described the reply time\nSetup: A check-in"
    assert embedding.embedding_text(dict(body)) == text and embedding.input_hash(text) == embedding.input_hash(text)
    assert embedding.input_hash(text) != embedding.input_hash(text + " ")
    assert embedding.embedding_text({"quote": "Only a quote"}) == "Quote: Only a quote"
    assert embedding.embedding_text({"proposition": "no quote"}) is None
    long = embedding.embedding_text({"quote": "q" * 200, "proposition": "r" * 9000, "context_summary": "s" * 9000})
    assert len(long) <= embedding.MAX_CHARACTERS and long.startswith("Quote: " + "q" * 200)


def test_a_mismatched_contract_refuses_to_queue_and_to_run(ledger, monkeypatch):
    repo, models, _, embedder = ledger
    with pytest.raises(ValueError, match="1536"):
        embedding.queue(repo, models.model_copy(update={"embedding_dimensions": 768}))
    queued = embedding.queue(repo, models, mode="cached")
    other = models.model_copy(update={"embedding_model": "openai/text-embedding-3-large"})
    assert SQLWorker(repo.settings, other, provider=embedder).once()
    job = job_of(repo)
    assert job["status"] == "failed" and "contract changed" in job["error_summary"] and embedder.embedded == []
    assert queued["queued"] == 7
    # Vectors made under another model are never mixed with this process's.
    embed_everything(repo, models, embedder)
    with pytest.raises(ValueError, match="another|made under"):
        embedding.queue(repo, other)
    with repo.connection() as conn:
        conn.execute("UPDATE key_moments SET embedding_model='some/other-model' WHERE moment_id='m_reply'")
    with pytest.raises(ValueError, match="some/other-model"):
        embedding.queue(repo, models)
    # Only while deliberately re-encoding is that lifted, and the moment is then pending again.
    monkeypatch.setenv(OVERRIDE, "true")
    assert embedding.queue(repo, models)["queued"] == 1


def test_a_live_run_needs_the_encoding_catch_and_an_active_plan_for_exactly_this_input_set(ledger, monkeypatch):
    repo, models, tmp_path, _ = ledger
    with pytest.raises(ValueError, match="permission is disabled"):
        embedding.queue(repo, models, mode="live")
    live_repo = type(repo)(repo.settings.model_copy(update={"encoding_enabled": True}))
    queued = embedding.queue(live_repo, models, mode="live")
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    monkeypatch.delenv("ATELIER_RUN_PLAN_ID", raising=False)
    worker = SQLWorker(live_repo.settings, models)
    assert worker.once()
    job = job_of(repo)
    assert job["status"] == "failed" and "run plan" in job["error_summary"], job["error_summary"]
    # A plan approved for another set of moments is refused; one for this set gets as far as the network, which tests forbid.
    with repo.connection() as conn:
        wrong = create_sql_plan(conn, purpose="x", stages=["embedding"], models=[MODEL], input_set_hash="sha256:other", max_calls=3,
                                max_cost_usd=1, approver="whitney@example.invalid")
    monkeypatch.setenv("ATELIER_DATABASE_URL", repo.settings.database_url)
    monkeypatch.setenv("ATELIER_RUN_PLAN_ID", wrong["plan_id"])
    with repo.connection() as conn:
        conn.execute("UPDATE pipeline_jobs SET status='queued', error_summary=NULL WHERE job_id=%s", (job["job_id"],))
        conn.execute("UPDATE pipeline_runs SET status='queued' WHERE run_id=%s", (job["run_id"],))
    assert SQLWorker(live_repo.settings, models).once()
    assert "another input set" in job_of(repo)["error_summary"]
    with repo.connection() as conn:
        right = create_sql_plan(conn, purpose="x", stages=["embedding"], models=[MODEL], input_set_hash=queued["input_set_hash"],
                                max_calls=3, max_cost_usd=1, approver="whitney@example.invalid")
        conn.execute("UPDATE pipeline_jobs SET status='queued', error_summary=NULL WHERE job_id=%s", (job["job_id"],))
        conn.execute("UPDATE pipeline_runs SET status='queued' WHERE run_id=%s", (job["run_id"],))
    monkeypatch.setenv("ATELIER_RUN_PLAN_ID", right["plan_id"])
    assert SQLWorker(live_repo.settings, models).once()
    assert "Verification forbids outbound HTTP" in job_of(repo)["error_summary"], "the plan accepted the call; only the network stopped it"
    with repo.connection() as conn:
        assert conn.execute("SELECT calls_used FROM run_plans WHERE plan_id=%s", (right["plan_id"],)).fetchone()["calls_used"] == 1


def test_a_retried_job_reuses_saved_vectors_instead_of_paying_again(ledger):
    repo, models, _, embedder = ledger
    embed_everything(repo, models, embedder)
    with repo.connection() as conn:
        conn.execute("UPDATE key_moments SET embedding=NULL, embedding_model=NULL, embedding_input_hash=NULL")
    sent = len(embedder.embedded)
    embed_everything(repo, models, embedder)
    assert len(embedder.embedded) == sent, "every vector came from the saved responses"
    assert job_of(repo)["result_refs"]["cache_reused"] >= 1 and job_of(repo)["result_refs"]["embedding_dispatches"] == 0
    with repo.connection() as conn:
        assert embedding.report(conn, models)["complete"] is True


def test_queueing_twice_before_the_worker_runs_is_one_job(ledger):
    repo, models, _, _ = ledger
    first = embedding.queue(repo, models, mode="cached")
    second = embedding.queue(repo, models, mode="cached")
    assert second["queued"] == 0 and second["already_queued"] is True and second["job_id"] == first["job_id"]


def test_the_commands_estimate_report_and_queue(ledger, monkeypatch, capsys):
    repo, models, _, embedder = ledger
    monkeypatch.setattr(StorageSettings, "from_env", classmethod(lambda cls: repo.settings))
    monkeypatch.setattr(type(models), "from_env", classmethod(lambda cls: models))

    def run(*argv):
        capsys.readouterr()
        storage_cli.main(list(argv))
        return json.loads(capsys.readouterr().out)
    assert run("moments-embed", "queue", "--estimate")["moments"] == 7 and job_of(repo) is None
    assert run("moments-embed", "report")["complete"] is False
    assert run("moments-embed", "queue", "--ids", "m_reply", "m_price")["queued"] == 2
