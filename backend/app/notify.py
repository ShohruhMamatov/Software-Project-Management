"""Alerts for new events (Telegram / email). Called by POST /agent/events.

TODO (Temur, tickets "Telegram alert bot" and "Email alerts"): send the snapshot, time,
camera name and a link to the review page. Keep it fast or run it in a background task,
so a slow Telegram API never blocks the edge agent's upload.
"""

import logging

from app.models import Event

log = logging.getLogger("lumi.notify")


def notify_new_event(event: Event) -> None:
    log.info("New event %s on camera %s (score %.2f)", event.id, event.camera_id, event.score)
