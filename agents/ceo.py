from message_bus import MessageBus
from typing import Optional, Dict
import os
import json
import time
from dotenv import load_dotenv
from google import genai


class CEOAgent:
    def __init__(self, bus: MessageBus):
        self.bus = bus
        self.name = "CEO"
        self.startup_idea = None
        load_dotenv()
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")

    def _extract_json(self, text: str):
        if not text:
            return None

        cleaned = text.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            return json.loads(cleaned)
        except Exception:
            return None

    def _fallback_plan(self, startup_idea: str) -> dict:
        return {
            "reasoning": (
                "Fallback reasoning: LLM unavailable.\n"
                "- Product: define value proposition, personas, features, and user stories\n"
                "- Engineer: build landing page and GitHub workflow\n"
                "- Marketing: create tagline, launch copy, email, and Slack message"
            ),
            "product_task": "Define the product specification with personas, features, and user stories.",
            "engineer_task": "Build a responsive landing page and prepare GitHub issue/PR workflow.",
            "marketing_task": "Create tagline, short description, cold email, and Slack launch message."
        }

    def _call_gemini(self, prompt: str) -> str:
        last_error = None

        for attempt in range(3):
            try:
                client = genai.Client()
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                text = (response.text or "").strip()
                if text:
                    return text
            except Exception as e:
                last_error = e
                print(f"Gemini error (CEO attempt {attempt + 1}):", e)
                time.sleep(2 ** attempt)

        if last_error:
            print("Gemini failed after retries:", last_error)
        return ""

    def start_project(self, startup_idea: str):
        self.startup_idea = startup_idea

        prompt = f"""
You are the CEO of a startup.

Startup idea:
{startup_idea}

Return ONLY valid JSON with exactly these keys:
{{
  "reasoning": "short explanation of how you decomposed the startup idea",
  "product_task": "task for Product agent",
  "engineer_task": "task for Engineer agent",
  "marketing_task": "task for Marketing agent"
}}

Make the tasks specific to the startup idea.
"""

        raw = self._call_gemini(prompt)
        parsed = self._extract_json(raw)

        if not parsed:
            parsed = self._fallback_plan(startup_idea)
            raw = parsed["reasoning"]

        task_payloads = {
            "Product": {
                "startup_idea": startup_idea,
                "task": parsed.get("product_task", "Create product specification."),
                "llm_reasoning": parsed.get("reasoning", raw)
            },
            "Engineer": {
                "startup_idea": startup_idea,
                "task": parsed.get("engineer_task", "Build landing page."),
                "llm_reasoning": parsed.get("reasoning", raw)
            },
            "Marketing": {
                "startup_idea": startup_idea,
                "task": parsed.get("marketing_task", "Create marketing content."),
                "llm_reasoning": parsed.get("reasoning", raw)
            }
        }

        for recipient, payload in task_payloads.items():
            self.bus.create_message(
                from_agent=self.name,
                to_agent=recipient,
                message_type="task",
                payload=payload
            )

    def handle_qa_feedback(self) -> Optional[Dict]:
        messages = self.bus.get_messages()

        qa_feedback = None
        for msg in reversed(messages):
            if msg["message_type"] == "result" and msg["payload"].get("result_type") == "qa_feedback":
                qa_feedback = msg
                break

        if not qa_feedback:
            return None

        feedback = qa_feedback["payload"].get("feedback", "")

        prompt = f"""
You are the CEO reviewing QA feedback.

QA feedback:
{feedback}

Return ONLY valid JSON with:
{{
  "decision": "YES or NO",
  "reasoning": "brief reasoning",
  "revision_instruction": "what the Engineer should change"
}}

If revision is needed, answer YES.
"""

        raw = self._call_gemini(prompt)
        parsed = self._extract_json(raw)

        if not parsed:
            parsed = {
                "decision": "YES",
                "reasoning": "Fallback decision: QA feedback indicates the landing page should be improved.",
                "revision_instruction": "Add a stronger CTA and include contact email."
            }

        decision = str(parsed.get("decision", "")).upper()
        reasoning = parsed.get("reasoning", raw or "No reasoning returned.")
        revision_instruction = parsed.get("revision_instruction", feedback)

        if "YES" in decision or "REVISE" in decision:
            return self.bus.create_message(
                from_agent=self.name,
                to_agent="Engineer",
                message_type="revision_request",
                payload={
                    "feedback": feedback,
                    "llm_decision": reasoning,
                    "revision_instruction": revision_instruction
                },
                parent_message_id=qa_feedback["message_id"]
            )

        return None

    def post_final_summary(self, pr_url: str, marketing_content: dict | None = None, qa_result: dict | None = None):
        from slack_sdk import WebClient

        token = os.getenv("SLACK_BOT_TOKEN")
        channel = os.getenv("SLACK_CHANNEL", "#launches")

        if not token:
            print("Slack error: missing SLACK_BOT_TOKEN")
            return None

        marketing_content = marketing_content or {}
        qa_result = qa_result or {}

        prompt = f"""
You are the CEO of FAST BookSwap.

Write a concise final launch summary for Slack in 2 to 3 sentences.
Mention:
- the product name FAST BookSwap
- the GitHub PR link: {pr_url}
- the marketing tagline: {marketing_content.get("tagline", "")}
- the QA verdict: {qa_result.get("verdict", "pass")}

Do not use bullets. Keep it polished and professional.
"""

        summary_text = self._call_gemini(prompt)
        if not summary_text:
            summary_text = f"FAST BookSwap is ready. PR: {pr_url}"

        client = WebClient(token=token)
        client.chat_postMessage(
            channel=channel,
            text=summary_text,
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Final Launch Summary: FAST BookSwap"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": summary_text
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*GitHub PR:*\n<{pr_url}|View PR>"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*QA Verdict:*\n{qa_result.get('verdict', 'pass')}"
                        }
                    ]
                }
            ]
        )

        print("CEO final summary sent to Slack.")
        return summary_text