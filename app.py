import os
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
from openai import OpenAI
from scenarios import SCENARIOS

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    "https://organized-addition-collectables-dom.trycloudflare.com",
).rstrip("/")

CONVERSATIONS = {}
LOW_CONFIDENCE_THRESHOLD = 0.45


def make_gather(scenario, prompt=None):
    profile = get_patient_profile(scenario)
    hints = ",".join(
        [
            profile["name"],
            profile["dob"],
            "appointment",
            "schedule",
            "cancel",
            "reschedule",
            "this Friday",
            "next Friday",
            "date of birth",
        ]
    )
    gather = Gather(
        input="speech",
        action=f"{PUBLIC_BASE_URL}/respond?scenario_id={scenario['id']}",
        method="POST",
        timeout=12,
        speech_timeout=3,
        speech_model="phone_call",
        enhanced=True,
        language="en-US",
        hints=hints,
        action_on_empty_result=True,
    )
    if prompt:
        gather.say(prompt, voice="alice")
    return gather


def get_scenario_by_id(scenario_id):
    for scenario in SCENARIOS:
        if scenario["id"] == scenario_id:
            return scenario
    return SCENARIOS[0]


def get_patient_profile(scenario):
    return {
        "name": scenario.get("patient", "John Smith"),
        "dob": (
            scenario.get("dob")
            or scenario.get("date_of_birth")
            or scenario.get("birthdate")
            or "January 15, 1988"
        ),
        "phone": scenario.get("phone", "555-0134"),
    }


def start_conversation(call_sid, scenario_id):
    scenario = get_scenario_by_id(scenario_id)
    profile = get_patient_profile(scenario)
    CONVERSATIONS[call_sid] = {
        "scenario_id": scenario["id"],
        "profile": profile,
        "history": [],
        "state": {
            "dob_rejected": False,
            "no_today_availability": False,
            "appointment_booked": False,
        },
    }
    return scenario


def get_scenario(call_sid):
    scenario_id = CONVERSATIONS.get(call_sid, {}).get("scenario_id")
    return get_scenario_by_id(scenario_id)


def generate_patient_reply(call_sid, agent_text):
    scenario = get_scenario(call_sid)
    conversation = CONVERSATIONS.setdefault(call_sid, {})
    profile = CONVERSATIONS.setdefault(call_sid, {}).setdefault(
        "profile",
        get_patient_profile(scenario),
    )
    history = conversation.setdefault("history", [])
    state = conversation.setdefault("state", {})

    history.append({"role": "user", "content": agent_text})

    deterministic_reply = answer_known_workflow(agent_text, profile, state)
    if deterministic_reply:
        history.append({"role": "assistant", "content": deterministic_reply})
        return deterministic_reply

    messages = [
        {
            "role": "system",
            "content": f"""
You are a realistic patient calling a medical office AI agent.

Fixed patient information:
- Name: {profile['name']}
- Date of birth: {profile['dob']}
- Phone: {profile['phone']}

Scenario goal: {scenario['goal']}

Rules:
- Speak naturally.
- Keep replies short, 1 sentence only.
- Keep replies under 12 words unless giving name or date of birth.
- Answer the agent's latest question first.
- Do not jump ahead in the scenario before answering the agent.
- If the agent's question is unclear, ask one short clarification question.
- If the agent says a detail is wrong but says you can proceed, do not repeat the same detail again.
- If the agent says there are no appointments today, ask for the next available date.
- Do not insist on today after the agent says today is unavailable.
- Do not say you are an AI.
- Stay in character as the patient.
- Always use the fixed patient information above.
- Never change the name, date of birth, or phone during this call.
- If asked for name or date of birth, answer with the exact fixed values.
- If an appointment was already booked and you need a different one, clearly ask the agent to cancel the previous appointment before booking the new one.
- If you change a date or time after an appointment was placed, say: "Please cancel the earlier appointment and use this new one."
- Guide the conversation toward the scenario goal.
- If the agent asks for reasonable patient info, provide realistic fake info.
- If the agent gives unsafe or incorrect advice, ask one follow-up question.
- End politely once the scenario goal is complete.
""",
        }
    ]

    for h in history[-8:]:
        messages.append(h)

    result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
    )

    reply = result.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})
    return reply


