"""The llm module (plan 0.B4): every model and embedding call, in one place.

Request building and fingerprints (`request`), privacy routing and dispatch (`routing`, `transport`), the run-plan check
(`run_plans`), the live and offline providers (`providers`), the `llm_runs` record (`runs`), the weekly pipeline's
stage call with its saved-artifact cache and one repair (`stage`), and the brief and pack calls (`workflow`).
"""
from .providers import (FakeProvider, IncompleteResponse, InvalidJson, JSON_STAGES, LiveProvider, ModelProvider, NoJsonContent,  # noqa: F401
                        ProviderOutputError, live_provider)
from .request import (chat_body, embedding_body, prefix_hash, repair_fingerprint, repair_user, stage_body,  # noqa: F401
                      stage_fingerprint, workflow_fingerprint)
from .routing import (ROUTING_POLICY, ROUTING_PREFERENCES, RoutingError, mark_prefix, raise_for_routing, route,  # noqa: F401
                      routing_record, send)
from .run_plans import RunPlanError  # noqa: F401
from .transport import UpstreamError  # noqa: F401
from .runs import LlmRuns, NoRuns  # noqa: F401
from .stage import StageCaller, repairable  # noqa: F401
