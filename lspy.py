# coding: utf-8

"""
Minimal python RPC implementation in a single file based on the JSON-RPC 2.0 specs from
http://www.jsonrpc.org/specification and LSP specs from https://microsoft.github.io/language-server-protocol/specification.
"""

__author__ = "firststef"
__email__ = ""
__copyright__ = ""
__credits__ = ["Marcel Rieger", "sventaro"]
__contact__ = ""
__license__ = "BSD-3-Clause"
__status__ = "Development"
__version__ = "0.0.1"
__all__ = ["RPC"]

import sys
import json
import io
import time
import threading
import base64


class Spec(object):
    """
    This class wraps methods that create LSP compatible string representations of
    requests, responses, and errors. All methods are class members, so you might never want to
    create an instance of this class, but rahter use the methods directly:

    .. code-block:: python

       Spec.request("my_method", 18)
       # => 'Content-Length: 51\r\n\r\n{"jsonrpc": "2.0", "method": "my_method", "id": 18}'

       Spec.response(18, "some_result")
       # => 'Content-Length: 53\r\n\r\n{"jsonrpc": "2.0", "id": 18, "result": "some_result"}'

       Spec.error(18, -32603)
       # => 'Content-Length: 84\r\n\r\n{"jsonrpc": "2.0", "id": 18, "error": {"code": -32603, "message": "Internal error"}}'
    """

    @classmethod
    def check_id(cls, id, allow_empty=False):
        """
        Value check for *id* entries. When *allow_empty* is *True*, *id* is allowed to be *None*.
        Raises a *TypeError* when *id* is not an interger and no string.
        """
        if allow_empty and id is None:
            return
        if not isinstance(id, (int, str)):
            raise TypeError("id must be an integer or string, got %s (%s)" % (id, type(id)))

    @classmethod
    def check_method(cls, method):
        """
        Value check for *method* entries. Raises a *TypeError* when *method* is not a string.
        """
        if not isinstance(method, str):
            raise TypeError("method must be a string, got %s (%s)" % (method, type(method)))

    @classmethod
    def check_code(cls, code):
        """
        Value check for *code* entries. Raises a *TypeError* when *code* is not an interger, or a
        *KeyError* when there is no :py:class:`RPCError` derivative registered for that *code*.
        """
        if not isinstance(code, int):
            raise TypeError("code must be an integer, got %s (%s)" % (id, type(id)))
        elif get_error(code) is None:
            raise KeyError("unknown code, got %s (%s)" % (code, type(code)))

    @classmethod
    def request(cls, method, id=None, params=None):
        """
        Creates the string representation of a request that calls *method* with optional *params*.
        When *id* is *None*, the request is considered a notification.
        """
        try:
            cls.check_method(method)
            cls.check_id(id, allow_empty=True)
        except Exception as e:
            raise RPCInvalidRequest(str(e))

        req = "{\"jsonrpc\":\"2.0\",\"method\":\"%s\"" % method

        if id is not None:
            if isinstance(id, str):
                id = '"%s"' % id
            req += ",\"id\":%s" % id

        if params is not None:
            try:
                req += ",\"params\":%s" % json.dumps(params, cls=JsonBinaryEncoder)
            except Exception as e:
                raise RPCParseError(str(e))

        req += "}"

        return ("Content-Length:%d\r\n\r\n" % len(req)) + req

    @classmethod
    def response(cls, id, result):
        """
        Creates the string representation of a respons that was triggered by a request with *id*.
        *result* is required.
        """
        try:
            cls.check_id(id)
        except Exception as e:
            raise RPCInvalidRequest(str(e))

        if isinstance(id, str):
            id = '"%s"' % id

        try:
            res = "{\"jsonrpc\":\"2.0\",\"id\":%s,\"result\":%s}" % (id, json.dumps(result, cls=JsonBinaryEncoder))
        except Exception as e:
            raise RPCParseError(str(e))

        return ("Content-Length:%d\r\n\r\n" % len(res)) + res

    @classmethod
    def error(cls, id, code, data=None):
        """
        Creates the string representation of an error that occured while processing a request with
        *id*. *code* must lead to a registered :py:class:`RPCError`. *data* might contain
        additional, detailed error information.
        """
        try:
            cls.check_id(id)
            cls.check_code(code)
        except Exception as e:
            raise RPCInvalidRequest(str(e))

        if isinstance(id, str):
            id = '"%s"' % id

        message = get_error(code).title

        err = "{\"code\":%d,\"message\":\"%s\"" % (code, message)

        if data is not None:
            try:
                err += ",\"data\":%s}" % json.dumps(data, cls=JsonBinaryEncoder)
            except Exception as e:
                raise RPCParseError(str(e))
        else:
            err += "}"

        err = "{\"jsonrpc\":\"2.0\",\"id\":%s,\"error\":%s}" % (id, err)

        return ("Content-Length:%d\r\n\r\n" % len(err)) + err


