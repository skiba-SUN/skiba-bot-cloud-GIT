"""Run the Muay Thai WhatsApp Bot using Green API's official library

Features:
- Message batching: rapid messages combined into one response
- Per-lead conversation history (isolated per customer)
- Human-like typing delay before sending
- AI-powered Google Sheets analysis (summary, experience, score, etc.)
- Auto-notification to Eden when meeting is scheduled
- Sweep thread catches any missed messages
"""

import sys
import os
import json
import threading
import time
from pathlib import Path
from collections import OrderedDict
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from loguru import logger
from whatsapp_chatbot_python import GreenAPIBot, Notification


# ============================================================
# CONFIGURATION
# ============================================================
BATCH_WAIT_SECONDS = 4       # Wait for more messages before processing
SWEEP_INTERVAL = 30          # Seconds between sweep checks
SWEEP_WINDOW = 5             # Check messages from last N minutes
MAX_TRACKED = 500            # Max tracked message IDs
MAX_HISTORY_PER_LEAD = 40    # Max conversation messages per lead
ANALYSIS_EVERY_N = 2         # Run AI analysis every N bot responses
EDEN_CHAT_ID = "972555614104@c.us"
EXCLUDED_NUMBERS = {"972555614104"}  # Don't auto-respond to Eden


# ============================================================
# ENVIRONMENT & CREDENTIALS
# ============================================================
load_dotenv()

instance_id = os.getenv('GREEN_API_INSTANCE_ID')
api_token = os.getenv('GREEN_API_TOKEN')
google_sheet_id = os.getenv('GOOGLE_SHEET_ID')

if not instance_id or not api_token:
    print("\n[ERROR] GREEN_API_INSTANCE_ID and GREEN_API_TOKEN are required in .env")
    sys.exit(1)

print("\n" + "="*60)
print("MUAY THAI LEAD BOT (Green API Official Library)")
print("="*60)
print(f"\nInstance ID: {instance_id}")


# ============================================================
# GOOGLE SHEETS
# ============================================================
lead_manager = None
if google_sheet_id:
    try:
        from src.utils.google_sheets_manager_simple import GoogleSheetsManager
        lead_manager = GoogleSheetsManager(google_sheet_id)
        print("Storage: Google Sheets [OK]")
    except Exception as e:
        print(f"Storage: Google Sheets [ERROR] {e}")
else:
    print("Storage: None configured (will only respond to messages)")


