"""Adapt API Gateway HTTP API v2 requests to the Flask WSGI application."""

import base64
from urllib.parse import unquote

from werkzeug.test import Client
from werkzeug.wrappers import Response

from app import app

client = Client(app, Response, use_cookies=False)


def lambda_handler(event, _context):
    http = event["requestContext"]["http"]
    headers = event.get("headers") or {}
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body)
    response = client.open(
        path=unquote(event["rawPath"]),
        method=http["method"],
        query_string=event.get("rawQueryString", ""),
        headers=headers,
        data=body,
    )
    return {
        "statusCode": response.status_code,
        "headers": dict(response.headers),
        "body": response.get_data(as_text=True),
        "isBase64Encoded": False,
    }