class RPC(object):
    """
    The main class of *lspy*. Instances of this class basically wrap an input stream *stdin* and
    an output stream *stdout* in order to communicate with other *services*. A service is not even
    forced to be written in Python as long as it strictly implements the JSON-RPC 2.0 specs. RPC
    instances may wrap a *target* object. Incomming requests will be routed to methods of this
    object whose result might be sent back as a response. Example implementation:

    *server.py*

    .. code-block:: python

       import lspy

       class MyTarget(object):

           def greet(self, name):
               return "Hi, %s!" % name

       jsonrpc.RPC(MyTarget())

    *client.py*

    .. code-block:: python

        import lspy
        from subprocess import Popen, PIPE

        p = Popen(["python", "server.py"], stdin=PIPE, stdout=PIPE)
        rpc = lspy.RPC(stdout=p.stdin, stdin=p.stdout)

        # non-blocking remote procedure call with callback, js-like signature
        def cb(err, res=None):
            if err:
                throw err
            print("callback got: " + res)

        rpc("greet", args=("John",), callback=cb)

        # cb is called asynchronously which prints
        # => "callback got: Hi, John!"

        # blocking remote procedure call with 0.1s polling
        print(rpc("greet", args=("John",), block=0.1))
        # => "Hi, John!"


    .. py:attribute:: target

       The wrapped target object. Might be *None* when no object is wrapped, e.g. for the *client*
       RPC instance.

    .. py:attribute:: stdin

       The input stream, re-opened with ``"rb"``.

    .. py:attribute:: stdout

       The output stream, re-opened with ``"wb"``.

    .. py:attribute:: watch

       The :py:class:`Watchdog` instance that watches *stdin*.
    """

    EMPTY_RESULT = object()

    def __init__(self, target=None, stdin=None, stdout=None, block=0.1, initialize=True, **kwargs):
        super(RPC, self).__init__()

        self.target = target
        self.block = block

        stdin = sys.stdin if stdin is None else stdin
        stdout = sys.stdout if stdout is None else stdout

        if initialize:
            self.stdin = io.open(stdin.fileno(), "rb")
            self.stdout = io.open(stdout.fileno(), "wb")
        else:
            self.stdin = stdin
            self.stdout = stdout

        self._i = -1
        self._callbacks = {}
        self._results = {}

        kwargs.setdefault("daemon", target is None)
        self.watchdog = Watchdog(self, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)

    def call(self, method, *args, **kwargs):
        """
        Performs an actual remote procedure call by writing a request representation (a string) to
        the output stream. The remote RPC instance uses *method* to route to the actual method to
        call with *args* and *kwargs*. When *callback* is set, it will be called with the result of
        the remote call. When *block* is larger than *0*, the calling thread is blocked until the
        result is received. In this case, *block* will be the poll interval. This mechanism emulates
        synchronuous return value behavior. When both, *callback* is *None* and *block* is *0* or
        less, the request is considered a notification and the remote RPC instance will not send a
        response.
        """
        if kwargs is None:
            kwargs = {}

        if args is None:
            args = ()

        callback = kwargs.pop("callback", None)
        if callback is not None or self.block > 0:
            self._i += 1
            id = self._i
        else:
            id = None

        if callback is not None:
            self._callbacks[id] = callback

        if self.block > 0:
            self._results[id] = self.EMPTY_RESULT

        if args != ():
            params = list(args)
        elif kwargs != {}:
            params = kwargs
        else:
            params = None
        req = Spec.request(method, id=id, params=params)
        self._write(req)

        if self.block > 0:
            while True:
                if self._results[id] != self.EMPTY_RESULT:
                    result = self._results[id]
                    del self._results[id]
                    if isinstance(result, Exception):
                        raise Exception('ERROR when in ' + method + ' : ' + str(result))
                    else:
                        return result
                time.sleep(self.block)

    def _handle(self, obj):
        """
        Handles an incoming object and dispatches the parsed object to the request, response, or
        error handler.
        """

        # dispatch to the correct handler
        if "method" in obj:
            # request
            self._handle_request(obj)
        elif "error" not in obj:
            # response
            self._handle_response(obj)
        else:
            # error
            self._handle_error(obj)

    def _handle_request(self, req):
        """
        Handles an incoming request *req*. When it contains an id, a response or error is sent
        back.
        """
        try:
            method = self._route(req["method"])
            if "params" in req:
                if isinstance(req["params"], list):
                    result = method(*req["params"])
                else:
                    result = method(**req["params"])
            else:
                result = method()
            if "id" in req:
                res = Spec.response(req["id"], result)
                self._write(res)
        except Exception as e:
            if "id" in req:
                if isinstance(e, RPCError):
                    err = Spec.error(req["id"], e.code, e.data)
                else:
                    err = Spec.error(req["id"], -32603, str(e))
                self._write(err)

    def _handle_response(self, res):
        """
        Handles an incomming successful response *res*. Blocking calls are resolved and registered
        callbacks are invoked with the first error argument being set to *None*.
        """
        if res["id"] in self._results:
            self._results[res["id"]] = res["result"]
        if res["id"] in self._callbacks:
            callback = self._callbacks[res["id"]]
            del self._callbacks[res["id"]]
            callback(None, res["result"])

    def _handle_error(self, res):
        """
        Handles an incomming failed response *res*. Blocking calls throw an exception and
        registered callbacks are invoked with an exception and the second result argument set to
        *None*.
        """
        err = res["error"]
        error = get_error(err["code"])(err.get("data", err["message"]))

        if res["id"] in self._results:
            self._results[res["id"]] = error
        if res["id"] in self._callbacks:
            callback = self._callbacks[res["id"]]
            del self._callbacks[res["id"]]
            callback(error, None)

    def _route(self, method):
        """
        Returnes the actual method of the wrapped target object to be called when *method* is
        requested. Example:

        .. code-block:: python
           MyClassB(object):
               def foo(self):
                   return 123

           MyClassA(object):
               def __init__(self):
                   self.b = MyClassB()
               def bar(self):
                   return "test"

           rpc = RPC(MyClassA())

           rpc._route("bar")
           # => <bound method MyClassA.bar ...>

           rpc._route("b.foo")
           # => <bound method MyClassB.foo ...>
        """
        obj = self.target
        for part in method.split("."):
            if not hasattr(obj, part):
                break
            obj = getattr(obj, part)
        else:
            return obj
        raise RPCMethodNotFound(data=method)

    def _write(self, s):
        """
        Writes a string *s* to the output stream.
        """
        self.stdout.write(bytearray(s, "utf-8"))
        self.stdout.flush()


