# edge-agent

Python process that runs on a PC inside the store (owner: Shamsiddinxoja, ML parts: Shohruh).

1. Reads the Hikvision RTSP **sub-stream** (`/Streaming/Channels/<ch>02`) at about 5 fps.
2. Runs the ML pipeline from `ml/` (YOLO + ByteTrack → VideoMAE → zone rule).
3. POSTs events, clips and snapshots to the backend with the store's API key.

Not scaffolded yet.
