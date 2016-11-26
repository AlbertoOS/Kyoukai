"""
A Werkzeug-based routing engine for Kyoukai.
"""
import typing

from asphalt.core import Context
from kyoukai.context import HTTPRequestContext
from kyoukai.response import Response
from kyoukai.converters import convert_args
from kyoukai.routing.base import ABCRouter, ABCRoute
from kyoukai.util import wrap_response

from werkzeug.routing import Rule


class WerkzeugRouteRule(Rule):
    """
    """

    def __init__(self, *a, kyk_route=None, **kw):
        super().__init__(*a, **kw)
        self.kyk_route = kyk_route

    def get_empty_kwargs(self):
        kwargs = super().get_empty_kwargs()
        kwargs["kyk_route"] = self.kyk_route
        return kwargs


class WerkzeugRoute(ABCRoute):
    """
    Defines a Werkzeug-based route.
    """

    def __init__(self, blueprint,
                 matcher: str, methods: list,
                 bound: bool = False,
                 run_hooks: bool = True):

        super().__init__(blueprint, matcher, methods, bound, run_hooks)
        self.matcher = WerkzeugRouteRule(matcher, methods=methods, kyk_route=self)

    def __repr__(self):
        return "<WerkzeugRoute '{}'>".format(self.bp.prefix + self._match_str)

    async def invoke(self, ctx: HTTPRequestContext, args: typing.Iterable = None,
                     exception: Exception = None):
        if self._should_run_hooks:
            # Run pre-request hooks.
            hooks = self.bp.gather_hooks("pre")
            if hooks:
                for hook in hooks:
                    # Await the hook.
                    ctx = await hook(ctx)
                    if not isinstance(ctx, Context):
                        # idc about the subtype, as long as it's a context.
                        raise TypeError("Hook {} returned non-context".format(hook.__name__))

        # Invoke the coroutine.
        # Construct the params.
        params = []
        if self._bound:
            params.append(self.self)

        params.append(ctx)

        if exception:
            # This is an error handler, so add the exception.
            params.append(exception)

        # Add args to params.
        if args:
            params += list(args)

        # Convert the arguments.
        if self.should_convert:
            args = await convert_args(ctx, self._wrapped_coro, *params, bound=self._bound)
        else:
            # Don't bother with converting.
            args = params

        # Call the coroutine.

        result = await self._wrapped_coro(*args)
        # Wrap the result.
        result = wrap_response(result, response_cls=ctx.app.response_cls)

        if self._should_run_hooks:
            hooks = self.bp.gather_hooks("post")
            if hooks:
                for hook in hooks:
                    result = await hook(ctx, result)
                    if not isinstance(result, Response):
                        raise TypeError("Hook {} returned non-response".format(hook.__name__))
                    result = wrap_response(result)

        # Set the request object.
        result.request = ctx.request

        return result


class WerkzeugRouter(ABCRouter):
    """
    A Werkzeug-based router.
    """

    def match(self, path: str, method: str):
        root_bp = self.app.root
        map = root_bp.gather_routes()  # XXX: store map somewhere!
        urls = map.bind("example.com", "/")  # domain doesn't matter for now
        match = urls.match(path, method, return_rule=True)
        return (match[0].kyk_route, match[1].values())
