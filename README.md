# LSPy

Minimal python LSP-RPC implementation in a single file based on the [JSON-RPC 2.0 specs](http://www.jsonrpc.org/specification).
This repo is ripped from [riga/lspy](https://github.com/riga/lspy). Note that this was more of a test for me, the same protocol I added here for LSP in c++ takes milliseconds to respond but in python it takes a few seconds so - not good. This is because python is very slow at reading one character at a time from stdin (for the header part, the body is read by reading the size from the header).

I only needed to add a header on top of json-rpc:
```
Content-Length: ...\r\n
\r\n
{
	"jsonrpc": "2.0",
	"id": 1,
	"method": "textDocument/didOpen",
	"params": {
		...
	}
}
```

## Usage

##### ``server.py``

```python
import lspy

class MyTarget(object):

    def greet(self, name):
        return "Hi, %s!" % name

lspy.RPC(MyTarget())
```


##### ``client.py``

```python
import lspy
from subprocess import Popen, PIPE

p = Popen(["python", "server.py"], stdin=PIPE, stdout=PIPE)
rpc = lspy.RPC(stdout=p.stdin, stdin=p.stdout)

#
# sync usage
#

print(rpc("greet", "John"))
# => "Hi, John!"


#
# async usage
#

def cb(err, res=None):
    if err:
        raise err
    print("callback got: " + res)

rpc("greet", callback=cb, "John")

# cb is called asynchronously which prints
# => "callback got: Hi, John!"
```

According to LSP Specifications, you can either pass parameters for the methods as a list or as an object:
```python
rpc("greet", callback=cb, "John")
rpc("greet", callback=cb, name="John")
```

## Installation

by simply copying the file into your project.


## Contributing

If you like to contribute to lspy, I'm happy to receive pull requests. Just make sure to add a new test cases and run them via:

```bash
> python -m unittest tests
```
