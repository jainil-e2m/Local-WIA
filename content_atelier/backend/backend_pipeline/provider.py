"""Compatibility alias for the llm module (plan 0.B4).

The provider, routing and request code moved to `backend_pipeline.llm`. This module only re-exports its public names so
the experiment runners kept under research/ (which import `backend_pipeline.provider`) keep working; nothing in the
package imports from here, and no request code lives here.
"""
from .llm.providers import FakeProvider, LiveProvider, ModelProvider  # noqa: F401
from .llm.request import chat_body, embedding_body  # noqa: F401
from .llm.routing import (ROUTING_POLICY, ROUTING_PREFERENCES, RoutingError, raise_for_routing, route, routing_record,  # noqa: F401
                          send)
