from typing import TypedDict, List, Dict, Any, Set
import json
import re
import os
import requests
import dns.resolver
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from ddgs import DDGS

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import make_msgid
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

# =================================================
# Config for mail
# =================================================
SMTP_CONFIG = {
    "host": "smtp.gmail.com",
    "port": 587,
    "username": "aegontar5454@gmail.com",
    "password": "xhyw jtoc ryax epqs",
    "from_name": "B2B Research Team"
}

# =================================================
# LLM
# =================================================
model = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.1-8b-instant",
    temperature=0
)

# =================================================
# Structure LLM
# =================================================
class EmailDraft(BaseModel):
    subject: str = Field(
        description="Short, Professional & Attractive subject line under 60 characters"
    )
    body: str = Field(
        description="Plain text B2B cold email body, 100-200 words, no placeholders"
    )

structured_email_model = model.with_structured_output(EmailDraft)

# =================================================
# CHECKPOINTER (PERSIST STATE)
# =================================================
conn = sqlite3.connect("lead_graph_state.db", check_same_thread=False)

checkpointer = SqliteSaver(conn=conn)

# =================================================
# GOOGLE CALENDAR SETUP (ONE TIME)
# =================================================
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

CAL_SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", CAL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", CAL_SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

# =================================================
# CONSTANTS
# =================================================
HEADERS = {"User-Agent": "Mozilla/5.0 (B2BResearchBot/1.0)"}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

BAD_DOMAINS = [
    "facebook.com", "linkedin.com", "twitter.com", "x.com",
    "reddit.com", "whatsapp.com", "youtube.com", "instagram.com",
    "tracxn.com", "f6s.com", "crunchbase.com", "medium.com",
    "techcrunch.com", "news", "wikipedia.org", "britannica.com", "wikimedia.org"
]

ROLE_PREFIXES = {
    "info", "contact", "sales",
    "support", "business", "careers"
}

DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com",
    "tempmail.com", "yopmail.com"
}

ICP_CONFIG = {
    "industries": {"ai", "saas", "fintech"},
    "company_sizes": {"small", "medium"},
    "min_score": 70
}


# =================================================
# Helper
# =================================================
def is_real_company_site(domain: str) -> bool:
    reject_keywords = [
        "news", "blog", "mag", "tracker", "directory",
        "listing", "media", "funding", "startup",
        "magazine", "portal", "wiki"
    ]
    return not any(k in domain for k in reject_keywords)

def normalize_company_size(emp_count: int | None) -> str:
    if not emp_count:
        return "unknown"
    if emp_count <= 50:
        return "small"
    if emp_count <= 250:
        return "medium"
    if emp_count <= 1000:
        return "large"
    return "enterprise"

def map_keywords_to_intent(keywords: List[str]) -> List[str]:
    text = " ".join(k.lower() for k in keywords)
    intents = []

    if "artificial intelligence" in text or "machine learning" in text:
        intents.append("ai platform")
    if "saas" in text or "enterprise software" in text:
        intents.append("enterprise software")
    if "lead generation" in text or "b2b" in text:
        intents.append("lead generation platform")
    if "automation" in text:
        intents.append("automation solution")

    return list(set(intents))

def normalize_industry(raw: str) -> str:
    if not raw:
        return "unknown"

    priority = ["ai", "saas", "fintech", "ecommerce", "health-care", "other"]

    raw = raw.lower()
    for p in priority:
        if p in raw:
            return p

    return "unknown"

def normalize_company_size_llm(raw: str) -> str:
    if not raw:
        return "unknown"

    priority = ["small", "medium", "large", "unknown"]

    raw = raw.lower()
    for p in priority:
        if p in raw:
            return p

    return "unknown"

def get_email_quality(emails: List[str]) -> str:
    if not emails:
        return "none"

    for e in emails:
        local = e.split("@")[0]
        if local not in ROLE_PREFIXES:
            return "personal"

    return "role_based"


def get_intent_confidence(intent_signals: List[str]) -> str:
    if not intent_signals:
        return "low"
    if len(intent_signals) == 1:
        return "medium"
    return "high"


