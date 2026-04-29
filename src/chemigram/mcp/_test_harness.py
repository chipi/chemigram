"""In-memory MCP client/server harness for integration tests.

Pairs a :class:`Server` and :class:`ClientSession` over an in-memory pair of
``MemoryObjectSendStream`` / ``MemoryObjectReceiveStream`` instances. Used by
the per-tool batch integration tests (#13/#14/#15) and the gate test (#16).

Public API:
    - :func:`in_memory_session` — async context manager yielding ``ClientSession``
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import anyio
from mcp import types
from mcp.client.session import ClientSession
from mcp.server import Server
from mcp.shared.message import SessionMessage


@asynccontextmanager
async def in_memory_session(
    server: Server[Any, Any],
) -> AsyncIterator[ClientSession]:
    """Run ``server`` in a background task; yield a connected ``ClientSession``.

    The harness uses two memory streams:
      - server reads from ``client_to_server``, writes to ``server_to_client``
      - client reads from ``server_to_client``, writes to ``client_to_server``

    The streams carry :class:`SessionMessage` instances per the MCP SDK's
    transport contract.
    """
    client_to_server_send, client_to_server_recv = anyio.create_memory_object_stream[
        SessionMessage | Exception
    ](max_buffer_size=10)
    server_to_client_send, server_to_client_recv = anyio.create_memory_object_stream[
        SessionMessage | Exception
    ](max_buffer_size=10)

    init_options = server.create_initialization_options()

    async with anyio.create_task_group() as tg:

        async def run_server() -> None:
            await server.run(
                client_to_server_recv,
                server_to_client_send,
                init_options,
                raise_exceptions=True,
            )

        tg.start_soon(run_server)

        async with ClientSession(
            read_stream=server_to_client_recv,
            write_stream=client_to_server_send,
            client_info=types.Implementation(
                name="chemigram-test-harness",
                version="0.0.0",
            ),
        ) as session:
            await session.initialize()
            try:
                yield session
            finally:
                tg.cancel_scope.cancel()
