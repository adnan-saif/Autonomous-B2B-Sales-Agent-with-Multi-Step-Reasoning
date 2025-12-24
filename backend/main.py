import json
import asyncio
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from graph_app import app as langgraph_app, LeadState, create_test_state

# =================================================
# Pydantic Models for API
# =================================================
class SenderProfile(BaseModel):
    company_name: str
    sender_name: str
    sender_role: str
    company_description: str

class CampaignStartRequest(BaseModel):
    query: str
    mode: str = Field("test", description="Mode: 'test' or 'live'")
    thread_id: Optional[str] = None
    sender_profile: SenderProfile

class EmailApprovalRequest(BaseModel):
    thread_id: str
    decision: str = Field(..., description="'yes' or 'no'")

class MeetingRequest(BaseModel):
    thread_id: str
    decision: str = Field(..., description="'yes' or 'no'")
    meeting_datetime: Optional[str] = Field(None, description="Format: YYYY-MM-DD HH:MM")

class CampaignStatusResponse(BaseModel):
    thread_id: str
    phase: str
    leads_count: int
    qualified_count: int
    emails_ready: int
    emails_sent: int
    monitoring_count: int
    replies_received: int
    current_state: Dict[str, Any]

# =================================================
# FastAPI App
# =================================================
app = FastAPI(title="B2B Lead Generation API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


active_connections: Dict[str, List[WebSocket]] = {}

# =================================================
# Helper Functions
# =================================================
async def notify_clients(thread_id: str, message: Dict[str, Any]):
    """Send update to all connected clients for this thread"""
    if thread_id in active_connections:
        for connection in active_connections[thread_id]:
            try:
                await connection.send_json(message)
            except:
                pass

def get_state_summary(state: LeadState) -> Dict[str, Any]:
    """Extract summary from state"""
    return {
        "phase": state.get("phase", "unknown"),
        "leads_count": len(state.get("leads", [])),
        "qualified_count": len([q for q in state.get("qualification", []) if q.get("qualified")]),
        "emails_ready": len(state.get("emails", [])),
        "emails_sent": len([e for e in state.get("email_send_logs", []) if e.get("status") == "sent"]),
        "monitoring_count": len([m for m in state.get("monitoring", []) if m.get("monitor_status") == "active"]),
        "replies_received": len([m for m in state.get("monitoring", []) if m.get("reply_received")]),
        "current_node": "unknown"
    }

# =================================================
# WebSocket Endpoint
# =================================================
@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await websocket.accept()
    
    if thread_id not in active_connections:
        active_connections[thread_id] = []
    active_connections[thread_id].append(websocket)
    
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        active_connections[thread_id].remove(websocket)
        if not active_connections[thread_id]:
            del active_connections[thread_id]

# =================================================
# API Endpoints
# =================================================
@app.get("/")
async def root():
    return {"message": "B2B Lead Generation API", "status": "running"}

@app.post("/api/campaign/start", response_model=Dict[str, Any])
async def start_campaign(request: CampaignStartRequest):
    """
    Start a new campaign or resume existing one
    """
    try:
        thread_id = request.thread_id or f"campaign-{uuid.uuid4().hex[:8]}"
        
        if request.mode == "test":
            initial_state = create_test_state(request.query, request.sender_profile.dict())
            
            config = {"configurable": {"thread_id": thread_id}}
            
            state = langgraph_app.invoke(initial_state, config=config)
            
            await notify_clients(thread_id, {
                "type": "campaign_started",
                "thread_id": thread_id,
                "mode": "test",
                "state": get_state_summary(state)
            })
            
            return {
                "thread_id": thread_id,
                "status": "started",
                "mode": "test",
                "state_summary": get_state_summary(state),
                "next_action": "review_emails"
            }
            
        else:

            initial_state: LeadState = {
                "query": request.query,
                "companies": [],
                "current_company": {},
                "site_text": "",
                "leads": [],
                "qualification": [],
                "emails": [],
                "email_send_logs": [],
                "monitoring": [],
                "active_monitor": {},
                "source": "unknown",
                "start_from_writer": False,
                "phase": "campaign",
                "human_decision": {},
                "pending_action": "",
                "sender_profile": request.sender_profile.dict()
            }
            
            config = {"configurable": {"thread_id": thread_id}}
            state = langgraph_app.invoke(initial_state, config=config)
            
            await notify_clients(thread_id, {
                "type": "campaign_started",
                "thread_id": thread_id,
                "mode": "live",
                "state": get_state_summary(state)
            })
            
            return {
                "thread_id": thread_id,
                "status": "started",
                "mode": "live",
                "state_summary": get_state_summary(state),
                "next_action": "searching_companies"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start campaign: {str(e)}")

@app.get("/api/campaign/{thread_id}/status", response_model=CampaignStatusResponse)
async def get_campaign_status(thread_id: str):
    """
    Get current status of a campaign
    """
    try:

        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            state = langgraph_app.invoke({}, config=config)
        except:
            # If no state exists
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        summary = get_state_summary(state)
        
        return CampaignStatusResponse(
            thread_id=thread_id,
            phase=summary["phase"],
            leads_count=summary["leads_count"],
            qualified_count=summary["qualified_count"],
            emails_ready=summary["emails_ready"],
            emails_sent=summary["emails_sent"],
            monitoring_count=summary["monitoring_count"],
            replies_received=summary["replies_received"],
            current_state=state
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.post("/api/campaign/{thread_id}/continue")
async def continue_campaign(thread_id: str):
    """
    Continue execution of a paused campaign
    """
    try:

        config = {"configurable": {"thread_id": thread_id}}
        state = langgraph_app.invoke({}, config=config)
        
        await notify_clients(thread_id, {
            "type": "campaign_updated",
            "thread_id": thread_id,
            "state": get_state_summary(state)
        })
        
        return {
            "thread_id": thread_id,
            "status": "continued",
            "state_summary": get_state_summary(state)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to continue campaign: {str(e)}")

@app.post("/api/campaign/{thread_id}/approve-emails")
async def approve_emails(thread_id: str, request: EmailApprovalRequest):
    """
    Approve or reject sending emails
    """
    try:
        if request.decision not in ["yes", "no"]:
            raise HTTPException(status_code=400, detail="Decision must be 'yes' or 'no'")
        
        config = {"configurable": {"thread_id": thread_id}}
        
        current_state = langgraph_app.invoke({}, config=config)
        
        if "human_decision" not in current_state:
            current_state["human_decision"] = {}
        
        current_state["human_decision"]["send_first_email"] = request.decision
        
        new_state = langgraph_app.invoke(current_state, config=config)
        
        await notify_clients(thread_id, {
            "type": "emails_approved" if request.decision == "yes" else "emails_rejected",
            "thread_id": thread_id,
            "decision": request.decision,
            "state": get_state_summary(new_state)
        })
        
        return {
            "thread_id": thread_id,
            "decision": request.decision,
            "status": "processed",
            "state_summary": get_state_summary(new_state)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process email approval: {str(e)}")

@app.post("/api/campaign/{thread_id}/schedule-meeting")
async def schedule_meeting(thread_id: str, request: MeetingRequest):
    try:
        if request.decision not in ["yes", "no"]:
            raise HTTPException(status_code=400, detail="Decision must be 'yes' or 'no'")
        
        if request.decision == "yes" and not request.meeting_datetime:
            raise HTTPException(status_code=400, detail="Meeting datetime required for 'yes' decision")
        
        config = {"configurable": {"thread_id": thread_id}}
        current_state = langgraph_app.invoke({}, config=config)
        
        if "human_decision" not in current_state:
            current_state["human_decision"] = {}
        
        current_state["human_decision"]["send_meeting_email"] = request.decision
        
        if request.decision == "yes":
            current_state["human_decision"]["meeting_datetime"] = request.meeting_datetime
        
        new_state = langgraph_app.invoke(current_state, config=config)
        

        if request.decision == "yes":
            new_state = langgraph_app.invoke(new_state, config=config)
        
        await notify_clients(thread_id, {
            "type": "meeting_scheduled" if request.decision == "yes" else "meeting_declined",
            "thread_id": thread_id,
            "decision": request.decision,
            "state": get_state_summary(new_state)
        })
        
        return {
            "thread_id": thread_id,
            "decision": request.decision,
            "status": "processed",
            "state_summary": get_state_summary(new_state)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule meeting: {str(e)}")

@app.get("/api/campaign/{thread_id}/leads")
async def get_leads(thread_id: str):
    """
    Get all leads for a campaign
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = langgraph_app.invoke({}, config=config)
        
        leads = state.get("leads", [])
        qualification = state.get("qualification", [])
        
        for lead in leads:
            qual = next((q for q in qualification if q["company_name"] == lead["company_name"]), {})
            lead["qualification_score"] = qual.get("qualification_score", 0)
            lead["qualified"] = qual.get("qualified", False)
            lead["qualification_reason"] = qual.get("qualification_reason", [])
        
        return {
            "thread_id": thread_id,
            "leads": leads,
            "count": len(leads)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get leads: {str(e)}")

@app.get("/api/campaign/{thread_id}/emails")
async def get_emails(thread_id: str):
    """
    Get all drafted emails for a campaign
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = langgraph_app.invoke({}, config=config)
        
        emails = state.get("emails", [])
        send_logs = state.get("email_send_logs", [])
        
        for email in emails:
            log = next((l for l in send_logs if l["email"] == email["email"] and l["company_name"] == email["company_name"]), {})
            email["sent"] = log.get("status") == "sent"
            email["sent_at"] = log.get("sent_at")
            email["message_id"] = log.get("message_id")
        
        return {
            "thread_id": thread_id,
            "emails": emails,
            "count": len(emails)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get emails: {str(e)}")

@app.get("/api/campaign/{thread_id}/monitoring")
async def get_monitoring(thread_id: str):
    """
    Get monitoring status for a campaign
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = langgraph_app.invoke({}, config=config)
        
        monitoring = state.get("monitoring", [])
        active_monitor = state.get("active_monitor", {})
        
        return {
            "thread_id": thread_id,
            "monitoring": monitoring,
            "active_monitor": active_monitor,
            "count": len(monitoring)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring data: {str(e)}")

@app.get("/api/threads")
async def list_threads():
    """
    List all campaign threads
    """
    try:

        return {
            "threads": [],
            "count": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list threads: {str(e)}")

# =================================================
# Run the application
# =================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)