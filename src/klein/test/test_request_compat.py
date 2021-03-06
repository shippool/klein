# -*- test-case-name: klein.test.test_request_compat -*-
# Copyright (c) 2011-2021. See LICENSE for details.

"""
Tests for L{klein._irequest}.
"""

from string import ascii_uppercase
from typing import Optional

from hyperlink import DecodedURL, EncodedURL
from hyperlink.hypothesis import decoded_urls

from hypothesis import given
from hypothesis.strategies import binary, text

from twisted.web.http_headers import Headers
from twisted.web.iweb import IRequest

from ._trial import TestCase
from .test_resource import requestMock
from .._headers import IHTTPHeaders
from .._message import FountAlreadyAccessedError
from .._request import IHTTPRequest
from .._request_compat import HTTPRequestWrappingIRequest


__all__ = ()


class HTTPRequestWrappingIRequestTests(TestCase):
    """
    Tests for L{HTTPRequestWrappingIRequest}.
    """

    def legacyRequest(
        self,
        path: bytes = b"/",
        method: bytes = b"GET",
        host: bytes = b"localhost",
        port: int = 8080,
        isSecure: bool = False,
        body: bytes = b"",
        headers: Optional[Headers] = None,
    ) -> IRequest:
        return requestMock(
            path=path,
            method=method,
            host=host,
            port=port,
            isSecure=isSecure,
            body=body,
            headers=headers,
        )

    def test_interface(self) -> None:
        """
        L{HTTPRequestWrappingIRequest} implements L{IHTTPRequest}.
        """
        request = HTTPRequestWrappingIRequest(request=self.legacyRequest())
        self.assertProvides(IHTTPRequest, request)

    @given(text(alphabet=ascii_uppercase, min_size=1))
    def test_method(self, methodText: str) -> None:
        """
        L{HTTPRequestWrappingIRequest.method} matches the underlying legacy
        request method.
        """
        legacyRequest = self.legacyRequest(method=methodText.encode("ascii"))
        request = HTTPRequestWrappingIRequest(request=legacyRequest)
        self.assertEqual(request.method, methodText)

    @given(decoded_urls())
    def test_uri(self, url: DecodedURL) -> None:
        """
        L{HTTPRequestWrappingIRequest.uri} matches the underlying legacy
        request URI.
        """
        uri = url.asURI()  # Normalize as (computer-friendly) URI

        assert uri.port is not None  # Tells mypy it's not an Optional

        path = (
            uri.replace(scheme="", host="", port=None).asText().encode("ascii")
        )
        legacyRequest = self.legacyRequest(
            isSecure=(uri.scheme == "https"),
            host=uri.host.encode("ascii"),
            port=uri.port,
            path=path,
        )
        request = HTTPRequestWrappingIRequest(request=legacyRequest)

        uriNormalized = uri
        requestURINormalized = request.uri.asURI()

        # Needed because non-equal URLs can render as the same strings
        def strURL(url: EncodedURL) -> str:
            return (
                "URL(scheme={url.scheme!r}, "
                "userinfo={url.userinfo!r}, "
                "host={url.host!r}, "
                "port={url.port!r}, "
                "path={url.path!r}, "
                "query={url.query!r}, "
                "fragment={url.fragment!r}, "
                "rooted={url.rooted})"
            ).format(url=url)

        self.assertEqual(
            requestURINormalized,
            uriNormalized,
            "{} != {}".format(
                strURL(requestURINormalized), strURL(uriNormalized)
            ),
        )

    def test_headers(self) -> None:
        """
        L{HTTPRequestWrappingIRequest.headers} returns an
        L{HTTPRequestWrappingIRequest} containing the underlying legacy request
        headers.
        """
        legacyRequest = self.legacyRequest()
        request = HTTPRequestWrappingIRequest(request=legacyRequest)
        self.assertProvides(IHTTPHeaders, request.headers)

    def test_bodyAsFountTwice(self) -> None:
        """
        L{HTTPRequestWrappingIRequest.bodyAsFount} raises
        L{FountAlreadyAccessedError} if called more than once.
        """
        legacyRequest = self.legacyRequest()
        request = HTTPRequestWrappingIRequest(request=legacyRequest)
        request.bodyAsFount()
        self.assertRaises(FountAlreadyAccessedError, request.bodyAsFount)

    @given(binary())
    def test_bodyAsBytes(self, data: bytes) -> None:
        """
        L{HTTPRequestWrappingIRequest.bodyAsBytes} matches the underlying
        legacy request body.
        """
        legacyRequest = self.legacyRequest(body=data)
        request = HTTPRequestWrappingIRequest(request=legacyRequest)
        body = self.successResultOf(request.bodyAsBytes())

        self.assertEqual(body, data)

    def test_bodyAsBytesCached(self) -> None:
        """
        L{HTTPRequestWrappingIRequest.bodyAsBytes} called twice returns the
        same object both times.
        """
        data = b"some data"
        legacyRequest = self.legacyRequest(body=data)
        request = HTTPRequestWrappingIRequest(request=legacyRequest)
        body1 = self.successResultOf(request.bodyAsBytes())
        body2 = self.successResultOf(request.bodyAsBytes())

        self.assertIdentical(body1, body2)
