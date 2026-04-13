"""Notification endpoints — /api/notify/*."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import notifier, scanner

router = APIRouter()


class LineNotifyRequest(BaseModel):
    message: str = ""   # if empty, auto-build from latest scan


@router.post("/line")
async def notify_line(req: LineNotifyRequest = LineNotifyRequest()):
    """
    Send a LINE Notify message.

    If `message` is omitted, the endpoint runs a fresh scan of the full
    watchlist and sends the formatted signal report automatically.
    """
    message = req.message.strip()

    if not message:
        # Auto-build: scan both markets and format
        combined = await scanner.scan_all()
        message  = notifier.build_scan_message(
            combined["TW"], combined["US"]
        )

    success, detail = await notifier.send(message)

    if not success:
        raise HTTPException(status_code=502, detail=f"LINE Notify 發送失敗: {detail}")

    return {"status": "sent", "message_length": len(message)}