class MessageBuffer:

    def __init__(self):
        self.m_headers = {}
        self.m_body = ""
        self.m_raw_message = ""
        self.m_is_header_done = False
        self.CMD_LINE_HEADER_TERMINATOR = "\r\n"

    def _try_parse_header(self):
        eol_pos = self.m_raw_message.find(self.CMD_LINE_HEADER_TERMINATOR)
        if eol_pos != -1:
            header_string = self.m_raw_message[:eol_pos]
            delim_pos = header_string.find(':')
            if delim_pos != -1:
                header_name = header_string[0: delim_pos]
                header_value = header_string[delim_pos + 1:]
                return header_name, header_value
        return "", ""

    def handle_char(self, c: chr):
        self.m_raw_message += c

        new_header = self._try_parse_header()
        # Check whether we were actually able to parse a header.
        # If so, add it to our known headers.
        # We'll also reset our string then.
        if new_header[0] != "":
            self.m_headers[new_header[0]] = new_header[1]
            self.m_raw_message = ""

        # A sole \r\n is the separator between the header block and the body block
        # but we don't need it.
        if self.m_raw_message == self.CMD_LINE_HEADER_TERMINATOR:
            self.m_raw_message = ""
            self.m_is_header_done = True

        if self.m_is_header_done:
            # Now that we know that we're in the body, we just have to count until
            # we reach the length of the body as provided in the Content-Length
            # header.
            content_length = int(self.m_headers["Content-Length"])
            if len(self.m_raw_message) == content_length:
                self.m_body = json.loads(self.m_raw_message, cls=JsonBinaryDecoder)
                
    def handle_string(self, s: str):
        self.m_raw_message += s

        new_header = self._try_parse_header()
        # Check whether we were actually able to parse a header.
        # If so, add it to our known headers.
        # We'll also reset our string then.
        if new_header[0] != "":
            self.m_headers[new_header[0]] = new_header[1]
            self.m_raw_message = ""

        # A sole \r\n is the separator between the header block and the body block
        # but we don't need it.
        if self.m_raw_message == self.CMD_LINE_HEADER_TERMINATOR:
            self.m_raw_message = ""
            self.m_is_header_done = True

        if self.m_is_header_done:
            # Now that we know that we're in the body, we just have to count until
            # we reach the length of the body as provided in the Content-Length
            # header.
            content_length = int(self.m_headers["Content-Length"])
            if len(self.m_raw_message) == content_length:
                self.m_body = json.loads(self.m_raw_message, cls=JsonBinaryDecoder)

    def clear(self):
        self.m_headers = {}
        self.m_raw_message = ""
        self.m_is_header_done = False

    def get_content_length(self):
        return int(self.m_headers["Content-Length"]) if self.m_is_header_done else 0

    def message_completed(self):
        return self.m_is_header_done and self.m_body != ""

    def is_m_header_done(self):
        return self.m_is_header_done

    def get_body(self):
        return self.m_body

    def get_headers(self):
        return self.m_headers

    def get_current_buffer(self):
        return self.m_raw_message


