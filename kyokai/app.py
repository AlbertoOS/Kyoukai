"""
A Kyokai app is an app powered by libuv's event loop, and Kyokai's routing code.

This file contains the main definition for the app.
"""

import asyncio
import traceback
import logging

import uvloop
import yaml

from kyokai.exc import HTTPClientException, HTTPException
from kyokai.request import Request
from kyokai.response import Response
from kyokai.route import Route
from kyokai.kanata import _KanataProtocol

try:
    from kyokai.renderers import MakoRenderer as MakoRenderer
    _has_mako = True
except ImportError:
    _has_mako = False

try:
    from kyokai.renderers import JinjaRenderer as JinjaRenderer
    _has_jinja2 = True
except ImportError:
    _has_jinja2 = False

# Enforce uvloop.
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class Kyokai(object):
    """
    A Kyoukai app.
    """

    def __init__(self, name: str, log_level=logging.INFO, config_file: str="config.yml"):
        """
        Create a new app.

        Parameters:
            name: str
                The name of the app.

            log_level:
                The log level of the logger.

            config_file:
                The path to the config file of the app. Optional.
        """

        self.name = name
        self.loop = asyncio.get_event_loop()
        self.logger = logging.getLogger("Kyokai")
        self.logger.setLevel(log_level)

        self.routes = []
        self.error_handlers = {}

        # Load config.
        try:
            with open(config_file, 'r') as f:
                self.config = yaml.load(f)
        except FileNotFoundError:
            self.config = {}

        # Create a renderer.
        if self.config.get("template_renderer", "mako") == "mako":
            if not _has_mako:
                raise ImportError("Mako is not installed; cannot use for templates.")
            else:
                self._renderer = MakoRenderer.render
        elif self.config.get("template_renderer", "mako") == "jinja2":
            if not _has_jinja2:
                raise ImportError("Jinja2 is not installed; cannot use for templates.")
            else:
                self._renderer = JinjaRenderer.render

    def _kanata_factory(self, *args, **kwargs):
        return _KanataProtocol(self)

    def render(self, filename, **kwargs):
        """
        Render a template using the specified rendering engine.
        """
        return self._renderer(filename, **kwargs)

    async def start(self, ip: str = "127.0.0.1", port: int = 4444):
        """
        Run the app, via async.
        """
        print("Kyokai serving on {}:{}.".format(ip, port))
        self.logger.info("Kyokai serving on {}:{}.".format(ip, port))
        self.server = await self.loop.create_server(self._kanata_factory, ip, port)

    def run(self, ip: str = "127.0.0.1", port: int = 4444):
        """
        Run a Kyokai app.

        This is just a shortcut to run the app from synchronous code.
        """
        self.loop.create_task(self.start(ip, port))
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            return

    def _match_route(self, path, meth):
        """
        Match a route, based on the regular expression of the route.
        """
        for route in self.routes:
            assert isinstance(route, Route), "Routes should be a Route class"
            if route.kyokai_match(path):
                if route.kyokai_method_allowed(meth):
                    return route
                else:
                    return -1

    def _wrap_response(self, response):
        """
        Wrap up a response, if applicable.

        This allows Flask-like `return ""`.
        """
        if isinstance(response, tuple):
            if len(response) == 1:
                # Only body.
                r = Response(200, response[0], {})
            elif len(response) == 2:
                # Body and code.
                r = Response(response[1], response[0], {})
            elif len(response) == 3:
                # Body, code, headers.
                r = Response(response[1], response[0], response[2])
            else:
                # what
                raise HTTPException
        elif isinstance(response, Response):
            r = response
        else:
            r = Response(200, response, {})
        return r

    def route(self, regex, methods: list = None, hard_match: bool = False):
        """
        Create an incoming route for a function.

        Parameters:
            regex:
                The regular expression to match the path to.
                In standard Python `re` forme.

                Group matches are automatically extracted from the regex, and passed as arguments.

            methods:
                The list of allowed methods, e.g ["GET", "POST"].
                You can check the method with `request.method`.

            hard_match:
                Should we match based on equality, rather than regex?

                This prevents index or lower level paths from matching 404s at higher levels.
        """
        if not methods:
            methods = ["GET"]
        # Override hard match if it's a `/` route.
        if regex == "/":
            hard_match = True
        r = Route(regex, methods, hard_match)
        self.routes.append(r)
        return r

    def errorhandler(self, code: int):
        r = Route("", [])
        self.error_handlers[code] = r
        return r

    async def delegate_request(self, protocol, request: Request):
        """
        Delegates a request to be handled automatically.
        """
        self.logger.debug("Matching route `{}`.".format(request.path))
        coro = self._match_route(request.path, request.method)
        if coro == -1:
            # 415 invalid method
            await self._exception_handler(protocol, request, 415)
            return
        elif not coro:
            await self._exception_handler(protocol, request, 404)
            return

        # Invoke the route, wrapped.
        try:
            response = await coro.invoke(request)
        except HTTPException as e:
            self.logger.info("{} {} - {}".format(request.method, request.path, e.errcode))
            await self._exception_handler(protocol, request, e.errcode)
            return
        except Exception as e:
            self.logger.info("{} {} - 500".format(request.method, request.path))
            self.logger.error("Error in route {}".format(coro.__name__))
            traceback.print_exc()
            await self._exception_handler(protocol, request, 500)
            return

        # Wrap the response.
        response = self._wrap_response(response)
        self.logger.info("{} {} - {}".format(request.method, request.path, response.code))
        # Handle the response.
        protocol.handle_resp(response)
        # Check if we should close it.
        if request.headers.get("Connection") != "keep-alive":
            # Close the conenction.
            protocol.close()

    async def _exception_handler(self, protocol, request, code):
        """
        Handles built in HTTP exceptions.
        """
        if code in self.error_handlers:
            route = self.error_handlers[code]
            # Await the invoke.
            try:
                response = await route.invoke(request)
            except Exception:
                self.logger.error("Error in error handler for code {}".format(code))
                traceback.print_exc()
                response = Response(500, "500 Internal Server Error", {})
        else:
            response = Response(code, body=str(code))

        # Handle the response.
        protocol.handle_resp(response)

        # Check if we should close it.
        if request.headers.get("Connection") != "keep-alive":
            # Close the conenction.
            protocol.close()
