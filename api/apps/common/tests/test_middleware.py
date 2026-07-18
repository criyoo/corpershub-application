import warnings
from unittest import IsolatedAsyncioTestCase

from django.http import StreamingHttpResponse

from apps.common.middleware import prepare_asgi_streaming_response


class AsyncStreamingResponseMiddlewareTests(IsolatedAsyncioTestCase):
    async def test_converts_sync_streaming_response_for_asgi_requests(self):
        request = type("Request", (), {"scope": {"type": "http"}})()
        response = StreamingHttpResponse(iter([b"content"]))

        converted_response = prepare_asgi_streaming_response(request, response)

        self.assertTrue(converted_response.is_async)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            chunks = [chunk async for chunk in converted_response]

        self.assertEqual(chunks, [b"content"])
        self.assertEqual(caught, [])