class Watchdog(threading.Thread):
    """
    This class represents a thread that watches the input stream for incomming content.

    .. py:attribute:: rpc

       The :py:class:`RPC` instance.

    .. py:attribute:: name

       The thread's name.

    .. py:attribute:: interval

       The polling interval of the run loop.

    .. py:attribute:: daemon

       The thread's daemon flag.
    """

    def __init__(self, rpc, name="watchdog", interval=0.1, daemon=False, start=True):
        super(Watchdog, self).__init__()

        self.rpc = rpc
        self.name = name
        self.interval = interval
        self.daemon = daemon

        self._stop = threading.Event()

        self._message_buffer = MessageBuffer()

        if start:
            self.start()

    def start(self):
        """
        Starts with thread's activity.
        """
        super(Watchdog, self).start()

    def stop(self):
        """
        Stops with thread's activity.
        """
        self._stop.set()

    def run(self):
        try:
            self._run()
        except:
            self.stop()

    def _run(self):
        stream = self.rpc.stdin

        if stream.isatty():
            last_pos = 0
            while not self._stop.is_set():
                cur_pos = stream.tell()
                if cur_pos != last_pos:
                    stream.seek(last_pos)
                    c = stream.read(1).decode('utf-8')
                    last_pos = stream.tell()
                    stream.seek(cur_pos)
                    self._message_buffer.handle_char(c)
                    if self._message_buffer.is_m_header_done():
                        sz = self._message_buffer.get_content_length()
                        if sz == 0:
                            continue
                        stri = stream.read(sz).decode('utf-8')
                        self._message_buffer.handle_string(stri)
                        self.rpc._handle(self._message_buffer.get_body())
                        self._message_buffer.clear()
                else:
                    self._stop.wait(self.interval)
        else:
            while not self._stop.is_set():
                c = stream.read(1).decode('utf-8')
                self._message_buffer.handle_char(c)
                if self._message_buffer.is_m_header_done():
                    sz = self._message_buffer.get_content_length()
                    if sz == 0:
                        continue
                    stri = stream.read(sz).decode('utf-8')
                    self._message_buffer.handle_string(stri)
                    self.rpc._handle(self._message_buffer.get_body())
                    self._message_buffer.clear()
                else:
                    self._stop.wait(self.interval)