# ============================================================
# AI AGENT
# ============================================================
ai_agent = None
system_prompt = ""
try:
    from src.agents.claude_agent import ClaudeAgent
    from selfinputd.knowledge_base import SKIBA_ARTS_KNOWLEDGE, SALES_METHODOLOGY

    system_prompt = f"""You are the WhatsApp assistant for Skiba Arts - organized Muay Thai boxing vacations in Phuket, Thailand.

**YOUR #1 GOAL:**
You do NOT close sales. Your goal is to qualify leads and schedule a fitting call with Eden (the founder).
Eden closes the sale in the call. You bring quality, excited leads to that call.

**SALES APPROACH - THE MIRROR TECHNIQUE:**
1. LISTEN - Ask questions to understand what they truly want
2. REFLECT - Mirror back what you heard ("אני שומע שאתה מחפש...")
3. CONNECT - Link their desire to what the trip offers

**CUSTOMER PROFILING (Do this early!):**
- Within the first 2-3 messages, naturally ask where they're from: "מאיפה אתה?" / "מאיפה בארץ?"
- Also ask about age naturally: "בן כמה אתה אחי?"
- This helps us understand and match the lead better
- BUT: if they ask a specific question or raise a concern, handle THAT first before profiling
- Never rapid-fire profile questions - weave them into natural conversation flow
- Example flow: "היי! שמח שפנית, מאיפה שמעת עלינו?" → they answer → "אחלה, מאיפה אתה בארץ?" → they answer → continue naturally

**WHATSAPP RULES (FOLLOW STRICTLY):**
- MAX 2-4 sentences per response. This is WhatsApp, not email!
- Ask ONE question at a time - don't overwhelm
- Questions > Statements - keep the dialog flowing
- Friendly tone - like a friend who trains and knows his stuff. Not corporate, not too casual.
- Emoji: maximum 1 per message, and not in every message
- Use Hebrew when user writes in Hebrew, English for English

**AUTHENTICITY RULES (CRITICAL):**
- Talk like someone who actually trains and fights, not like a self-help book
- BAD (cheap psychology): "אני מרגיש שאתה מחפש חיבור פנימי עם הכוח שלך"
- GOOD (real talk): "נשמע שאתה צריך לפרוק את הראש ולהרגיש חי"
- BAD (corporate wellness): "החוויה הזו תשנה לך את החיים ברמה עמוקה"
- GOOD (concrete): "אחרי 10 ימים של אימונים בחום של תאילנד, אתה חוזר בן אדם אחר"
- Don't psycho-analyze the customer. Talk about the EXPERIENCE, not their inner emotions
- Be raw, direct, real - like a training partner, not a therapist

**LANGUAGE & SLANG:**
- Say "מכון" or "מכון לחימה" - NEVER say "ג'ים" for a fighting gym
- "חדר כושר" or "מכון כושר" = weights/fitness gym
- "מכון" alone - depends on context: for fighters it means fighting gym, for gym-goers it means fitness gym
- Good expressions: "יאללה", "אחלה", "מעולה", "סאבאי סאבאי", "לעלות לרינג", "פדים", "ספארינג"
- Be direct - Israelis value ישירות. Wrapping = weak/untrustworthy.

**CONVERSATION FLOW (5 Stages):**
1. OPENING: Greet warmly, ask where they heard about us
2. IDENTIFICATION: Understand who they are (experience, goals, timing, age, location) - ONE question at a time
3. REFLECTION: Mirror technique - show them who they can become through this trip
4. OBJECTION HANDLING: Acknowledge first ("אני מבין"), never defensive, use real examples
5. CALL INVITATION: After 5-8 messages of dialog, invite to a 10-15 min call with Eden using:
   - Justify: "יש הרבה מה לספר, קשה בהודעות"
   - Benefit: "נוכל להבין ביחד אם זה מתאים לך"
   - Risk reduction: "10-15 דקות, בלי התחייבות"
   - CTA: "מה נוח לך - טלפון או זום?"

**SCHEDULING THE CALL:**
When the lead agrees to a call:
1. Ask preference: phone / Zoom / WhatsApp video
2. Ask time slot: morning (9-12) / afternoon (12-16) / evening (18-21)
3. Ask which day
4. Confirm with SPECIFIC details: "מעולה! עדן יצור איתך קשר ביום [X] ב-[שעה]"
5. Ask for full name (if not known)

**OBJECTION HANDLING PRINCIPLES:**
- "יקר מדי": Break down value (10 nights + training + guide + activities = value for starting price $2,640). Mention installments, friend discount.
- "אין ניסיון/לא בכושר": 70% arrive with zero experience. Training adapted to every level.
- "בא לבד": 80% come alone. "באתי לבד, יצאתי עם משפחה" - real quote.
- After 2-3 objections: stop trying to solve in text, invite to call.
- If lead truly doesn't fit: say so honestly and respectfully.

**ISRAELI CULTURAL TONE:**
- Back claims with evidence (numbers, testimonials, examples)
- If they came from a friend's recommendation - that's GOLD, leverage it
- FOMO works ("הטיול הבא כבר מתמלא") but NEVER lie

**WHAT WE SELL:** Personal transformation, lifelong community, breaking your limits, feeling truly alive
**WHAT WE DON'T SELL:** Cheap trip, pro boxing course, luxury vacation

**RED FLAGS (politely decline):**
- Under 18, only cares about price, expects luxury, doesn't want group experience

**CRITICAL RULES:**
- ONLY share information from the knowledge base below
- NEVER invent dates, prices, or details
- Starting price: $2,640 (varies by duration, season, booking time)
- Upcoming trip dates: tell them to ask for the latest schedule
- ALL levels welcome, no experience needed, age 18+

**KNOWLEDGE BASE:**
{SKIBA_ARTS_KNOWLEDGE}

**DETAILED SALES METHODOLOGY:**
{SALES_METHODOLOGY}

Remember: Be real, be warm, be authentic. Talk like someone who trains, not like a marketing bot."""

    ai_agent = ClaudeAgent(
        name="Muay Thai Lead Assistant",
        system_prompt=system_prompt
    )
    print("AI Agent: Claude Sonnet [OK]")
