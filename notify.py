"""This module provides a class to send a message to LINE Notify.

The LineNotify class provides a method to send a message to LINE Notify.
"""

import io
import logging
from typing import BinaryIO

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

LINENOTIFY_API_URL = "https://notify-api.line.me/api/notify"


class LineNotify:
    """A class to send a message to LINE Notify.
    
    Attributes:
        url (str): The LINE Notify API URL.
        token_index (int): The index of the LINE Notify token.
    """

    def __init__(self):
        self.url = LINENOTIFY_API_URL
        self.token_index = 0

    def send(
        self, token: str, message: str, image_file: str | bytes | BinaryIO | None = None, image_url: str | None = None, retries: int | None = 2
    ) -> bool:
        """Send a message to LINE Notify.

        Args:
            token (str): The LINE Notify token.
            message (str): The message to send.
            image_file (str, bytes, BinaryIO, optional): The image file to send. Defaults to None.
            image_url (str, optional): The URL of the image to send. Defaults to None.
            retries (int, optional): The number of retries. Defaults to 2.
        
        Returns:
            bool: True if the message was sent successfully, False otherwise.
        """

        headers = {"Authorization": "Bearer " + token}

        retry_strategy = Retry(
            total=retries,
            status_forcelist=(500, 502, 503, 504)
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        data = {"message": message}
        if isinstance(image_file, (bytes, io.IOBase)):
            files = {"imageFile": image_file}
        elif isinstance(image_file, str):
            try:
                with open(image_file, "rb") as img:
                    files = {"imageFile": img}
            except FileNotFoundError as err:
                logger.error("File not found: %s", err)
                files = None
        elif image_url:
            files = {"imageFullsize": image_url}
        else:
            files = None

        try:
            response = session.post(
                self.url, headers=headers, data=data, files=files)
            if response.status_code == 400 and response.text == "Image rate limit exceeded.":
                logger.error(
                    "Image rate limit exceeded. Sending text only.")
                response = session.post(
                    self.url, headers=headers, data=data)
            response.raise_for_status()
            logger.info("Message sent successfully.")
            return True
        except requests.exceptions.HTTPError as err:
            logger.error("HTTP error occurred: %s", err)
        except Exception as err:
            logger.error("Error occurred: %s", err)
        finally:
            session.close()

        return False
