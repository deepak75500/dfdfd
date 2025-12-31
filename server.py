import os
import json
import uuid
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

rooms = {}  # room_id -> {peer_id: pc}

async def index(request):
    return web.FileResponse("./static/index.html")

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    peer_id = str(uuid.uuid4())
    pc = RTCPeerConnection()
    room_id = None

    async for msg in ws:
        data = json.loads(msg.data)

        # JOIN ROOM
        if data["type"] == "join":
            room_id = data["room"]
            rooms.setdefault(room_id, {})
            rooms[room_id][peer_id] = pc

            await ws.send_json({
                "type": "joined",
                "peerId": peer_id
            })

        # OFFER
        elif data["type"] == "offer":
            offer = RTCSessionDescription(**data["offer"])
            await pc.setRemoteDescription(offer)

            # Forward existing tracks
            for other_id, other_pc in rooms[room_id].items():
                if other_id != peer_id:
                    for sender in other_pc.getSenders():
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

        # ICE
        elif data["type"] == "candidate":
            await pc.addIceCandidate(data["candidate"])

    # CLEANUP
    if room_id and peer_id in rooms.get(room_id, {}):
        del rooms[room_id][peer_id]
        if not rooms[room_id]:
            del rooms[room_id]

    await pc.close()
    return ws


app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/ws", websocket_handler)

PORT = int(os.environ.get("PORT", 8000))
web.run_app(app, host="0.0.0.0", port=PORT)