def calculate_research_confidence(
    industry: str,
    company_size: str,
    emails: List[str],
    people: List[str],
    intent_signals: List[str]
) -> float:
    score = 0.0

    if industry != "unknown":
        score += 0.2
    if company_size != "unknown":
        score += 0.2
    if emails:
        score += 0.2
    if intent_signals:
        score += 0.2
    if people:
        score += 0.2

    return round(score, 2)


import imaplib
import email
import time

IMAP_CONFIG = {
    "host": "imap.gmail.com",
    "username": SMTP_CONFIG["username"],
    "password": SMTP_CONFIG["password"]
}

def check_reply_for_message_id(message_id: str) -> bool:
    """
    Check Gmail inbox for replies to a specific Message-ID
    using IMAP HEADER search (In-Reply-To / References).
    """

    # Gmail IMAP requires Message-ID WITHOUT <>
    search_id = message_id.strip("<>")

    mail = imaplib.IMAP4_SSL(IMAP_CONFIG["host"])
    mail.login(IMAP_CONFIG["username"], IMAP_CONFIG["password"])
    mail.select("inbox")

    # Search by In-Reply-To
    status, data = mail.search(
        None,
        f'HEADER "In-Reply-To" "{search_id}"'
    )

    if status == "OK" and data[0]:
        mail.logout()
        return True

    # Fallback: search by References
    status, data = mail.search(
        None,
        f'HEADER "References" "{search_id}"'
    )

    if status == "OK" and data[0]:
        mail.logout()
        return True

    mail.logout()
    return False


def generate_followup_email(lead: Dict[str, Any], followup_no: int, sender: Dict[str, Any]) -> EmailDraft:

    prompt = f"""
Write a professional B2B follow-up email.

Rules:
- No emojis
- No hype
- No placeholders like [Your Name]
- Plain text only
- 60–90 words
- Polite and respectful
- Not pushy
- Clear soft CTA
- This is FOLLOW-UP #{followup_no}

Context:
Company: {lead["company_name"]}
Industry: {lead.get("industry")}
Pain Points: {lead.get("pain_points")}
Original Intent: {lead.get("intent_signals")}


Sender Information:
- Name: {sender["sender_name"]}
- Role: {sender["sender_role"]}
- Company: {sender["company_name"]}
- What we do: {sender["company_description"]}

Example:
Hi {lead["company_name"]},

Dear Recipient, I wanted to follow up on my previous email regarding how AI-driven analytics can help simplify reporting and improve decision-making.

I understand you may be busy, so I just wanted to briefly check if this is something worth exploring at this stage. We work with small teams to reduce manual effort and provide clearer insights without adding complexity.

If this sounds relevant, I'd be happy to share more or schedule a short call at your convenience.

Best regards,

Sender Name  
Sender Role  
Sender Company

Tone:
- Follow-up 1 → gentle reminder
- Follow-up 2 → final polite check-in
"""

    return structured_email_model.invoke(
        [HumanMessage(content=prompt)]
    )


# ======================================
# CAMPAIGN RUNNER
# ======================================
def run_campaign(app, thread_id: str):
    print("Campaign started")

    while True:
        state = app.invoke(
            {},
            config={"configurable": {"thread_id": thread_id}},
        )

        active = [
            m for m in state.get("monitoring", [])
            if m["monitor_status"] == "active"
        ]

        if not active:
            print("Campaign finished")
            break

        print("Monitoring... next check in 60s")
        time.sleep(60)


# =================================================
# STATE
# =================================================
class LeadState(TypedDict):
    query: str
    companies: List[Dict[str, str]]
    current_company: Dict[str, str]
    site_text: str
    leads: List[Dict[str, Any]]
    qualification: List[Dict[str, Any]]
    emails: List[Dict[str, Any]]
    email_send_logs: List[Dict[str, Any]]
    monitoring: List[Dict[str, Any]]
    active_monitor: Dict[str, Any]
    source: str

    start_from_writer: bool
    phase: str

    human_decision: Dict[str, Any]
    pending_action: str

    sender_profile: Dict[str, str]


