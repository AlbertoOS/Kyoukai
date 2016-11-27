"""
kyoukai.wsgi
~~~~~~~~~~~~

This file name is misleading. Kyoukai does NOT implement WSGI at all, except in the uWSGI wrapper. Instead, this file
adds some utilities which convert from Werkzeug's WSGI magic to our normalized area.
"""
import typing
from io import BytesIO
from urllib.parse import urlsplit

import sys

from werkzeug.wrappers import Response


class SaneWSGIWrapper(object):
    """
    Forces a WSGI object to be in-line.
    """
    def __init__(self):
        self.headers = []
        self.real_body = ""

        self.status = None

    def start_response(self, status, headers: typing.List[tuple], exc_info=None):
        """
        Used as the ``start_response`` callable when interacting with WSGI devices.
        """
        self.status = status
        self.headers = headers

    def unfuck_iterable(self, i: typing.Iterable):
        """
        Unfucks the WSGI iterable into a single body.
        """
        for part in i:
            self.real_body += part.decode()

    def format(self):
        base = "HTTP/1.1 {status}\r\n{headers}\r\n{body}"

        headers_fmt = ""
        # Calculate headers
        for name, val in self.headers:
            headers_fmt += "{}: {}\r\n".format(name, val)

        return base.format(status=self.status, headers=headers_fmt, body=self.real_body).encode()

    def __str__(self):
        """
        Converts this into the string format.
        """
        return self.format()


def to_wsgi_environment(headers: dict, method: str, path: str,
                        http_version: str, body: BytesIO = None) -> dict:
    """
    Produces a new WSGI environment from a set of data that is passed in.

    This will return a dictionary that is directly compatible with Werkzeug's Request wrapper.

    .. code:: python

        d = to_wsgi_environment({"Host": "127.0.0.1"}, "GET", "/", None)
        request = werkzeug.wrappers.Request(d)

    :param headers: The headers of the HTTP request.
    :param method: The HTTP method of this request, e.g GET or POST.
    :param path: The HTTP path to get, in raw form.
        This should NOT be urldecoded, as the path is manually decoded.

    :param http_version: The HTTP version to use.
    :param body: A :class:`BytesIO` representing the body wrapper for this dict, or None if there is no request body.
    :return:
    """
    environ = {}

    # Convert all the headers into HTTP_ form.
    for header, value in headers.items():
        environ["HTTP_{}".format(header.upper())] = value

    # urlsplit the path
    sp_path = urlsplit(path)
    environ["PATH_INFO"] = sp_path.path
    environ["QUERY_STRING"] = sp_path.query

    environ["SERVER_PROTOCOL"] = "HTTP/{}".format(http_version)

    # place the method
    environ["REQUEST_METHOD"] = method

    if body:
        # wsgi.input is the body reader, if the request has a body
        environ["wsgi.input"] = body
        environ["wsgi.input_terminated"] = True

    # these should exist
    environ["wsgi.version"] = (1, 0)
    environ["wsgi.errors"] = sys.stderr
    environ["wsgi.url_scheme"] = "http"

    return environ


def get_formatted_response(response: Response, environment: dict) -> bytes:
    """
    Transform a Werkzeug response into a HTTP response that can be sent back down the wire.

    :param response: The response object to transform.
    :return: Bytes of text that can be sent to a client.
    """
    wrapper = SaneWSGIWrapper()
    iterator = response(environment, wrapper.start_response)
    wrapper.unfuck_iterable(iterator)

    return wrapper.format()
