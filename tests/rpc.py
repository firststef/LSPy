# -*- coding: utf-8 -*-


import unittest
import os
from subprocess import Popen, PIPE

import lspy


__all__ = ["RPCTestCase"]


class RPCTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(RPCTestCase, self).__init__(*args, **kwargs)

        cwd = os.path.dirname(os.path.abspath(__file__))
        self.p = Popen(["python", "server/simple.py"], stdin=PIPE, stdout=PIPE, cwd=cwd)

        self.rpc = lspy.RPC(stdout=self.p.stdin, stdin=self.p.stdout, block=0.1)

    def __del__(self):
        self.p.terminate()

    def test_request_wo_args(self):
        def cb(err, result):
            self.assertEqual(err, None)
            self.assertEqual(result, 1)
        self.rpc("one", callback=cb)

        self.assertEqual(self.rpc("one"), 1)

    def test_request_w_args(self):
        def cb(err, result):
            self.assertEqual(err, None)
            self.assertEqual(result, 84)
        self.rpc("twice", 42, callback=cb)

        self.assertEqual(self.rpc("twice", name=42), 84)

    def test_request_arguments(self):
        args = (1, None, True)
        kwargs = {"a": {}, "b": [1, 2]}

        def cb(err, n):
            self.assertEqual(err, None)
            self.assertEqual(n, 3)
        self.rpc("arglen", callback=cb, *args)

        self.assertEqual(self.rpc("arglen", **kwargs), 2)

    def test_request_error(self):
        def cb(err, *args):
            self.assertIsInstance(err, lspy.RPCInternalError)
        try:
            self.rpc("one", 27, callback=cb)
        except Exception as e:
            pass

        err = None
        try:
            self.rpc("one", 27)
        except Exception as e:
            err = e
        finally:
            self.assertIsInstance(err, lspy.RPCInternalError)
