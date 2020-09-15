# LSPy

Minimal python LSP-RPC implementation in a single file based on the [JSON-RPC 2.0 specs](http://www.jsonrpc.org/specification).
This repo is ripped from riga/jsonrpyc.

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

print(rpc("greet", args=("John",), block=0.1))
# => "Hi, John!"


#
# async usage
#

def cb(err, res=None):
    if err:
        raise err
    print("callback got: " + res)

rpc("greet", args=("John",), callback=cb)

# cb is called asynchronously which prints
# => "callback got: Hi, John!"
```


## Installation

by simply copying the file into your project.


## Contributing

If you like to contribute to lspy, I'm happy to receive pull requests. Just make sure to add a new test cases and run them via:

```bash
> python -m unittest tests
```
