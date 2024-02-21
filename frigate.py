"""A module to subscribe to Frigate MQTT events and send notifications to LINE Notify.

This module provides a class to subscribe to Frigate MQTT events and send notifications to LINE Notify.
"""

import json
import logging
import os
import time

import paho.mqtt.client as mqtt
import requests

from notify import LineNotify
from utils.line_token_rotator import LineTokenRotator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# The time interval in seconds between sending notifications for the same camera.
SEND_INTERVAL = float(os.getenv("SEND_INTERVAL", "1.5"))

LINE_NOTIFY_TOKENS = [token.strip()
                      for token in os.getenv("LINE_NOTIFY_TOKENS").split(",")]
FRIGATE_HOST = os.getenv("FRIGATE_HOST", "localhost")
BROKER_ADDRESS = os.getenv("MQTT_BROKER_ADDRESS", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "frigate/events")

line_notify = LineNotify()
line_token_rotator = LineTokenRotator(LINE_NOTIFY_TOKENS)


class FrigateMQTTSubscriber:
    """A class to subscribe to Frigate MQTT events and send notifications to LINE Notify.

    Attributes:
        BROKER (str): The address of the MQTT broker.
        PORT (int): The port of the MQTT broker.
        TOPIC (str): The MQTT topic to subscribe to.
    """

    BROKER = BROKER_ADDRESS
    PORT = BROKER_PORT
    TOPIC = MQTT_TOPIC

    def __init__(self):
        self.mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqttc.on_connect = self.on_connect
        self.mqttc.on_message = self.on_message

        # Dictionary to store the last notification time for each camera
        self.last_send_time = {}

    def on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        """Callback function for when the client receives a CONNACK response from the server.

        Args:
            client (mqtt.Client): The client instance for this callback.
            userdata (Any): The private user data as set in Client() or user_data_set().
            flags (Dict): Response flags sent by the broker.
            reason_code (int): The connection result.
            properties (Properties): The properties returned by the broker.
        """

        if reason_code == 0:
            logger.info(
                "Connected to MQTT broker at %s:%s", self.BROKER, self.PORT)
            client.subscribe(self.TOPIC)
        else:
            logger.error("Connection failed with code %s", reason_code)

    def on_message(self, client, userdata, msg) -> None:
        """Callback function for when a PUBLISH message is received from the server.

        Args:
            client (mqtt.Client): The client instance for this callback.
            userdata (Any): The private user data as set in Client() or user_data_set().
            msg (mqtt.MQTTMessage): An instance of MQTTMessage.
        """

        payload_str = msg.payload.decode("utf-8")
        try:
            event = json.loads(payload_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON message.")
            return

        # https://github.com/blakeblackshear/frigate/discussions/2898#discussion-3915893
        if not event.get("after", {}).get("entered_zones"):
            return
        if event.get("type") != "new" and event.get("before", {}).get("entered_zones"):
            return

        event_id = event.get("after", {}).get("id")
        snapshot_time = event.get("after", {}).get(
            "snapshot", {}).get("frame_time")
        camera = event.get("after", {}).get("camera")

        if not all([event_id, snapshot_time, camera]):
            logger.error(
                "Missing required fields in event message: %s", event
            )
            return

        # Check if the time difference between the current notification and the last notification for this camera is less than SEND_INTERVAL seconds.
        last_send_time = self.last_send_time.get(camera)
        if last_send_time is not None and snapshot_time - last_send_time < SEND_INTERVAL:
            logger.info("Skipping notification for camera %s.", camera)
            return

        try:
            response = requests.get(
                f"http://{FRIGATE_HOST}:5000/api/events/{event_id}/snapshot.jpg?bbox=1&timestamp=1")
            if response.status_code != 200:
                logger.error(
                    "Failed to retrieve image. URL: %s, Status code: %s", response.url, response.status_code
                )
                return

            image_data = response.content
            is_success = line_notify.send(token=line_token_rotator.current_token(),
                                          message=camera, image_file=image_data)
            if not is_success:
                logger.error("Failed to send notification.")
                return

            line_token_rotator.rotate_token()
            self.last_send_time[camera] = snapshot_time
        except Exception as err:
            logger.error("Failed to send snapshot: %s", err)

    def run_forever(self):
        """Run the MQTT client forever.

        Connect to the MQTT broker and start the network loop to process incoming messages.
        """

        if MQTT_USERNAME is not None:
            self.mqttc.username_pw_set(
                username=MQTT_USERNAME, password=MQTT_PASSWORD)
        for _ in range(3):  # Try to connect 3 times
            try:
                self.mqttc.connect(self.BROKER, self.PORT)
                break
            except Exception as err:
                logger.error(
                    "Failed to connect to MQTT broker: %s, retrying...", err)
                time.sleep(5)  # Wait for 5 seconds before trying to reconnect
        else:
            logger.error("Failed to connect to MQTT broker after 3 attempts")
            return  # Exit the function if connection failed after 3 attempts
        self.mqttc.loop_forever()


if __name__ == "__main__":
    frigate_subscriber = FrigateMQTTSubscriber()
    frigate_subscriber.run_forever()