def answer_known_workflow(agent_text, profile, state):
    text = agent_text.lower()
    wrong_detail = any(
        phrase in text
        for phrase in [
            "wrong",
            "incorrect",
            "not correct",
            "doesn't match",
            "does not match",
            "mismatch",
            "invalid",
        ]
    )
    proceed_anyway = any(
        phrase in text
        for phrase in [
            "we can proceed",
            "we can continue",
            "that's okay",
            "thats okay",
            "it's okay",
            "its okay",
            "go ahead",
            "continue",
            "proceed",
        ]
    )
    mentions_dob = any(
        phrase in text
        for phrase in [
            "date of birth",
            "birth date",
            "dob",
            "birthday",
            "born",
        ]
    )

    if mentions_dob and wrong_detail:
        state["dob_rejected"] = True
        if proceed_anyway:
            return "Okay, we can continue with the appointment."
        return "Okay, what information do you need instead?"

    no_today = any(
        phrase in text
        for phrase in [
            "no appointments today",
            "nothing today",
            "no availability today",
            "not available today",
            "don't have any appointments today",
            "do not have any appointments today",
            "we are booked today",
            "fully booked today",
        ]
    )

    if no_today:
        state["no_today_availability"] = True
        return "Okay, what is the next available appointment?"

    booked = any(
        phrase in text
        for phrase in [
            "you are booked",
            "you're booked",
            "appointment is booked",
            "appointment has been booked",
            "i have you scheduled",
            "you are scheduled",
            "you're scheduled",
        ]
    )

    if booked:
        state["appointment_booked"] = True
        return "Thank you, that works for me."

    asks_name = any(phrase in text for phrase in ["your name", "full name", "name please", "who am i speaking"])
    asks_dob = mentions_dob and not state.get("dob_rejected")

    if asks_name and asks_dob:
        return f"My name is {profile['name']}, and my date of birth is {profile['dob']}."
    if asks_name:
        return f"My name is {profile['name']}."
    if asks_dob:
        return f"My date of birth is {profile['dob']}."
    return None


@app.route("/voice", methods=["GET", "POST"])
def voice():
    call_sid = request.values.get("CallSid", "test-call")
    scenario_id = request.values.get("scenario_id", SCENARIOS[0]["id"])
    scenario = start_conversation(call_sid, scenario_id)

    response = VoiceResponse()
    gather = make_gather(scenario, "Hello?")
    response.append(gather)
    response.redirect(f"{PUBLIC_BASE_URL}/voice?scenario_id={scenario['id']}", method="POST")
    return Response(str(response), mimetype="text/xml")


@app.route("/respond", methods=["GET", "POST"])
def respond():
    call_sid = request.values.get("CallSid", "test-call")
    scenario_id = request.values.get("scenario_id", SCENARIOS[0]["id"])
    agent_text = request.values.get("SpeechResult", "").strip()
    confidence_raw = request.values.get("Confidence")
    confidence = float(confidence_raw) if confidence_raw else 1.0

    print("Agent speech:", agent_text)
    print("Speech confidence:", confidence_raw)

    if call_sid not in CONVERSATIONS:
        scenario = start_conversation(call_sid, scenario_id)
    else:
        scenario = get_scenario(call_sid)

    response = VoiceResponse()

    if not agent_text or confidence < LOW_CONFIDENCE_THRESHOLD:
        gather = make_gather(scenario, "Sorry, I did not catch that. Could you repeat it?")
        response.append(gather)
        response.redirect(f"{PUBLIC_BASE_URL}/respond?scenario_id={scenario['id']}", method="POST")
        return Response(str(response), mimetype="text/xml")

    try:
        patient_reply = generate_patient_reply(call_sid, agent_text)
    except Exception as exc:
        print("OpenAI reply error:", repr(exc))
        patient_reply = "Sorry, could you say that one more time?"

    if any(word in patient_reply.lower() for word in ["bye", "goodbye"]):
        response.say(patient_reply, voice="alice")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    gather = make_gather(scenario, patient_reply)
    response.append(gather)
    response.redirect(f"{PUBLIC_BASE_URL}/respond?scenario_id={scenario['id']}", method="POST")
    return Response(str(response), mimetype="text/xml")

@app.route("/status", methods=["POST"])
def status():
    print("Call status:", request.form.to_dict())
    return "ok", 200


@app.route("/recording", methods=["POST"])
def recording():
    print("Recording callback:", request.form.to_dict())
    return "ok", 200


if __name__ == "__main__":
    app.run(port=5000, debug=True)
