# -*- coding: utf-8 -*-

import unittest

import lspy


__all__ = ["SpecTestCase"]


class SpecTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(SpecTestCase, self).__init__(*args, **kwargs)

    def test_request(self):
        req = lspy.Spec.request("some_method")
        self.assertEqual(req, 'Content-Length:40\r\n\r\n{"jsonrpc":"2.0","method":"some_method"}')

    def test_request_with_id(self):
        req = lspy.Spec.request("some_method", 18)
        self.assertEqual(req, 'Content-Length:48\r\n\r\n{"jsonrpc":"2.0","method":"some_method","id":18}')

    def test_request_with_strid(self):
        req = lspy.Spec.request("some_method", "myUuid")
        self.assertEqual(req, 'Content-Length:54\r\n\r\n{"jsonrpc":"2.0","method":"some_method","id":"myUuid"}')

    def test_request_with_params(self):
        req = lspy.Spec.request("some_method", params=[1, 2, True])
        self.assertEqual(req, 'Content-Length:62\r\n\r\n{"jsonrpc":"2.0","method":"some_method","params":[1, 2, true]}')

    def test_response(self):
        res = lspy.Spec.response(18, None)
        self.assertEqual(res, 'Content-Length:39\r\n\r\n{"jsonrpc":"2.0","id":18,"result":null}')

    def test_error(self):
        err = lspy.Spec.error(18, -32603)
        self.assertEqual(err, 'Content-Length:76\r\n\r\n{"jsonrpc":"2.0","id":18,"error":{"code":-32603,"message":"Internal error"}}')

    def test_error_with_range(self):
        err = lspy.Spec.error(18, -32001)
        self.assertEqual(err, 'Content-Length:74\r\n\r\n{"jsonrpc":"2.0","id":18,"error":{"code":-32001,"message":"Server error"}}')

    def test_error_with_data(self):
        err = lspy.Spec.error(18, -32603, data=[1, 2, True])
        self.assertEqual(err, 'Content-Length:96\r\n\r\n{"jsonrpc":"2.0","id":18,"error":{"code":-32603,"message":"Internal error","data":[1, 2, true]}}')
