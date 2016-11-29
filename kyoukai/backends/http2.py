"""
A HTTP/2 interface to Kyoukai.

This uses https://python-hyper.org/projects/h2/en/stable/asyncio-example.html as a reference and a base. Massive thanks
to the authors of this page.
"""
import asyncio
import importlib
import ssl
import sys
import threading

import logging
import typing
import warnings

import collections
from functools import partial
from io import BytesIO
from urllib.parse import urlsplit

from asphalt.core import Context
from h2.errors import PROTOCOL_ERROR
from werkzeug.wrappers import Request, Response

from kyoukai import Kyoukai
from kyoukai.asphalt import KyoukaiComponent

try:
    from h2.connection import H2Connection
    from h2.events import (
        DataReceived, RequestReceived, WindowUpdated, StreamEnded, StreamReset
    )
except ImportError:
    raise RuntimeError("h2 must be installed for the http2 backend")

# Sentinel value for the request being complete.
REQUEST_FINISHED = object()


def get_header(headers: typing.List[typing.Tuple[str, str]], name: str) -> str:
    """
    Gets a header from the list of headers, or None if it doesn't exist.
    """
    for header, value in headers:
        if header == name:
            return value


# WSGI helpers.
def create_wsgi_environment(r: 'H2State'):
    """
    Creates a new WSGI environment from the RequestData provided.
    """
    # HTTP/2 special header path
    path = get_header(r.headers, ':path')

    # urlsplit the path
    sp_path = urlsplit(path)

    # HTTP/2 special header server name
    server_name = get_header(r.headers, ':authority')

    # try and split the port away
    try:
        server_name, port = server_name.split(':', 1)
    except ValueError as e:
        port = "8443"

    # HTTP/2 special header method
    method = get_header(r.headers, ":method")

    environ = {
        # Basic items
        "PATH_INFO": sp_path.path,
        "QUERY_STRING": sp_path.query,
        "SERVER_PROTOCOL": "HTTP/2",
        "REQUEST_METHOD": method,
        # WSGI protocol things
        "wsgi.version": (1, 0),
        "wsgi.errors": sys.stderr,
        "wsgi.url_scheme": get_header(r.headers, ":scheme"),
        "wsgi.input": r,
        "wsgi.async": True,
        "wsgi.multithread": True,  # technically false sometimes, but oh well
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "SERVER_NAME": server_name,
        "SERVER_PORT": port
    }

    # Add the headers.
    for header, value in r.headers:
        if not header.startswith(":"):
            environ["HTTP_{}".format(header.replace("-", "_").upper())] = value

    return environ


class H2State:
    """
    A temporary class that is used to store request data for a HTTP/2 connection.

    This is also passed to the Werkzeug request to emit data.
    """

    def __init__(self, headers: list, stream_id, protocol: 'H2KyoukaiProtocol'):
        self.stream_id = stream_id
        self._protocol = protocol

        self.headers = headers

        # The queue of data.
        # This is a deque as reading from here is implicitly async.
        self.body = asyncio.Queue()

        # The data to emit.
        self._emit_headers = None
        self._emit_status = None

    def insert_data(self, data: bytes):
        """
        Writes data from the stream into the body.
        """
        self.body.put_nowait(data)

    async def read_async(self, to_end=True):
        """
        There's no good way to do this - WSGI isn't async, after all.

        However, you can use `read_async` on the Werkzeug request (which we subclass) to wait until the request has
        finished streaming.

        :param to_end: If ``to_end`` is specified, then read until the end of the request.
            Otherwise, it will read one data chunk.
        """
        data = b""
        if to_end:
            while True:
                d = await self.body.get()
                if d == REQUEST_FINISHED:
                    break
                data += d
        else:
            d = await self.body.get()
            if not d == REQUEST_FINISHED:
                data += d

        return data

    def read(self, size: int = -1) -> bytes:
        """
        Reads data from the request until it's all done.

        :param size: The maximum amount of data to receive.
        """
        # Thanks h2 docs page for the chunking inspiration
        # However, we're lazy and just shove it back on the front of the queue when we're done
        curr_data = b""
        while size < 0 or len(curr_data) < size:
            # size < 0 means read until we can't
            # b''.join is probably faster.
            try:
                curr_data += self.body.get_nowait()
            except asyncio.QueueEmpty:
                # no more data left to pop
                break

        # Get rid of any excess data.
        d = curr_data[:size]
        if len(curr_data) != len(d):
            # we have data left to read, so place it back on the left of the deque.
            self.body._queue.appendleft(curr_data[size:])

        return d

    def get_chunk(self) -> bytes:
        """
        Gets a chunk of data from the queue.
        """
        try:
            d = self.body.get_nowait()
            if d == REQUEST_FINISHED:
                return b""
        except asyncio.QueueEmpty:
            return b""

        return d

    def start_response(self, status: str, headers: typing.List[typing.Tuple[str, str]], exc_info=None) -> \
            typing.Callable:
        """
        The ``start_response`` callable that is plugged into a Werkzeug response.
        """
        self._emit_status = status.split(" ")[0]
        self._emit_headers = headers

        # fake "write" callable
        return (lambda data: None)

    def get_response_headers(self):
        """
        Called by the protocol once the Response is writable to submit the request to the HTTP/2 state machine.
        """
        headers = [(":status", self._emit_status)]
        headers.extend(self._emit_headers)

        # Send the response headers.
        return headers

    def __iter__(self):
        return self

    def __next__(self):
        return self.get_chunk()


