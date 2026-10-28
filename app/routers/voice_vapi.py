import json
import logging
from typing import Any, Dict
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.services.llm_agent import execute_agent_tool
from app.services.patient_service import patient_service
from app.models.appointment import CallTranscriptCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice/vapi", tags=["Vapi Telephony Integration"])


@router.post("/webhook")
async def vapi_webhook(request: Request):
    """
    Handles Vapi webhook events, including:
    - Tool calls (check_patient_by_phone, save_patient_registration, schedule_appointment)
    - Status updates & End-of-call reporting (saves call transcript)
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    message = body.get("message", {})
    message_type = message.get("type") or body.get("type")

    logger.info(f"Received Vapi webhook event: {message_type}")

    # Handle Tool / Function Calls
    if message_type in ("tool-calls", "function-call"):
        # Vapi passes tool calls in toolCalls or functionCall
        tool_calls = message.get("toolCalls") or []
        if not tool_calls and "functionCall" in message:
            fn = message["functionCall"]
            tool_calls = [{
                "id": fn.get("name", "call_1"),
                "function": {
                    "name": fn.get("name"),
                    "arguments": fn.get("parameters") or {}
                }
            }]

        results = []
        for call in tool_calls:
            call_id = call.get("id")
            fn_data = call.get("function", {})
            name = fn_data.get("name")
            args = fn_data.get("arguments", {})

            # Parse string arguments if received as JSON string
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}

            logger.info(f"Executing Vapi tool '{name}' with args: {args}")
            res = execute_agent_tool(name, args)
            results.append({
                "toolCallId": call_id,
                "result": json.dumps(res)
            })

        return JSONResponse(status_code=200, content={"results": results})

    # Handle End of Call Report (Transcript and Sentiment Logging)
    elif message_type in ("end-of-call-report", "call-ended"):
        call_id = message.get("call", {}).get("id") or body.get("call", {}).get("id")
        customer_phone = message.get("customer", {}).get("number")
        transcript = message.get("transcript") or message.get("summary") or "Voice call completed."
        summary = message.get("summary")
        duration = message.get("durationSeconds") or 0

        # Try to find associated patient
        patient_id = None
        if customer_phone:
            existing = patient_service.find_existing_by_phone(customer_phone)
            if existing:
                patient_id = existing["patient_id"]

        try:
            patient_service.record_call_transcript(CallTranscriptCreate(
                call_id=call_id,
                patient_id=patient_id,
                caller_phone=customer_phone,
                direction="inbound",
                transcript=transcript,
                summary=summary,
                sentiment="completed",
                duration_seconds=duration
            ))
            logger.info(f"Persisted call transcript for call {call_id}")
        except Exception as e:
            logger.error(f"Failed to save call log: {e}")

        return JSONResponse(status_code=200, content={"status": "logged"})

    return JSONResponse(status_code=200, content={"status": "acknowledged"})