# =================================================
# TOOLS
# =================================================
@tool
def apollo_company_search(
    query: str,
    country: str = "India",
    per_page: int = 5
) -> List[Dict[str, Any]]:
    """
    Fetch company leads from Apollo API.
    """
    API_KEY = APOLLO_API_KEY
    url = "https://api.apollo.io/api/v1/organizations/search"

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": API_KEY
    }

    payload = {
        "q_keywords": query,
        "organization_country": country,
        "organization_num_employees_ranges": [
        "51-200",
        "201-500"
        ],

        "organization_is_public": False,

        "page": 1,
        "per_page": per_page
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code != 200:
        return []

    data = resp.json()
    companies = []

    for org in data.get("organizations", []):
        if not org.get("website_url") or not org.get("primary_domain"):
            continue

        companies.append({
            "company_name": org.get("name"),
            "company_website": org.get("website_url"),
            "domain": org.get("primary_domain"),
            "industry": org.get("industry"),
            "estimated_employees": org.get("estimated_num_employees"),
            "keywords": org.get("keywords", []),
            "source": "apollo"
        })

    return companies

@tool
def web_company_search(query: str) -> List[Dict[str, str]]:
    """
    Search the web for real B2B company websites matching the query.
    Filters out media, blogs, directories, and aggregators.
    """
    companies = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=15):
            if r.get("href"):
                domain = urlparse(r["href"]).netloc.lower()
                if (
                    domain
                    and not any(bad in domain for bad in BAD_DOMAINS)
                    and is_real_company_site(domain)
                ):
                    parts = domain.split(".")
                    if len(parts) >= 2:
                        company_key = parts[-2]
                    else:
                        company_key = parts[0]

                    companies.append({
                        "company_name": company_key.replace("-", " ").title(),
                        "company_website": f"https://{domain}",
                        "domain": domain
                    })
    return companies[:5]


