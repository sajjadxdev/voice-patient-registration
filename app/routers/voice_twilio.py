import html
import logging
from typing import Dict, List
from fastapi import APIRouter, Form, Request, Response

from app.services.llm_agent import voice_agent
from app.services.patient_service import patient_service
from app.models.appointment import CallTranscriptCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice/twilio", tags=["Twilio Voice Integration"])

# In-memory session store for active calls (CallSid -> message history)
CALL_SESSIONS: Dict[str, List[dict]] = {}


def generate_twiml(say_text: str, gather: bool = True, action_url: str = "/voice/twilio/process") -> str:
    escaped_text = html.escape(say_text)
    if gather:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna-Neural" language="en-US">{escaped_text}</Say>
    <Gather input="speech" action="{action_url}" method="POST" speechTimeout="auto" timeout="5" />
    <Say voice="Polly.Joanna-Neural">I didn't quite catch that. Could you please repeat that for me?</Say>
    <Gather input="speech" action="{action_url}" method="POST" speechTimeout="auto" timeout="5" />
</Response>"""
    else:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna-Neural" language="en-US">{escaped_text}</Say>
    <Hangup />
</Response>"""


@router.post("/incoming")
async def twilio_incoming(
    request: Request,
    CallSid: str = Form(...),
    From: str = Form(default="")
):
    """
    Twilio webhook called when a user dials into the clinic phone number.
    Initializes conversational intake session.
    """
    logger.info(f"Incoming Twilio phone call: CallSid={CallSid}, From={From}")
    
    # Check for returning caller by phone
    greeting = "Hi! Thank you for calling Oakwood Health Clinic. I'm Sarah, your patient intake coordinator. I can help register you today."
    
    CALL_SESSIONS[CallSid] = [
        {"role": "assistant", "content": greeting + " To get started, could I have your first and last name?"}
    ]

    if From:
        existing = patient_service.find_existing_by_phone(From)
        if existing:
            first = existing["first_name"]
            last = existing["last_name"]
            followup = f" Hello, it looks like we may already have a record for {first} {last}. Are you calling to update your information, or would you like to register someone else?"
            CALL_SESSIONS[CallSid] = [
                {"role": "assistant", "content": greeting + followup}
            ]
            twiml = generate_twiml(greeting + followup)
            return Response(content=twiml, media_type="application/xml")

    twiml = generate_twiml(greeting + " To get started, could I have your first and last name?")
    return Response(content=twiml, media_type="application/xml")


@router.post("/process")
async def twilio_process(
    CallSid: str = Form(...),
    SpeechResult: str = Form(default=""),
    From: str = Form(default="")
):
    """
    Processes spoken response transcribed by Twilio STT.
    """
    logger.info(f"Twilio SpeechResult for CallSid {CallSid}: '{SpeechResult}'")
    
    history = CALL_SESSIONS.get(CallSid, [])
    if SpeechResult:
        history.append({"role": "user", "content": SpeechResult})
    
    result = voice_agent.process_turn(history, call_id=CallSid)
    reply = result.get("reply", "Could you please repeat that?")
    is_completed = result.get("is_completed", False)
    
    history.append({"role": "assistant", "content": reply})
    CALL_SESSIONS[CallSid] = history

    if is_completed:
        # Save transcript to DB
        transcript_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history])
        try:
            patient_service.record_call_transcript(CallTranscriptCreate(
                call_id=CallSid,
                caller_phone=From,
                direction="inbound",
                transcript=transcript_text,
                summary=f"Patient intake completed: {reply[:100]}",
                sentiment="positive"
            ))
        except Exception as e:
            logger.error(f"Error saving Twilio call transcript: {e}")

        # Final signoff
        twiml = generate_twiml(reply + " Thank you for calling Oakwood Health Clinic. Goodbye!", gather=False)
    else:
        twiml = generate_twiml(reply, gather=True)

    return Response(content=twiml, media_type="application/xml")
