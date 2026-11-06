"""0.B11: the small things the plan lists under housekeeping."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.errors import UndefinedColumn, UndefinedTable

from backend_pipeline.errors import SCHEMA_NOT_READY, install_schema_handler

BACKEND = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("error", [UndefinedTable, UndefinedColumn])
def test_a_database_behind_the_code_answers_503_on_every_route(error):
    app = FastAPI()
    install_schema_handler(app)

    @app.get("/anything")
    def anything():
        raise error('relation "intake_sources" does not exist')
    response = TestClient(app, raise_server_exceptions=False).get("/anything")
    assert response.status_code == 503 and response.json() == {"detail": SCHEMA_NOT_READY}


def test_the_real_app_installs_the_handler():
    from backend_pipeline.api import app
    assert UndefinedTable in app.exception_handlers and UndefinedColumn in app.exception_handlers


def test_the_intake_action_wrapper_maps_it_too():
    import inspect

    import backend_pipeline.intake.api as intake
    source = inspect.getsource(intake.routers)
    assert "except (UndefinedTable, UndefinedColumn)" in source and "SCHEMA_NOT_READY" in source


def test_unused_pins_are_gone_and_the_ones_the_legacy_runner_needs_stay():
    for name in ("requirements.txt", "pyproject.toml"):
        text = (BACKEND / name).read_text(encoding="utf-8")
        assert not re.search(r"\b(sqlalchemy|openai)\b\s*==", text, re.I), name
        assert "tiktoken" in text and "tokenizers" in text and "boto3" in text, name
    imported = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (BACKEND / "backend_pipeline").rglob("*.py")
                         if "tests" not in p.parts)
    assert not re.search(r"^\s*(import|from) (sqlalchemy|openai)\b", imported, re.M)


def test_the_stale_compose_file_is_gone_and_the_stack_is_one_file():
    assert not (BACKEND / "docker-compose.pipeline.yml").exists()
    for name in ("compose.storage.yml", "compose.editorial.yml", "compose.intake.yml"):
        assert not (BACKEND / name).exists()
    assert (BACKEND / "compose.yml").exists()


def test_retrieval_keeps_its_docstring_first():
    import backend_pipeline.retrieval as retrieval
    assert retrieval.__doc__ and retrieval.__doc__.startswith("Filtered exact semantic")