@tool
def deep_crawl_site(url: str, max_pages: int = 6) -> str:
    """
    Crawl a company website across internal pages
    and return combined clean text.
    """
    visited: Set[str] = set()
    to_visit = [url]
    base_domain = urlparse(url).netloc
    combined = ""

    while to_visit and len(visited) < max_pages:
        current = to_visit.pop(0)
        if current in visited:
            continue
        visited.add(current)

        try:
            r = requests.get(current, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            for t in soup(["script", "style", "noscript"]):
                t.decompose()
            combined += " " + soup.get_text(" ", strip=True)

            for a in soup.find_all("a", href=True):
                link = urljoin(current, a["href"])
                if urlparse(link).netloc == base_domain:
                    to_visit.append(link)
        except:
            pass

    return combined[:6000]


@tool
def extract_and_validate_emails(text: str, domain: str) -> List[str]:
    """
    Extract emails from website text and validate domain using MX records.
    Falls back to role-based emails if none found.
    """

    parts = domain.lower().split(".")
    if len(parts) >= 2:
        root_domain = parts[-2] + "." + parts[-1]
    else:
        root_domain = domain.lower()

    found = set(re.findall(EMAIL_REGEX, text))
    emails = []

    try:
        dns.resolver.resolve(root_domain, "MX")
    except:
        return []

    for e in found:
        e = e.lower()
        if e.endswith(f"@{root_domain}") and root_domain not in DISPOSABLE_DOMAINS:
            emails.append(e)

    if not emails:
        emails = [f"{p}@{root_domain}" for p in ROLE_PREFIXES]

    return list(set(emails))


@tool
def detect_decision_maker_roles(text: str) -> List[str]:
    """
    Detect decision-maker roles mentioned on the company website.
    Returns roles only (no names).
    """
    roles = [
        "ceo", "cto", "cfo",
        "coo", "founder", "co-founder",
        "director", "head organizer", "vp",
        "vice president"
    ]

    text_lower = text.lower()
    found = []

    for role in roles:
        if role in text_lower:
            found.append(role)

    return list(set(found))


# =================================================
# MODEL WITH TOOLS
# =================================================
tools = [
    apollo_company_search,
    web_company_search,
    deep_crawl_site,
    extract_and_validate_emails,
    detect_decision_maker_roles
]
model_with_tools = model.bind_tools(tools)


# =================================================
# NODES
# =================================================
def human_sender_profile_node(state: LeadState) -> LeadState:
    if state.get("sender_profile"):
        return state 

    return state


def planner_node(state: LeadState) -> LeadState:
    if state.get("phase") == "monitor":
        return state
    if state.get("start_from_writer"):
        return state

    apollo_results = apollo_company_search.invoke({
        "query": state["query"]
    })

    if apollo_results:
        state["companies"] = apollo_results
        state["source"] = "apollo"
        return state

    web_results = web_company_search.invoke({
        "query": state["query"]
    })

    state["companies"] = web_results
    state["source"] = "web"
    return state


def research_node(state: LeadState) -> LeadState:
    """Research ALL companies before moving to qualifier"""
    if state.get("phase") == "monitor":
        return state
    if state.get("start_from_writer"):
        return state

    while state["companies"]:
        company = state["companies"].pop(0)

        site_text = deep_crawl_site.invoke(company["company_website"])

        emails = extract_and_validate_emails.invoke({
            "text": site_text,
            "domain": company["domain"]
        })

        decision_maker_roles = detect_decision_maker_roles.invoke(site_text)

        industry = company.get("industry", "unknown")

        company_size = normalize_company_size(
            company.get("estimated_employees")
        )

        intent_signals = map_keywords_to_intent(
            company.get("keywords", [])
        )

        pain_points = []

        prompt = f"""
Extract business facts ONLY from text.
DO NOT invent names for decision_makers.
Try to fill the intent_signals & pain_points field with help of text.
IF intent_signals:
  - Add short phrases ONLY if supported by phrases in the TEXT
    (e.g. "ai platform", "enterprise software", "automation solution"
  - If no clear signals exist, return unknown.
IF pain_points:
  - Add short phrases ONLY if supported by phrases in the TEXT
  - If no pain points are mentioned, return unknown.

Return JSON ONLY.

{{
  "industry": "ai | saas | fintech | ecommerce | other | health-care",
  "company_size": "small | medium | large | unknown",
  "intent_signals": [],
  "pain_points": []
}}

TEXT:
{site_text[:3500]}
"""

        response = model.invoke([HumanMessage(content=prompt)])
        raw = response.content.replace("```", "").replace("json", "").strip()


        try:
            enriched = json.loads(raw)
            industry = normalize_industry(
                enriched.get("industry", industry)
            )

            company_size = normalize_company_size_llm(
                enriched.get("company_size", company_size)
            )
            pain_points = enriched.get("pain_points", [])

            if not intent_signals:
                intent_signals = enriched.get("intent_signals", [])

        except:
            pain_points = []


        summary_prompt = f"""
Summarize the following company website text in a clear, descriptive, business-focused way.
Do NOT say "Here is", "Summary:", or similar phrases.
You must return ONLY the summary text.

Rules:
- Use ONLY the provided text
- Do NOT add assumptions
- Do NOT add opinions
- Do NOT invent products or services
- Write 4–6 concise sentences
- Focus on: what the company does, who it serves, and key offerings

TEXT:
{site_text[:3000]}
"""

        summary_response = model.invoke(
            [HumanMessage(content=summary_prompt)]
        )

        website_summary = summary_response.content.strip()


        email_quality = get_email_quality(emails)

        intent_confidence = get_intent_confidence(intent_signals)

        research_confidence = calculate_research_confidence(
            industry=industry,
            company_size=company_size,
            emails=emails,
            people=decision_maker_roles,
            intent_signals=intent_signals
        )

        state["leads"].append({
            "company_name": company["company_name"],
            "company_website": company["company_website"],
            "domain": company["domain"],

            "industry": industry,
            "company_size": company_size,

            "intent_signals": intent_signals,
            "intent_confidence": intent_confidence,

            "pain_points": pain_points,

            "decision_makers": decision_maker_roles,

            "validated_emails": emails,
            "email_quality": email_quality,

            "website_summary": website_summary,
            "website_text_sample": site_text[:900],

            "research_confidence": research_confidence,

            "source": company.get("source", state.get("source", "web")),
        })

    return state


def qualifier_node(state: LeadState) -> LeadState:
    """
    Rule-based qualification of researched leads.
    """
    if state.get("phase") == "monitor":
        return state
    if state.get("start_from_writer"):
        return state

    qualified_results = []

    for lead in state["leads"]:
        score = 0
        reasons = []

        if lead["industry"] in ICP_CONFIG["industries"]:
            score += 25
            reasons.append("Industry matches ICP")

        if lead["company_size"] in ICP_CONFIG["company_sizes"]:
            score += 20
            reasons.append("Company size matches ICP")

        if lead.get("decision_makers"):
            score += 20
            reasons.append("Decision-maker role found")

        if lead["email_quality"] == "personal":
            score += 15
            reasons.append("Personal email found")
        elif lead["email_quality"] == "role_based":
            score += 10
            reasons.append("Role-based email found")

        if lead["intent_confidence"] == "high":
            score += 20
            reasons.append("High intent detected")
        elif lead["intent_confidence"] == "medium":
            score += 10
            reasons.append("Medium intent detected")

        qualified_results.append({
            "company_name": lead["company_name"],
            "domain": lead["domain"],
            "qualification_score": score,
            "qualified": score >= ICP_CONFIG["min_score"],
            "qualification_reason": reasons
        })

    state["qualification"] = qualified_results

    return state

def qualifier_router(state: LeadState):
    """Only go to writer if any lead has score ≥ 70"""
    if state.get("start_from_writer"):
        return "writer"
    for q in state["qualification"]:
        if q["qualified"]:
            return "writer"
    return END


def writer_node(state: LeadState) -> LeadState:
    """
    Writes outreach emails ONLY for qualified leads
    using schema-enforced structured output.
    """
    if state.get("phase") == "monitor":
        return state

    emails_to_send = []

    for q in state["qualification"]:
        if not q["qualified"]:
            continue

        lead = next(
            (l for l in state["leads"] if l["company_name"] == q["company_name"]),
            None
        )
        if not lead:
            continue

        sender = state["sender_profile"]

        prompt = f"""
Write a short, professional B2B cold email.

Rules:
- No emojis
- No hype
- No placeholders like [Your Name] or [Recipient]
- Plain text only
- 100 - 200 words
- Mention company context naturally
- Clear, soft CTA
- Professional tone
- Must have 3-4 paragraph


Sender Information:
- Name: {sender["sender_name"]}
- Role: {sender["sender_role"]}
- Company: {sender["company_name"]}
- What we do: {sender["company_description"]}

Example:
Hi {lead["company_name"]},\n\n

Dear Recipient, I came across Test AI Corp and was impressed by your company's commitment to leveraging AI for business growth.

As a small business owner, I'm sure you're aware of the challenges that come with manual reporting and slow decision-making. Our AI-based analytics solutions can help automate these processes, freeing up your time to focus on what matters most. If you're interested in learning more about how our platform can benefit your business,

I'd be happy to schedule a call to discuss further.

Best regards,\n\n
Sender Name
Sender Role
sender company

Company Summary:
{lead["website_summary"]}

Pain Points:
{lead["pain_points"]}

Intent Signals:
{lead["intent_signals"]}
"""

        email_draft: EmailDraft = structured_email_model.invoke(
            [HumanMessage(content=prompt)]
        )

        for email_addr in lead["validated_emails"]:
            emails_to_send.append({
                "company_name": lead["company_name"],
                "email": email_addr,
                "email_subject": email_draft.subject,
                "email_body": email_draft.body
            })

    state["emails"] = emails_to_send
    return state



def sender_node(state: LeadState) -> LeadState:
    """
    Sender Agent: Sends emails and logs Message-IDs for monitoring.
    """
    if state.get("phase") == "monitor":
        return state

    sent_logs = []

    with smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"]) as server:
        server.starttls()
        server.login(
            SMTP_CONFIG["username"],
            SMTP_CONFIG["password"]
        )

        for item in state.get("emails", []):
            try:
                msg = MIMEMultipart()

                msg["From"] = f'{SMTP_CONFIG["from_name"]} <{SMTP_CONFIG["username"]}>'
                msg["To"] = item["email"]
                msg["Subject"] = item["email_subject"]

                message_id = make_msgid()
                msg["Message-ID"] = message_id

                msg.attach(MIMEText(item["email_body"], "plain"))

                server.send_message(msg)

                sent_logs.append({
                    "company_name": item["company_name"],
                    "email": item["email"],
                    "message_id": message_id,
                    "status": "sent",
                    "sent_at": datetime.utcnow().isoformat()
                })

            except Exception as e:
                sent_logs.append({
                    "company_name": item["company_name"],
                    "email": item["email"],
                    "message_id": message_id,
                    "status": "failed",
                    "error": str(e),
                    "sent_at": datetime.utcnow().isoformat()
                })

    state["email_send_logs"] = sent_logs

    now = datetime.now(timezone.utc).isoformat()

    state["monitoring"] = []

    for log in state["email_send_logs"]:
        if log["status"] != "sent":
            continue

        state["monitoring"].append({
            "company_name": log["company_name"],
            "email": log["email"],
            "message_id": log["message_id"],

            "monitor_started_at": now,
            "last_checked_at": None,

            "reply_received": False,
            "meeting_scheduled": False, 

            "followup_1_sent": False,
            "followup_2_sent": False,

            "monitor_status": "active"
        })

    state["phase"] = "monitor"
    return state

def human_send_approval_node(state: LeadState) -> LeadState:
    """
    Pause graph and wait for human input:
    send_first_email: yes / no
    """
    # If decision already exists, just continue
    if state.get("human_decision", {}).get("send_first_email") is not None:
        return state

    return state

def human_send_router(state: LeadState):
    decision = state["human_decision"].get("send_first_email")
    if decision == "yes":
        return "sender"
    return END


from datetime import datetime, timezone

def monitor_node(state: LeadState) -> LeadState:
    now = datetime.now(timezone.utc)

    for m in state["monitoring"]:
        if m["monitor_status"] != "active":
            continue

        start = datetime.fromisoformat(m["monitor_started_at"])
        elapsed = (now - start).total_seconds()

        if not m["reply_received"]:
            if check_reply_for_message_id(m["message_id"]):
                m["reply_received"] = True
                m["last_checked_at"] = now.isoformat()
                state["active_monitor"] = m
                return state

        if elapsed >= 60 and not m["followup_1_sent"]:
            state["active_monitor"] = m
            return state

        if elapsed >= 420 and not m["followup_2_sent"]:
            state["active_monitor"] = m
            return state

        if elapsed >= 600:
            m["monitor_status"] = "expired"

    state["active_monitor"] = {}
    return state


def human_meeting_decision_node(state: LeadState) -> LeadState:
    m = state["active_monitor"]

    if not m:
        return state

    if state["human_decision"].get("send_meeting_email") is not None:
        return state

    return state

def human_meeting_router(state: LeadState):
    if state["human_decision"].get("send_meeting_email") == "yes":
        return "meeting"
    return "monitor"


def followup_node(state: LeadState) -> LeadState:
    m = state["active_monitor"]

    lead = next(
        (l for l in state["leads"] if l["company_name"] == m["company_name"]),
        {}
    )

    followup_no = 1 if not m["followup_1_sent"] else 2

    draft = generate_followup_email(lead, followup_no, state["sender_profile"])

    with smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"]) as server:
        server.starttls()
        server.login(
            SMTP_CONFIG["username"],
            SMTP_CONFIG["password"]
        )

        msg = MIMEMultipart()
        msg["From"] = f'{SMTP_CONFIG["from_name"]} <{SMTP_CONFIG["username"]}>'
        msg["To"] = m["email"]
        msg["Subject"] = draft.subject

        msg.attach(MIMEText(draft.body, "plain"))

        server.send_message(msg)

    if not m["followup_1_sent"]:
        m["followup_1_sent"] = True
    else:
        m["followup_2_sent"] = True

    state["active_monitor"] = {}
    return state



from datetime import datetime, timedelta
import uuid

def meeting_node(state: LeadState) -> LeadState:
    m = state["active_monitor"]

    meeting_dt_str = state["human_decision"].get("meeting_datetime")
    if not meeting_dt_str:
        return state

    # Convert "YYYY-MM-DD HH:MM" → datetime
    start_dt = datetime.strptime(meeting_dt_str, "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(minutes=30)

    service = get_calendar_service()

    event = {
        "summary": f"Meeting with {m['company_name']}",
        "description": "Automated meeting created by B2B outreach system",
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid.uuid4())
            }
        },
        "attendees": [
            {"email": m["email"]}
        ]
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1,
        sendUpdates="all"
    ).execute()

    meet_link = created_event["conferenceData"]["entryPoints"][0]["uri"]

    m["meet_link"] = meet_link
    m["calendar_event_id"] = created_event["id"]
    m["monitor_status"] = "meeting_created"
    m["meeting_scheduled"] = True

    state["active_monitor"] = {}
    return state



