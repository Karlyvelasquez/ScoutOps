"""Langfuse tracing helpers for instrumenting async workflow nodes."""

from __future__ import annotations

import os
import time
import importlib
import inspect
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from dotenv import load_dotenv

from observability.logs import get_logger

logger = get_logger(__name__)
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


_langfuse_client: Any | None = None


class _NoopSpan:
    def update(self, **_: Any) -> None:
        return

    def end(self) -> None:
        return


class _NoopLangfuse:
    def span(self, **_: Any) -> _NoopSpan:
        return _NoopSpan()

    def start_observation(self, **_: Any) -> _NoopSpan:
        return _NoopSpan()


def _start_span(client: Any, name: str, input_payload: dict[str, Any]) -> Any:
    """Create a tracing span/observation compatible across Langfuse SDK versions."""
    if hasattr(client, "span"):
        return client.span(name=name, input=input_payload)

    if hasattr(client, "start_observation"):
        try:
            return client.start_observation(name=name, input=input_payload)
        except TypeError:
            # Older signatures may not accept input directly.
            return client.start_observation(name=name)

    return _NoopSpan()


def get_langfuse_client() -> Any:
    """Return a singleton Langfuse client configured from environment variables."""
    global _langfuse_client

    if _langfuse_client is not None:
        return _langfuse_client

    load_dotenv()
    try:
        langfuse_module = importlib.import_module("langfuse")
        Langfuse = getattr(langfuse_module, "Langfuse")

        _langfuse_client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    except Exception:
        logger.warning(
            "langfuse_client_init_failed_using_noop",
            extra={"service": "observability", "node_name": "trace_node"},
        )
        _langfuse_client = _NoopLangfuse()

    return _langfuse_client


def trace_node(name: str) -> Callable[[F], F]:
    """Decorator that records node execution spans in Langfuse."""

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                client = get_langfuse_client()
                start = time.perf_counter()
                generation = _start_span(client, name, {"args": str(args), "kwargs": kwargs})

                try:
                    result = await func(*args, **kwargs)
                    latency_ms = (time.perf_counter() - start) * 1000.0
                    generation.update(
                        output=result,
                        metadata={"latency_ms": round(latency_ms, 2), "status": "success"},
                    )
                    generation.end()
                    return result
                except Exception as exc:
                    latency_ms = (time.perf_counter() - start) * 1000.0
                    generation.update(
                        output={"error": str(exc)},
                        metadata={"latency_ms": round(latency_ms, 2), "status": "error"},
                    )
                    generation.end()
                    logger.exception(
                        "trace_node_failed",
                        extra={"service": "observability", "node_name": name},
                    )
                    raise

            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            client = get_langfuse_client()
            start = time.perf_counter()
            generation = _start_span(client, name, {"args": str(args), "kwargs": kwargs})

            try:
                result = func(*args, **kwargs)
                latency_ms = (time.perf_counter() - start) * 1000.0
                generation.update(
                    output=result,
                    metadata={"latency_ms": round(latency_ms, 2), "status": "success"},
                )
                generation.end()
                return result
            except Exception as exc:
                latency_ms = (time.perf_counter() - start) * 1000.0
                generation.update(
                    output={"error": str(exc)},
                    metadata={"latency_ms": round(latency_ms, 2), "status": "error"},
                )
                generation.end()
                logger.exception(
                    "trace_node_failed",
                    extra={"service": "observability", "node_name": name},
                )
                raise

        return sync_wrapper  # type: ignore[return-value]

    return decorator
