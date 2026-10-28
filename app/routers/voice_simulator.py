import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models.envelope import api_success, api_error
from app.models.appointment import CallTranscriptCreate
from app.services.llm_agent import voice_agent
from app.services.patient_service import patient_service
from app.repositories.patient_repo import patient_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice/simulate", tags=["Voice Call Simulator"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class SimulationTurnRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Optional conversation session ID")
    messages: List[ChatMessage] = Field(..., description="Full or appended message history")
    caller_phone: Optional[str] = Field(None, description="Simulated caller phone number")


@router.post("/turn", status_code=status.HTTP_200_OK)
def simulate_conversation_turn(payload: SimulationTurnRequest):
    """
    Simulates a voice intake conversational turn.
    Returns the agent's spoken reply, executed tool calls, and completion status.
    """
    try:
        session_id = payload.session_id or str(uuid.uuid4())
        msg_dicts = [{"role": m.role, "content": m.content} for m in payload.messages]
        
        result = voice_agent.process_turn(msg_dicts, call_id=session_id)
        
        # If call completed, persist call transcript
        if result.get("is_completed"):
            full_transcript = "\n".join([f"{m.role.upper()}: {m.content}" for m in payload.messages]) + f"\nASSISTANT: {result.get('reply')}"
            try:
                patient_service.record_call_transcript(CallTranscriptCreate(
                    call_id=session_id,
                    caller_phone=payload.caller_phone or "Simulated Call",
                    direction="inbound",
                    transcript=full_transcript,
                    summary="Patient registration completed successfully.",
                    sentiment="positive",
                    duration_seconds=120
                ))
            except Exception as e:
                logger.warning(f"Could not persist simulation transcript: {e}")

        return api_success({
            "session_id": session_id,
            "reply": result.get("reply"),
            "tool_calls_executed": result.get("tool_calls_executed", []),
            "is_completed": result.get("is_completed", False)
        })
    except Exception as e:
        logger.error(f"Error in voice simulation turn: {e}", exc_info=True)
        return api_error(f"Failed to process conversation turn: {str(e)}", code=500)


@router.get("/transcripts", status_code=status.HTTP_200_OK)
def list_call_transcripts(limit: int = 50):
    """
    List historical call transcripts and logs.
    """
    logs = patient_repo.list_call_logs(limit=limit)
    return api_success(logs)