class RPCError(Exception):
    """
    Base class for RPC errors.

    .. py:attribute:: message

       The message of this error, i.e., ``"<title> (<code>)[, data: <data>]"``.

    .. py:attribute:: data

       Additional data of this error. Setting the data attribute will also change the message
       attribute.
    """

    def __init__(self, data=None):
        message = "%s (%s)" % (self.title, self.code)
        if data is not None:
            message += ", data: " + str(data)
        self.message = message

        super(RPCError, self).__init__(message)

        self.data = data

    def __str__(self):
        return self.message


error_map_distinct = {}
error_map_range = {}


def is_range(code):
    return (
            isinstance(code, tuple) and
            len(code) == 2 and
            all(isinstance(i, int) for i in code) and
            code[0] < code[1]
    )


def register_error(cls):
    """
    Decorator that registers a new RPC error derived from :py:class:`RPCError`. The purpose of
    error registration is to have a mapping of error codes/code ranges to error classes for faster
    lookups during error creation.

    .. code-block:: python

       @register_error
       class MyCustomRPCError(RPCError):
           code = ...
           title = "My custom error"
    """
    # it would be much cleaner to add a meta class to RPCError as a registry for codes
    # but in cpython exceptions aren't types, so simply provide a registry mechanism here
    if not issubclass(cls, RPCError):
        raise TypeError("'%s' is not a subclass of RPCError" % cls)

    code = cls.code

    if isinstance(code, int):
        error_map = error_map_distinct
    elif is_range(code):
        error_map = error_map_range
    else:
        raise ValueError("invalid RPC error code " + str(code))

    if code in error_map:
        raise AttributeError("duplicate RPC error code " + str(code))

    error_map[code] = cls

    return cls


def get_error(code):
    """
    Returns the RPC error class that was previously registered to *code*. *None* is returned when no
    class could be found.
    """
    if code in error_map_distinct:
        return error_map_distinct[code]

    for (lower, upper), cls in error_map_range.items():
        if lower <= code <= upper:
            return cls

    return None


@register_error
class RPCParseError(RPCError):
    code = -32700
    title = "Parse error"


@register_error
class RPCInvalidRequest(RPCError):
    code = -32600
    title = "Invalid Request"


@register_error
class RPCMethodNotFound(RPCError):
    code = -32601
    title = "Method not found"


@register_error
class RPCInvalidParams(RPCError):
    code = -32602
    title = "Invalid params"


@register_error
class RPCInternalError(RPCError):
    code = -32603
    title = "Internal error"


@register_error
class RPCServerError(RPCError):
    code = (-32099, -32000)
    title = "Server error"


class JsonBinaryEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return 'b64:' + base64.b64encode(obj).decode('utf-8')
        return json.JSONEncoder.default(self, obj)


class JsonBinaryDecoder(json.JSONDecoder):
    def decode(self, s, _w=json.decoder.WHITESPACE.match):
        obj = json.JSONDecoder.decode(self, s)
        return self.replace_b64_in_obj(obj)

    def replace_b64_in_obj(self, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, dict):
                    obj[k] = self.replace_b64_in_obj(v)
                if isinstance(v, str) and v.startswith('b64:'):
                    obj[k] = self.replace_b64_str(v)
                if isinstance(v, list):
                    obj[k] = [(self.replace_b64_str(a) if isinstance(a, str) else a) for a in v]
        elif isinstance(obj, list):
            obj = [self.replace_b64_str(a) if isinstance(a, str) else a for a in obj]
        return obj

    def replace_b64_str(self, s):
        return base64.b64decode(s[len('b64:'):])

