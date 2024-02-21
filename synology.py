""" Flask app to handle Synology Surveillance Station webhooks.

This module provides a Flask app to handle Synology Surveillance Station webhooks.
"""

import json
import logging
import os

import requests
from flask import Flask, abort, request

from notify import LineNotify
from utils.line_token_rotator import LineTokenRotator

LINE_NOTIFY_TOKENS = [token.strip()
                      for token in os.getenv("LINE_NOTIFY_TOKENS").split(",")]
line_notify = LineNotify()
line_token_rotator = LineTokenRotator(LINE_NOTIFY_TOKENS)

logger = logging.getLogger(__name__)

FLASK_RUN_HOST = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
FLASK_RUN_PORT = int(os.getenv("FLASK_RUN_PORT", "8080"))
app = Flask(__name__)


def parse_request() -> dict:
    """Parse the request and return the data.

    Returns:
        dict: The parsed data.

    Raises:
        HTTPException: If the content type is not supported.
    """

    mimetype = request.mimetype
    if mimetype == "application/json":
        data = request.get_json()
    elif mimetype == "application/x-www-form-urlencoded":
        data = json.loads(next(iter(request.form.keys())))
    else:
        abort(400, description="Unsupported content type")
    return data


def validate_data(data: dict) -> tuple[str, str]:
    """Validate the data.

    Args:
        data (dict): The data to validate.

    Returns:
        tuple[str, str]: The message and image URL.

    Raises:
        HTTPException: If the message or image URL is missing.
    """

    message = data.get("message")
    image_url = data.get("image_url")
    if message is None or image_url is None:
        abort(400, description="Missing message or image_url")
    return message, image_url


@app.route("/webhook", methods=["POST"])
def handle_webhook() -> str:
    """Handle the webhook.

    Returns:
        str: The response message.
    
    Raises:
        HTTPException: If the request cannot be parsed or the data is invalid.
    """

    try:
        data = parse_request()
        message, image_url = validate_data(data)
    except Exception as err:
        logger.error("Failed to parse request: %s", err)
        abort(400, description="Failed to parse request")

    try:
        if "ATTACHMENT" not in image_url:
            response = requests.get(image_url)
            if response.status_code != 200:
                logger.error("Failed to retrieve image. URL: %s, Status code: %s",
                             response.url, response.status_code)
                abort(500, description="Failed to retrieve image")

            image_data = response.content
        else:
            image_data = None

        is_success = line_notify.send(token=line_token_rotator.current_token(), message=message,
                                      image_file=image_data)
        if not is_success:
            logger.error("Failed to send notification.")
            abort(500, description="Failed to send notification")

        line_token_rotator.rotate_token()
    except Exception as err:
        logger.error("Failed to send snapshot: %s", err)
        abort(500, description="Failed to send snapshot")

    return "Webhook received successfully"


if __name__ == "__main__":
    app.run(host=FLASK_RUN_HOST, port=FLASK_RUN_PORT)
