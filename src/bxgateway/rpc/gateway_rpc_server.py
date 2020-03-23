import asyncio
import json
import base64
from typing import TYPE_CHECKING, Callable, Awaitable, Optional
from aiohttp import web
from aiohttp.web import Application, Request, Response, AppRunner, TCPSite
from aiohttp.web_exceptions import HTTPClientError
from aiohttp.web_exceptions import HTTPUnauthorized

from bxgateway.rpc import rpc_constants
from bxgateway.rpc.request_formatter import RequestFormatter
from bxgateway.rpc.response_formatter import ResponseFormatter

from bxutils import logging

from bxgateway.rpc.rpc_request_handler import RPCRequestHandler

if TYPE_CHECKING:
    from bxgateway.connections.abstract_gateway_node import AbstractGatewayNode

logger = logging.get_logger(__name__)


@web.middleware
async def request_middleware(request: Request, handler: Callable[[Request], Awaitable[Response]]) -> Response:
    request_formatter = RequestFormatter(request)
    logger.trace("Handling RPC request: {}.", request_formatter)
    response = await handler(request)
    logger.trace(
        "Finished handling request: {}, returning response: {}.", request_formatter, ResponseFormatter(response)
    )
    return response


class GatewayRpcServer:
    RUN_SLEEP_INTERVAL_S: int = 5

    def __init__(self, node: "AbstractGatewayNode"):
        self._node = node
        self._app = Application(middlewares=[request_middleware])
        self._app.add_routes([web.post("/", self.handle_request), web.get("/", self.handle_get_request)])
        self._runner = AppRunner(self._app)
        self._site = None
        self._handler = RPCRequestHandler(self._node)
        self._stop_requested = False
        self._stop_waiter = asyncio.get_event_loop().create_future()
        self._started = False
        self._encoded_auth: Optional[str] = None
        rpc_user = self._node.opts.rpc_user
        if rpc_user:
            rpc_password = self._node.opts.rpc_password
            self._encoded_auth = base64.b64encode(f"{rpc_user}:{rpc_password}".encode("utf-8")).decode("utf-8")

    async def run(self) -> None:
        try:
            await self._start()
            while not self._stop_requested:
                await asyncio.sleep(self.RUN_SLEEP_INTERVAL_S)
        finally:
            self._stop_waiter.set_result(True)

    async def start(self) -> None:
        if self._started:
            return
        try:
            await self._start()
        finally:
            self._stop_waiter.set_result(True)

    async def stop(self) -> None:
        self._stop_requested = True
        await self._stop_waiter
        await self._runner.cleanup()

    async def handle_request(self, request: Request) -> Response:
        try:
            self._authenticate_request(request)
            return await self._handler.handle_request(request)
        except HTTPClientError as e:
            return self._format_client_error(e)

    async def handle_get_request(self, request: Request) -> Response:
        try:
            self._authenticate_request(request)
        except HTTPUnauthorized as e:
            return self._format_client_error(e)
        else:
            return web.json_response({
                "required_request_type": "POST",
                "required_headers": [{RPCRequestHandler.CONTENT_TYPE: RPCRequestHandler.PLAIN}],
                "payload_structures": await self._handler.help()
            })

    async def _start(self) -> None:
        self._started = True
        await self._runner.setup()
        opts = self._node.opts
        self._site = TCPSite(self._runner, opts.rpc_host, opts.rpc_port)
        await self._site.start()

    def _format_client_error(self, client_error: HTTPClientError) -> HTTPClientError:
        err_msg = client_error.text
        code = client_error.status_code
        request_id = self._handler.request_id
        response_json = {
            "result": None,
            "error": err_msg,
            "code": code,
            "message": err_msg,
            "id": request_id
        }
        client_error.text = json.dumps(response_json)
        return client_error

    def _authenticate_request(self, request: Request) -> None:
        is_authenticated = True
        if self._encoded_auth is not None:
            if rpc_constants.AUTHORIZATION_HEADER_KEY in request.headers:
                is_authenticated = self._encoded_auth == request.headers[rpc_constants.AUTHORIZATION_HEADER_KEY]
            else:
                is_authenticated = False
        if not is_authenticated:
            raise HTTPUnauthorized(text="Request credentials are invalid!")