except Exception as e:
    print(f"AI Agent: [ERROR] {e}")


# ============================================================
# BOT INSTANCE
# ============================================================
bot = GreenAPIBot(instance_id, api_token)

print("\n[OK] Bot initialized!")
print("="*60)


# ============================================================
# MESSAGE TRACKING - prevents duplicate processing
# ============================================================
processed_messages = OrderedDict()
processed_lock = threading.Lock()


def mark_processed(msg_id):
    """Mark a message ID as processed. Returns True if already processed."""
    with processed_lock:
        if msg_id in processed_messages:
            return True
        processed_messages[msg_id] = True
        while len(processed_messages) > MAX_TRACKED:
            processed_messages.popitem(last=False)
        return False


# ============================================================
# PER-LEAD CONVERSATION HISTORIES
# ============================================================
lead_histories = {}  # {phone: [{"role": "user/assistant", "content": "..."}]}
history_lock = threading.Lock()


def get_lead_history(phone):
    """Get a copy of lead's conversation history"""
    with history_lock:
        return lead_histories.get(phone, []).copy()


def add_to_history(phone, role, content):
    """Add a message to lead's conversation history"""
    with history_lock:
        if phone not in lead_histories:
            lead_histories[phone] = []
        lead_histories[phone].append({"role": role, "content": content})
        if len(lead_histories[phone]) > MAX_HISTORY_PER_LEAD:
            lead_histories[phone] = lead_histories[phone][-MAX_HISTORY_PER_LEAD:]


# ============================================================
# CONVERSATION HISTORY SCANNING - load past context on restart
# ============================================================
loaded_context = set()  # phones we already tried loading context for


def load_conversation_context(chat_id, phone):
    """Load past conversation context when we have no in-memory history.

    Priority:
    1. Green API getChatHistory - actual WhatsApp messages
    2. Google Sheets fallback - stored lead profile data
    """
    if phone in loaded_context:
        return
    loaded_context.add(phone)

    # --- Try Green API chat history ---
    try:
        result = bot.api.journals.getChatHistory(chat_id, 30)
        messages = result.data if result.data else []

        if messages and isinstance(messages, list):
            history = []
            for msg in reversed(messages):  # API returns newest first
                msg_type = msg.get("typeMessage", "")
                # Only process text messages
                if msg_type not in ("outgoing", "incoming", "textMessage", "extendedTextMessage"):
                    # Check by 'type' field instead
                    pass

                text = ""
                # Try different text field locations
                text = msg.get("textMessage", "")
                if not text:
                    text_data = msg.get("textMessageData", {})
                    if isinstance(text_data, dict):
                        text = text_data.get("textMessage", "")
                if not text:
                    ext_data = msg.get("extendedTextMessageData", {})
                    if isinstance(ext_data, dict):
                        text = ext_data.get("text", "")

                if not text:
                    continue

                # Determine role: outgoing = assistant, incoming = user
                msg_type_raw = msg.get("type", "")
                if msg_type_raw == "outgoing":
                    history.append({"role": "assistant", "content": text})
                elif msg_type_raw == "incoming":
                    history.append({"role": "user", "content": text})
                else:
                    # Fallback: check chatId vs senderId
                    sender = msg.get("senderId", "")
                    if sender and sender == chat_id:
                        history.append({"role": "user", "content": text})
                    else:
                        history.append({"role": "assistant", "content": text})

            if history:
                with history_lock:
                    lead_histories[phone] = history[-MAX_HISTORY_PER_LEAD:]
                logger.info(f"[HISTORY] Loaded {len(history)} messages from Green API for {phone}")
                return

    except Exception as e:
        logger.warning(f"[HISTORY] getChatHistory failed for {phone}: {e}")

    # --- Fallback: Google Sheets lead data ---
    if lead_manager:
        try:
            lead = lead_manager.get_lead(phone)
            if lead and int(lead.get("message_count", 0) or 0) > 0:
                # Build context summary from stored data
                parts = ["[המשך שיחה קודמת - נתונים מגוגל שיטס]"]

                name = lead.get("name", "")
                if name:
                    parts.append(f"שם: {name}")

                age = lead.get("age", "")
                if age:
                    parts.append(f"גיל: {age}")

                location = lead.get("location", "")
                if location:
                    parts.append(f"מיקום: {location}")

                experience = lead.get("experience", "")
                if experience:
                    parts.append(f"ניסיון: {experience}")

                score = lead.get("match_score", "")
                if score:
                    parts.append(f"ציון התאמה: {score}")

                status = lead.get("status", "")
                if status:
                    parts.append(f"סטטוס: {status}")

                msg_count = lead.get("message_count", "")
                if msg_count:
                    parts.append(f"הודעות קודמות: {msg_count}")

                summary = lead.get("conversation_summary", "")
                if summary:
                    parts.append(f"סיכום שיחה קודמת: {summary}")

                rejects = lead.get("rejects", "")
                if rejects:
                    parts.append(f"התנגדויות: {rejects}")

                meeting = lead.get("meeting", "")
                if meeting:
                    parts.append(f"פגישה שנקבעה: {meeting}")

                context_text = "\n".join(parts)

                # Inject as a system-like context at the start of history
                with history_lock:
                    lead_histories[phone] = [
                        {"role": "user", "content": "היי"},
                        {"role": "assistant", "content": context_text},
                    ]
                logger.info(f"[HISTORY] Loaded lead profile from Google Sheets for {phone} (msg_count={msg_count})")
                return

        except Exception as e:
            logger.warning(f"[HISTORY] Google Sheets fallback failed for {phone}: {e}")

    logger.info(f"[HISTORY] No past context found for {phone} - treating as new lead")