# =================================================
# GRAPH
# =================================================
graph = StateGraph(LeadState)

graph.add_node("human_sender_profile", human_sender_profile_node)
graph.add_node("planner", planner_node)
graph.add_node("research", research_node)
graph.add_node("qualifier", qualifier_node)
graph.add_node("writer", writer_node)
graph.add_node("human_send_approval", human_send_approval_node)
graph.add_node("sender", sender_node)
graph.add_node("monitor", monitor_node)
graph.add_node("human_meeting", human_meeting_decision_node)
graph.add_node("followup", followup_node)
graph.add_node("meeting", meeting_node)

graph.set_entry_point("human_sender_profile")

graph.add_edge("human_sender_profile", "planner")
graph.add_edge("planner", "research")
graph.add_edge("research", "qualifier")
graph.add_conditional_edges("qualifier", qualifier_router, {"writer": "writer", END: END})
graph.add_edge("writer", "human_send_approval")

graph.add_conditional_edges(
    "human_send_approval",
    human_send_router,
    {
        "sender": "sender",
        END: END
    }
)

graph.add_conditional_edges(
    "human_meeting",
    human_meeting_router,
    {
        "meeting": "meeting",
        "monitor": "monitor"
    }
)

graph.add_edge("sender", "monitor")
graph.add_conditional_edges(
    "monitor",
    lambda s: (
        "meeting"
        if s.get("active_monitor", {}).get("reply_received")
        else "followup"
        if s.get("active_monitor")
        else END
    ),
    {
        "meeting": "human_meeting",
        "followup": "followup",
        END: END,
    },
)

