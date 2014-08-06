#-*- coding: utf-8 -*-
from alot.db.utils import decode_header


class TestDecodeHeader(object):
    def test_one(self):
        input = "someone@example.com"
        output = decode_header(input)
        expected_output = u"someone@example.com"
        assert output == expected_output

    def test_one_with_name(self):
        input = "Some One <someone@example.com>"
        output = decode_header(input)
        expected_output = u"Some One <someone@example.com>"
        assert output == expected_output

    def test_one_with_name_with_quotes(self):
        input = "\"Some One\" <someone@example.com>"
        output = decode_header(input)
        expected_output = u"\"Some One\" <someone@example.com>"
        assert output == expected_output

    def test_one_nonascii(self):
        input = "=?utf-8?b?xaHDs21lw7NuZQ==?= <someone@example.com>"
        output = decode_header(input)
        expected_output = u"šómeóne <someone@example.com>"
        assert output == expected_output

    def test_one_nonascii_with_quotes(self):
        input = "\"=?utf-8?b?xaHDs21lw7NuZQ==?=\" <someone@example.com>"
        output = decode_header(input)
        expected_output = u"šómeóne <someone@example.com>"
        assert output == expected_output

    def test_multiple_nonascii_with_quotes(self):
        input = '"Some One" <someone@example.com>, ' \
                '"=?utf-8?b?xaHDs21lw7Nuw6k=?=" <sometwo@example.com>, ' \
                '"Some Three" <somethere@example>'
        output = decode_header(input)
        expected_output = u'"Some One" <someone@example.com>, ' \
                          u'šómeóné <sometwo@example.com>, ' \
                          u'"Some Three" <somethere@example>'
        assert output == expected_output

    def test_multiple_nonascii_with_quotes2(self):
        input = '"=?utf-8?b?xaHDs21lw7Nuw6k=?=" <sometwo@example.com>, ' \
                '"Some Three" <somethere@example>, ' \
                '"=?utf-8?b?xaHDs21lw7NuZQ==?=\" <someone@example.com>'
        output = decode_header(input)
        expected_output = u'šómeóné <sometwo@example.com>, ' \
                          u'"Some Three" <somethere@example>, ' \
                          u"šómeóne <someone@example.com>"
        assert output == expected_output