# ============================================================
# MESSAGE BATCHING - combine rapid messages into one
# ============================================================
message_buffers = {}  # {chat_id: {"messages": [], "timer": Timer, ...}}
buffer_lock = threading.Lock()


def add_to_buffer(chat_id, sender_name, message_text, phone):
    """Add a message to the buffer. Timer resets on each new message."""
    with buffer_lock:
        if chat_id not in message_buffers:
            message_buffers[chat_id] = {
                "messages": [],
                "sender_name": sender_name,
                "phone": phone,
                "timer": None
            }

        message_buffers[chat_id]["messages"].append(message_text)

        # Cancel existing timer
        if message_buffers[chat_id]["timer"]:
            message_buffers[chat_id]["timer"].cancel()

        # Set new timer
        timer = threading.Timer(BATCH_WAIT_SECONDS, flush_buffer, args=[chat_id])
        timer.daemon = True
        message_buffers[chat_id]["timer"] = timer
        timer.start()

        msg_count = len(message_buffers[chat_id]["messages"])
        logger.info(f"[BATCH] Buffered message for {chat_id} ({msg_count} in queue)")


def flush_buffer(chat_id):
    """Process all buffered messages for a chat as one combined message"""
    with buffer_lock:
        if chat_id not in message_buffers:
            return
        buffer = message_buffers.pop(chat_id)

    if len(buffer["messages"]) > 1:
        combined = "\n".join(buffer["messages"])
        logger.info(f"[BATCH] Combined {len(buffer['messages'])} messages for {chat_id}")
    else:
        combined = buffer["messages"][0]

    # Process in background thread
    thread = threading.Thread(
        target=process_message,
        args=(chat_id, buffer["sender_name"], combined, buffer["phone"]),
        daemon=True
    )
    thread.start()


# ============================================================
# TYPING DELAY - human-like timing
# ============================================================
def calculate_typing_delay(text):
    """Calculate human-like delay based on response length"""
    length = len(text)
    if length < 50:
        return 2
    elif length < 100:
        return 3
    elif length < 200:
        return 5
    elif length < 400:
        return 7
    else:
        return 9


