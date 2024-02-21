"""Main entry point for the application.

This module starts the application based on the NVR type.
"""

import os
import logging

logging.basicConfig(level=logging.INFO)

NVR_TYPE = os.getenv("NVR_TYPE")
FLASK_RUN_HOST = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
FLASK_RUN_PORT = int(os.getenv("FLASK_RUN_PORT", "8080"))


if NVR_TYPE is None:
    raise ValueError("NVR_TYPE is not set")
if NVR_TYPE.lower() == "synology":
    import synology

    synology.app.run(host=FLASK_RUN_HOST, port=FLASK_RUN_PORT)
elif NVR_TYPE.lower() == "frigate":
    from frigate import FrigateMQTTSubscriber

    frigate_subscriber = FrigateMQTTSubscriber()
    frigate_subscriber.run_forever()
else:
    raise ValueError(f"Unsupported NVR type: {NVR_TYPE}")
