"""Pretend to be the edge agent: send a heartbeat and/or a fake event to the backend.

Lets the frontend be built and demoed before the real edge agent exists.

Usage (from the repo root, with the backend venv active):
    python scripts/send_test_event.py --api-key lumi_xxx --camera-id 1
    python scripts/send_test_event.py --api-key lumi_xxx --camera-id 1 --snapshot frame.jpg --clip clip.webm
    python scripts/send_test_event.py --api-key lumi_xxx --camera-id 1 --heartbeat-only --snapshot frame.jpg

The API key is shown once when the store is created (or rotate it: POST /stores/me/api-key).
"""

import argparse
import random
from datetime import datetime, timezone
from pathlib import Path

import httpx

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webm": "video/webm", ".mp4": "video/mp4"}


def file_part(path: str | None):
    if not path:
        return None
    p = Path(path)
    return (p.name, p.read_bytes(), MIME.get(p.suffix.lower(), "application/octet-stream"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", default="http://localhost:8000")
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--camera-id", type=int, required=True)
    ap.add_argument("--score", type=float, default=None, help="default: random 0.6-0.99")
    ap.add_argument("--snapshot", help=".jpg/.png to attach")
    ap.add_argument("--clip", help=".webm/.mp4 to attach")
    ap.add_argument("--heartbeat-only", action="store_true", help="only mark the camera online (+ snapshot)")
    args = ap.parse_args()

    headers = {"X-API-Key": args.api_key}
    with httpx.Client(base_url=args.backend, headers=headers, timeout=30) as http:
        files = {"snapshot": file_part(args.snapshot)} if args.snapshot else None
        r = http.post(f"/agent/cameras/{args.camera_id}/heartbeat", files=files)
        r.raise_for_status()
        print("heartbeat ok: camera is online")
        if args.heartbeat_only:
            return

        data = {
            "camera_id": str(args.camera_id),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "score": str(args.score if args.score is not None else round(random.uniform(0.6, 0.99), 2)),
        }
        files = {k: v for k, v in {"clip": file_part(args.clip), "snapshot": file_part(args.snapshot)}.items() if v}
        r = http.post("/agent/events", data=data, files=files or None)
        r.raise_for_status()
        print("event created:", r.json())


if __name__ == "__main__":
    main()
