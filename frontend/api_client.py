"""HTTP/SSE client for communicating with the Recipe RAG backend API."""

import json
from dataclasses import dataclass, field
from typing import Any, Generator

import httpx


@dataclass
class StreamResult:
    """Mutable container that accumulates results as the text generator is consumed.

    Fields are populated as side effects during iteration of the text generator
    returned by `stream_chat()`.
    """

    session_id: str | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    full_text: str = ""
    error: str | None = None


def stream_chat(
    base_url: str,
    message: str,
    session_id: str | None = None,
    timeout: float = 120.0,
) -> tuple[Generator[str, None, None], StreamResult]:
    """Stream a chat response from the backend via SSE.

    Returns a (text_generator, result) tuple. The generator yields text delta
    strings suitable for ``st.write_stream``. The *result* object is populated
    as a side effect while the generator is consumed.
    """
    result = StreamResult()

    def _generate() -> Generator[str, None, None]:
        payload: dict[str, Any] = {"message": message}
        if session_id:
            payload["session_id"] = session_id

        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream(
                    "POST",
                    f"{base_url}/chat/stream",
                    json=payload,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        line = line.strip()
                        if not line or line.startswith("event:"):
                            continue
                        if not line.startswith("data:"):
                            continue

                        data_str = line[5:].strip()
                        if not data_str:
                            continue

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        event_type = data.get("type")

                        if event_type == "session":
                            result.session_id = data.get("session_id")

                        elif event_type == "text":
                            content = data.get("content", "")
                            result.full_text += content
                            yield content

                        elif event_type == "tools":
                            result.tools = data.get("tools", [])

                        elif event_type == "error":
                            result.error = data.get("content", "Unknown error")

                        elif event_type == "end":
                            break

        except httpx.ConnectError:
            result.error = (
                "Cannot connect to backend. "
                "Make sure the API server is running."
            )
        except httpx.ReadTimeout:
            result.error = "Request timed out waiting for the backend."
        except httpx.HTTPStatusError as exc:
            result.error = f"HTTP {exc.response.status_code}: {exc.response.text}"

    return _generate(), result


def check_health(base_url: str, timeout: float = 5.0) -> dict[str, Any] | None:
    """Check backend health. Returns the health dict or None on failure."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{base_url}/health")
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return None