class H2KyoukaiComponent(KyoukaiComponent):
    """
    A component subclass that creates H2KyoukaiProtocol instances.
    """
    def __init__(self, app, ssl_keyfile: str, ssl_certfile: str,
                 *, ip: str="127.0.0.1", port: int=4444):
        """
        Creates a new HTTP/2 SSL-based context.

        This will use the HTTP/2 protocol, disabling HTTP/1.1 support for this port. It is possible to run the

        :param app:
        :param ssl_keyfile:
        :param ssl_certfile:
        :param ip:
        :param port:
        """
        super().__init__(app, ip, port)

    def get_protocol(self, ctx: Context, serv_info: tuple):
        return H2KyoukaiProtocol(self, ctx)

    async def start(self, ctx: Context):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile="server.crt", keyfile="server.key")
        ssl_context.set_alpn_protocols(["h2"])

        protocol = partial(self.get_protocol, ctx, (self._server_name, self.port))
        self.app.finalize()
        self.server = await asyncio.get_event_loop().create_server(protocol, self.ip, self.port, ssl=ssl_context)
        self.logger.info("Kyoukai H2 serving on {}:{}".format(self.ip, self.port))


class H2KyoukaiProtocol(asyncio.Protocol):
    """
    The base protocol for Kyoukai, using H2.
    """

    def __init__(self, component: 'H2Component', parent_context: Context):
        # The current component used by this connection.
        self.component = component

        self.parent_context = parent_context

        # The HTTP/2 state machine.
        self.conn = H2Connection(client_side=False)

        # The current transport for this connection.
        self.transport = None  # type: asyncio.WriteTransport

        # The current streams for this request.
        # This is a dictionary of stream_id -> data.
        self.streams = {}  # type: typing.Dict[H2State]

        # The current stream data queue.
        # This is a Queue of two-item tuples: (stream_data, stream_id).
        # These are plucked off of a Werkzeug request as they come in from Kyoukai.
        self.stream_data = collections.defaultdict(lambda *args: asyncio.Queue())

        # The current logger.
        self.logger = logging.getLogger("Kyoukai")

        # Client data.
        self.ip, self.client_port = None, None

        # If we're waiting to send data due to the window being exceeded.
        self._locked = collections.defaultdict(lambda *args: asyncio.Event())

        # The dictionary of stream tasks.
        self.stream_tasks = {}

    def raw_write(self, data: bytes):
        """
        Writes to the underlying transport.
        """
        # TODO: Handle connection reset
        return self.transport.write(data)

    def connection_made(self, transport: asyncio.WriteTransport):
        """
        Called when a connection is made.

        :param transport: The transport made by the connection.
        """
        # Set our own attributes, and update the HTTP/2 state machine.
        self.transport = transport
        try:
            self.ip, self.client_port = self.transport.get_extra_info("peername")
            self.logger.debug("Connection received from {}:{}".format(self.ip, self.client_port))
        except ValueError:
            # Sometimes socket.socket.getpeername() isn't available, so it tried to unpack a None.
            # Or, it returns None (wtf?)
            # So just provide some fake values.
            warnings.warn("getpeername() returned None, cannot provide transport information.")
            self.ip, self.client_port = None, None

        # Send the HTTP2 preamble.
        self.conn.initiate_connection()
        self.raw_write(self.conn.data_to_send())

    def data_received(self, data: bytes):
        """
        Called when data is received from the underlying socket.
        """
        # Get a list of events by writing to the state machine.
        events = self.conn.receive_data(data)
        # Find any data we need to send to the client first.
        self.transport.write(self.conn.data_to_send())

        # Then, switch upon the events we've received from the HTTP/2 client.
        for event in events:
            self.logger.debug("Received HTTP/2 event {.__class__.__name__}".format(event))
            # RequestReceived - headers have been received.
            # Handle it with ``request_received``.
            if isinstance(event, RequestReceived):
                self.request_received(event)
            # HTTP/2 body.
            # This will read data into the current stream.
            elif isinstance(event, DataReceived):
                self.receive_data(event)
            # The stream has ended.
            # This will invoke Kyoukai to handle the stream.
            elif isinstance(event, StreamEnded):
                self.stream_complete(event)
            elif isinstance(event, WindowUpdated):
                self.window_opened(event)

    def _processing_done(self, environ: dict, stream_id):
        """
        Callback for when processing is done on a request.
        """

        def _inner(fut: asyncio.Future):
            result = fut.result()  # type: Response

            # Get the H2State for this request.
            state = self.streams[stream_id]  # type: H2State

            # Get the app iterator.
            it = result(environ, state.start_response)
            headers = state.get_response_headers()

            # Send the headers.
            self.conn.send_headers(stream_id, headers, end_stream=False)

            # Place all the data from the app iterator on the queue.
            for i in it:
                self.stream_data[stream_id].put_nowait(i)

            # Add the sentinel value.
            self.stream_data[stream_id].put_nowait(REQUEST_FINISHED)

            # This will all be done with the sending task.

        return _inner

    async def sending_loop(self, stream_id):
        """
        This loop continues sending data to the client as it comes off of the queue.
        """
        while True:
            self._locked[stream_id].clear()
            data = await self.stream_data[stream_id].get()

            if data == REQUEST_FINISHED:
                # The request is finished - terminate the stream.
                self.conn.end_stream(stream_id)
                self.raw_write(self.conn.data_to_send())
                # This stream is dead, now.
                return

            # Buffer data - don't exceed the control flow window size.
            window_size = self.conn.local_flow_control_window(stream_id)
            chunk_size = min(window_size, len(data))
            data_to_send = data[:chunk_size]
            data_to_buffer = data[chunk_size:]

            if data_to_send:
                # Split it into chunks and send it out.
                max_size = self.conn.max_outbound_frame_size
                chunks = (
                    data_to_send[x:x + max_size]
                    for x in range(0, len(data_to_send), max_size)
                )
                for chunk in chunks:
                    self.conn.send_data(stream_id, chunk)
                self.raw_write(self.conn.data_to_send())

            if data_to_buffer:
                # Don't exceed flow window, set this data to be sent later.
                # Put it back on the left of the deque, then wait for our event to be set.
                self.stream_data[stream_id]._queue.appendleft(data)
                await self._locked[stream_id].wait()
                self._locked[stream_id].clear()
                continue

    # H2 callbacks
    def request_received(self, event: RequestReceived):
        """
        Called when a request has been received.
        """
        # Create the RequestData that stores this event.
        r = H2State(event.headers, event.stream_id, self)
        self.streams[event.stream_id] = r

        # Create the task that runs the app.
        app = self.component.app  # type: Kyoukai
        # Create the fake WSGI environment.
        env = create_wsgi_environment(r)
        request = Request(environ=env)

        loop = asyncio.get_event_loop()
        t = loop.create_task(app.process_request(request, self.parent_context))  # type: asyncio.Task
        self.stream_tasks[event.stream_id] = loop.create_task(self.sending_loop(event.stream_id))

        t.add_done_callback(self._processing_done(env, event.stream_id))

    def window_opened(self, event: WindowUpdated):
        """
        Called when a control flow window has opened again.
        """
        if event.stream_id:
            # Set the lock on the event, which will cause the sending_loop to wake up.
            self._locked[event.stream_id].set()
        else:
            # Unlock all events.
            for ev in self._locked.keys():
                ev.set()

    def receive_data(self, event: DataReceived):
        """
        Called when a request has data that has been received.
        """
        # Write into the RequestData for this event.
        try:
            req = self.streams[event.stream_id]
        except KeyError:
            # Reset the stream, because the client is stupid.
            self.conn.reset_stream(event.stream_id, PROTOCOL_ERROR)
        else:
            req.insert_data(event.data)

    def stream_complete(self, event: StreamEnded):
        """
        Called when a stream is complete.

        This will invoke Kyoukai, which will handle the request.
        """
        try:
            req = self.streams[event.stream_id]
        except KeyError:
            # shoo
            self.conn.reset_stream(event.stream_id, PROTOCOL_ERROR)
            return
        else:
            req.insert_data(REQUEST_FINISHED)