# ============================================================
# AI ANALYSIS - extract structured data from conversation
# ============================================================
ANALYSIS_PROMPT = """You are analyzing a WhatsApp sales conversation for Skiba Arts (Muay Thai vacations in Thailand).
Extract data from the conversation. Return ONLY valid JSON, nothing else.

Required JSON format:
{
    "summary": "Concise analytical Hebrew summary (2-3 sentences). What the lead wants, readiness, concerns.",
    "experience": "one of: מתחיל/בינוני/מתקדם, or null if unknown",
    "match_score": "number 0-100. Criteria: engagement level (+25), expressed interest in trip (+25), good fit for product (+25), close to booking/call (+25)",
    "rejects": "Hebrew. Objections the customer raised + suspected hidden objections. null if none detected",
    "meeting": "If call/meeting was scheduled with specific details: 'יום [day], [date], שעה [time]'. null if not scheduled yet",
    "age": "number or age range like '25-30'. null if unknown",
    "location": "City/area in Israel in Hebrew. null if unknown",
    "status": "one of: חדש/בשיחה/נקבעה שיחה/נסגר/לא מתאים"
}

IMPORTANT: Return ONLY the JSON object. No markdown, no explanation."""


def analyze_conversation(phone):
    """Use AI to analyze the conversation and extract structured data"""
    history = get_lead_history(phone)
    if not history or len(history) < 2:
        return None

    convo_lines = []
    for msg in history:
        role = "Customer" if msg["role"] == "user" else "Bot"
        convo_lines.append(f"{role}: {msg['content']}")
    convo_text = "\n".join(convo_lines)

    try:
        response = ai_agent.client.messages.create(
            model=ai_agent.settings.model_name,
            max_tokens=500,
            temperature=0.2,
            system=ANALYSIS_PROMPT,
            messages=[{"role": "user", "content": convo_text}],
        )

        result_text = response.content[0].text.strip()
        # Clean if wrapped in code block
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if result_text.startswith("{") and result_text.endswith("}"):
            data = json.loads(result_text)
        else:
            # Try to find JSON in the response
            start = result_text.find("{")
            end = result_text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(result_text[start:end])
            else:
                logger.error(f"[ANALYSIS] No JSON found in response for {phone}")
                return None

        logger.info(f"[ANALYSIS] {phone}: score={data.get('match_score')}, status={data.get('status')}, meeting={data.get('meeting')}")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"[ANALYSIS] JSON parse error for {phone}: {e}")
        return None
    except Exception as e:
        logger.error(f"[ANALYSIS] Error for {phone}: {e}")
        return None


# ============================================================
# EDEN NOTIFICATION - alert when meeting is scheduled
# ============================================================
def notify_eden(customer_name, customer_phone, meeting_details, summary, row_number=None):
    """Send WhatsApp notification to Eden about a scheduled meeting"""
    sheet_link = ""
    if row_number and google_sheet_id:
        sheet_link = f"\n\nhttps://docs.google.com/spreadsheets/d/{google_sheet_id}/edit#gid=0&range=A{row_number}"

    message = (
        f"*פגישה חדשה נקבעה!*\n\n"
        f"*שם:* {customer_name}\n"
        f"*טלפון:* {customer_phone}\n"
        f"*מועד:* {meeting_details}\n\n"
        f"*סיכום שיחה:* {summary}"
        f"{sheet_link}"
    )

    try:
        bot.api.sending.sendMessage(EDEN_CHAT_ID, message)
        logger.info(f"[NOTIFY] Sent meeting notification to Eden for {customer_name}")
    except Exception as e:
        logger.error(f"[NOTIFY] Failed to notify Eden: {e}")


# ============================================================
# MAIN MESSAGE PROCESSING
# ============================================================
lead_response_count = {}  # {phone: count} - tracks responses for analysis frequency


