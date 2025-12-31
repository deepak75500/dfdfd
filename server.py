import os
import json
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

rooms = {}

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    pc = RTCPeerConnection()
    room_id = None

    async for msg in ws:
        data = json.loads(msg.data)

        if data["type"] == "join":
            room_id = data["room"]
            rooms.setdefault(room_id, []).append(pc)
            await ws.send_json({"type": "joined"})

        elif data["type"] == "offer":
            offer = RTCSessionDescription(**data["offer"])
            await pc.setRemoteDescription(offer)

            for other in rooms.get(room_id, []):
                if other != pc:
                    for sender in other.getSenders():
                        if sender.track:
                            pc.addTrack(sender.track)

            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            await ws.send_json({
                "type": "answer",
                "answer": {
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type
                }
            })

    return ws

app = web.Application()
app.router.add_get("/ws", websocket_handler)

PORT = int(os.environ.get("PORT", 8000))
web.run_app(app, host="0.0.0.0", port=PORT)