graph.add_edge("followup", "monitor")
graph.add_edge("meeting", "monitor")


# Create the LangGraph application
app = graph.compile(checkpointer=checkpointer)

# =================================================
# Utility functions for API
# =================================================
def create_test_state(query: str, sender_profile: Dict[str, str]) -> LeadState:
    """Create a test state for test mode"""
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc).isoformat()

    return {
        "start_from_writer": True,
        "phase": "campaign",

        "query": query,
        "companies": [],
        "site_text": "",
        "source": "test",

        "leads": [
            {
                "company_name": "Test AI Corp",
                "company_website": "https://testai.example",
                "domain": "testai.example",

                "industry": "ai",
                "company_size": "small",

                "intent_signals": ["ai platform"],
                "intent_confidence": "high",

                "pain_points": ["manual reporting", "slow decision making"],

                "decision_makers": ["cto"],

                "validated_emails": [
                    "morning444night@gmail.com"
                ],
                "email_quality": "personal",

                "website_summary": (
                    "Test AI Corp provides AI-based analytics solutions "
                    "to help small businesses automate decision-making."
                ),
                "website_text_sample": "dummy",

                "research_confidence": 1.0,
                "source": "test"
            }
        ],

        "qualification": [
            {
                "company_name": "Test AI Corp",
                "domain": "testai.example",
                "qualification_score": 95,
                "qualified": True,
                "qualification_reason": ["TEST MODE"]
            }
        ],

        "emails": [],
        "email_send_logs": [],
        "monitoring": [],
        "active_monitor": {},
        "current_company": {},
        "human_decision": {},
        "sender_profile": sender_profile
    }