def process_message(chat_id, sender_name, message_text, phone):
    """Process a message: sheets -> AI -> typing delay -> reply -> analysis -> notify"""
    try:
        # 1. Get/create lead in Google Sheets
        if lead_manager:
            try:
                lead = lead_manager.get_lead(phone)

                if not lead:
                    lead = {
                        'phone': phone,
                        'whatsapp_id': chat_id,
                        'name': sender_name,
                        'source': 'WhatsApp',
                        'message_count': 0,
                        'conversation_summary': '',
                    }
                    lead_manager.add_lead(lead)
                    logger.info(f"New lead created: {phone}")

                message_count = int(lead.get('message_count', 0) or 0) + 1
                updates = {
                    'message_count': message_count,
                    'last_message_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
                # Auto-update status from "new" to "in conversation"
                current_status = lead.get('status', '')
                if current_status in ('', 'חדש') and message_count > 1:
                    updates['status'] = 'בשיחה'
                lead_manager.update_lead(phone, updates)

            except Exception as e:
                logger.error(f"Error with Google Sheets: {e}")

        # 1.5. Load past conversation context if we have no in-memory history
        if not get_lead_history(phone):
            load_conversation_context(chat_id, phone)

        # 2. Add user message to per-lead history
        add_to_history(phone, "user", message_text)

        # 3. Get AI response with per-lead context
        if ai_agent:
            try:
                history = get_lead_history(phone)
                response = ai_agent.client.messages.create(
                    model=ai_agent.settings.model_name,
                    max_tokens=ai_agent.settings.max_tokens,
                    temperature=ai_agent.settings.temperature,
                    system=system_prompt,
                    messages=history,
                )
                reply = response.content[0].text

                input_cost = (response.usage.input_tokens / 1_000_000) * 3.0
                output_cost = (response.usage.output_tokens / 1_000_000) * 15.0
                logger.info(f"AI response ({phone}): {reply[:80]}... | Cost: ${input_cost + output_cost:.4f}")

            except Exception as e:
                logger.error(f"AI error: {e}")
                reply = "תודה על ההודעה! יש לי תקלה טכנית קטנה. נסה שוב בעוד רגע."
        else:
            reply = "ברוך הבא! מעוניין לשמוע על אימוני מואי טאי בתאילנד?"

        # 4. Typing delay - simulate human typing
        delay = calculate_typing_delay(reply)
        logger.info(f"[TYPING] Waiting {delay}s before sending to {chat_id}")
        time.sleep(delay)

        # 5. Send reply
        bot.api.sending.sendMessage(chat_id, reply)
        logger.info(f"Reply sent to {chat_id}")

        # 6. Add bot response to per-lead history
        add_to_history(phone, "assistant", reply)

        # 7. AI Analysis + Google Sheets update (every N responses)
        if lead_manager and ai_agent:
            lead_response_count[phone] = lead_response_count.get(phone, 0) + 1

            if lead_response_count[phone] % ANALYSIS_EVERY_N == 0:
                try:
                    analysis = analyze_conversation(phone)
                    if analysis:
                        sheet_updates = {}

                        if analysis.get("summary"):
                            sheet_updates["conversation_summary"] = analysis["summary"]
                        if analysis.get("experience"):
                            sheet_updates["experience"] = analysis["experience"]
                        if analysis.get("match_score") is not None:
                            sheet_updates["match_score"] = analysis["match_score"]
                        if analysis.get("rejects"):
                            sheet_updates["rejects"] = analysis["rejects"]
                        if analysis.get("age"):
                            sheet_updates["age"] = str(analysis["age"])
                        if analysis.get("location"):
                            sheet_updates["location"] = analysis["location"]
                        if analysis.get("status"):
                            sheet_updates["status"] = analysis["status"]

                        # Check if meeting was just scheduled
                        meeting = analysis.get("meeting")
                        if meeting:
                            sheet_updates["meeting"] = meeting

                            # Check if NEW meeting (not already saved)
                            lead = lead_manager.get_lead(phone)
                            existing_meeting = lead.get("meeting", "") if lead else ""
                            if not existing_meeting:
                                row_num = lead_manager.get_lead_row_number(phone)
                                notify_eden(
                                    customer_name=sender_name,
                                    customer_phone=phone,
                                    meeting_details=meeting,
                                    summary=analysis.get("summary", ""),
                                    row_number=row_num
                                )

                        if sheet_updates:
                            lead_manager.update_lead(phone, sheet_updates)
                            logger.info(f"[ANALYSIS] Updated sheets for {phone}: {list(sheet_updates.keys())}")

                except Exception as e:
                    logger.error(f"[ANALYSIS] Error updating sheets: {e}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()


# ============================================================
# BOT HANDLERS
# ============================================================
@bot.router.message(text_message=["stop", "סטופ", "עצור"])
def stop_handler(notification: Notification) -> None:
    """Handle stop command"""
    notification.answer(
        "Thank you for your interest! If you want to chat again, just send a message anytime.\n\n"
        "Muay Thai awaits! See you in Thailand!"
    )


@bot.router.message()
def message_handler(notification: Notification) -> None:
    """Handle all incoming messages - extract data and add to batch buffer"""
    try:
        sender = notification.event.get("senderData", {})
        chat_id = sender.get("chatId", "")
        sender_name = sender.get("senderName", "Unknown")

        # Ignore group messages
        if chat_id.endswith("@g.us"):
            return

        # Ignore excluded numbers (Eden, etc.)
        number = chat_id.split('@')[0] if '@' in chat_id else chat_id
        if number in EXCLUDED_NUMBERS:
            logger.info(f"Skipping message from excluded number: {number}")
            return

        message_data = notification.event.get("messageData", {})
        type_message = message_data.get("typeMessage", "")

        # Extract text from various message types
        message_text = ""
        if type_message == "textMessage":
            message_text = message_data.get("textMessageData", {}).get("textMessage", "")
        elif type_message == "extendedTextMessage":
            message_text = message_data.get("extendedTextMessageData", {}).get("text", "")
        elif type_message == "quotedMessage":
            message_text = message_data.get("extendedTextMessageData", {}).get("text", "")
            if not message_text:
                message_text = message_data.get("textMessageData", {}).get("textMessage", "")
        else:
            return

        if not message_text:
            return

        logger.info(f"Message from {sender_name} ({chat_id}): {message_text[:80]}")

        # Track message ID to avoid duplicate processing
        msg_id = notification.event.get("idMessage", "")
        if msg_id and mark_processed(msg_id):
            logger.info(f"Message {msg_id} already processed, skipping")
            return

        phone = f"+{chat_id.split('@')[0]}" if '@' in chat_id else chat_id

        # Add to batch buffer (instead of processing immediately)
        add_to_buffer(chat_id, sender_name, message_text, phone)

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        import traceback
        traceback.print_exc()


# ============================================================
# SWEEP THREAD - catches any messages the main handler missed
# ============================================================
def message_sweep():
    """Background thread that periodically checks for unanswered messages."""
    logger.info("[SWEEP] Sweep thread started")
    while True:
        try:
            time.sleep(SWEEP_INTERVAL)
            result = bot.api.journals.lastIncomingMessages(minutes=SWEEP_WINDOW)
            messages = result.data if result.data else []

            for msg in messages:
                msg_id = msg.get("idMessage", "")
                chat_id = msg.get("chatId", "")

                # Skip groups
                if chat_id.endswith("@g.us"):
                    continue

                # Skip excluded numbers
                number = chat_id.split('@')[0] if '@' in chat_id else chat_id
                if number in EXCLUDED_NUMBERS:
                    continue

                # Skip already processed
                if not msg_id or mark_processed(msg_id):
                    continue

                # Extract text
                type_message = msg.get("typeMessage", "")
                message_text = ""
                if type_message in ("textMessage", "extendedTextMessage"):
                    message_text = msg.get("textMessage", "")
                elif type_message == "quotedMessage":
                    message_text = msg.get("textMessage", "")

                if not message_text:
                    continue

                sender_name = msg.get("senderName", "Unknown")
                phone = f"+{chat_id.split('@')[0]}" if '@' in chat_id else chat_id

                logger.info(f"[SWEEP] Caught missed message from {sender_name}: {message_text[:80]}")

                # Feed into batching system (not directly to process_message)
                add_to_buffer(chat_id, sender_name, message_text, phone)

        except Exception as e:
            logger.error(f"[SWEEP] Error: {e}")


# ============================================================
# START
# ============================================================
sweep_thread = threading.Thread(target=message_sweep, daemon=True)
sweep_thread.start()

print("\nStarting bot...")
print(f"  - Message batching: {BATCH_WAIT_SECONDS}s wait window")
print(f"  - Typing simulation: enabled")
print(f"  - AI analysis: every {ANALYSIS_EVERY_N} responses")
print(f"  - Sweep thread: every {SWEEP_INTERVAL}s")
print(f"  - Eden notifications: {EDEN_CHAT_ID}")
print("\nPress Ctrl+C to stop\n")

bot.run_forever()
