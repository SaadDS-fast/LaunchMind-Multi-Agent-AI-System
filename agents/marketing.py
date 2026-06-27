import os
import requests
from dotenv import load_dotenv
from message_bus import MessageBus
from llm_client import call_llm
from logging_utils import log_skip, log_success
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from text_utils import extract_json

load_dotenv()


class MarketingAgent:
    def __init__(self, bus: MessageBus):
        self.bus = bus
        self.name = "Marketing"

    def _call_gemini(self, prompt: str) -> str:
        return call_llm(prompt, self.name)

    def _extract_json(self, text: str):
        return extract_json(text)

    def _latest_product_spec(self):
        messages = self.bus.get_messages()
        for msg in reversed(messages):
            if msg.get("message_type") == "result" and msg.get("payload", {}).get("result_type") == "product_spec":
                return msg["payload"]["data"]
        return None

    def send_email(self, subject, body):
        api_key = os.getenv("SENDGRID_API_KEY")
        email_to = os.getenv("EMAIL_TO")
        email_from = os.getenv("EMAIL_FROM")

        if not api_key or not email_to or not email_from:
            log_skip("Marketing", "Email integration skipped (credentials not configured).")
            return None

        url = "https://api.sendgrid.com/v3/mail/send"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "personalizations": [
                {
                    "to": [{"email": email_to}],
                    "subject": subject
                }
            ],
            "from": {"email": email_from},
            "content": [
                {
                    "type": "text/html",
                    "value": f"<p>{body.replace(chr(10), '<br>')}</p>"
                }
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
        except requests.RequestException as e:
            log_skip("Marketing", f"Email integration request failed ({e}).")
            return None

        if response.status_code == 202:
            log_success("Marketing", "Email sent successfully.")
        else:
            log_skip("Marketing", f"Email integration returned status {response.status_code}.")
        return response

    def post_slack(self, content: dict, pr_url: str):
        token = os.getenv("SLACK_BOT_TOKEN")
        channel = os.getenv("SLACK_CHANNEL", "#launches")

        if not token:
            log_skip("Marketing", "Slack integration skipped (credentials not configured).")
            return None

        client = WebClient(token=token)

        try:
            response = client.chat_postMessage(
                channel=channel,
                text=f"New launch: {content.get('tagline', 'FAST BookSwap')}",
                blocks=[
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"New Launch: {content.get('tagline', 'FAST BookSwap')}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": content.get("description", "")
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
                                "text": "*Status:* Ready for review"
                            }
                        ]
                    }
                ]
            )
        except SlackApiError as e:
            log_skip("Marketing", f"Slack integration failed ({e.response.get('error', e)}).")
            return None
        except Exception as e:
            log_skip("Marketing", f"Slack integration failed ({e}).")
            return None

        log_success("Marketing", "Slack launch message sent.")
        return response

    def process_task(self):
        messages = self.bus.get_messages_for_agent(self.name)
        if not messages:
            return None

        latest_task = messages[-1]
        product_spec = self._latest_product_spec() or {}

        product_name = product_spec.get("product_name", "FAST BookSwap")
        value_proposition = product_spec.get(
            "value_proposition",
            f"{product_name} helps students buy and sell used books on campus."
        )
        top_features = [f.get("name", "") for f in product_spec.get("features", [])[:3] if f.get("name")]

        prompt = f"""
You are a startup marketing expert.

Product name: {product_name}
Value proposition: {value_proposition}
Top features: {", ".join(top_features)}

Return ONLY valid JSON with exactly these keys:
{{
  "email_subject": "",
  "tagline": "",
  "description": "",
  "cold_email": "",
  "twitter_post": "",
  "linkedin_post": "",
  "instagram_post": "",
  "slack_message": ""
}}

Rules:
- Use the actual product name: {product_name}
- Do NOT use placeholders like [Startup Name], [Link], [University Name], or bracketed text
- Keep the tagline under 10 words
- Description must be 2 to 3 sentences
- Cold email should sound natural and persuasive
- Make everything specifically about a campus book marketplace
"""

        raw = self._call_gemini(prompt)
        marketing_content = self._extract_json(raw)

        if not marketing_content:
            marketing_content = {
                "email_subject": "Save on textbooks this semester",
                "tagline": "Stop overpaying for textbooks.",
                "description": f"{product_name} is a campus marketplace for students to buy and sell used books locally.",
                "cold_email": f"Hi,\n\nWe built {product_name} to help students save money on textbooks and trade locally on campus.\n\nJoin the waitlist today.",
                "twitter_post": f"{product_name} helps students save money on used books.",
                "linkedin_post": f"{product_name} is building a local campus marketplace for used textbooks.",
                "instagram_post": f"Save money on books with {product_name}.",
                "slack_message": f"{product_name} is live for campus book swapping."
            }
            log_skip("Marketing", "LLM unavailable; fallback marketing copy used.")
        else:
            log_success("Marketing", "Marketing content generated.")

        self.send_email(
            subject=marketing_content["email_subject"],
            body=marketing_content["cold_email"]
        )

        self.bus.create_message(
            from_agent=self.name,
            to_agent="CEO",
            message_type="result",
            payload={
                "result_type": "marketing_output",
                "content": marketing_content
            },
            parent_message_id=latest_task["message_id"]
        )

        return marketing_content
