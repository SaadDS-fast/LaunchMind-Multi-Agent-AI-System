from message_bus import MessageBus
from dotenv import load_dotenv
from google import genai
import os
import json
import time


class ProductAgent:
    def __init__(self, bus: MessageBus):
        self.bus = bus
        self.name = "Product"
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

    def _fallback_spec(self, startup_idea: str) -> dict:
        return {
            "product_name": "FAST BookSwap",
            "startup_idea": startup_idea,
            "value_proposition": "A campus-first marketplace that helps students buy, sell, and exchange used academic books at affordable prices.",
            "personas": [
                {"name": "Ali", "role": "Budget student", "pain_point": "New books are expensive"},
                {"name": "Sara", "role": "Final-year student", "pain_point": "No easy resale platform"},
                {"name": "Usman", "role": "Freshman", "pain_point": "Does not know seniors"}
            ],
            "features": [
                {"name": "Post used books", "description": "Allow students to list books and notes for sale or exchange.", "priority": 1},
                {"name": "Search by course", "description": "Let users find books by course, semester, and subject.", "priority": 2},
                {"name": "Direct contact", "description": "Enable buyers and sellers to contact each other directly.", "priority": 3},
                {"name": "Campus filtering", "description": "Show listings relevant to FAST campus users.", "priority": 4},
                {"name": "Wishlist alerts", "description": "Notify students when needed books are posted.", "priority": 5}
            ],
            "user_stories": [
                "As a student, I want to search books by course so I can find relevant material.",
                "As a seller, I want to post my used books so I can recover costs.",
                "As a buyer, I want to contact the seller directly so I can negotiate price."
            ],
            "reasoning": "Fallback reasoning: generated a structured product specification for FAST BookSwap."
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
                print(f"Gemini error (Product attempt {attempt + 1}):", e)
                time.sleep(2 ** attempt)

        if last_error:
            print("Gemini failed after retries:", last_error)
        return ""

    def process_task(self):
        messages = self.bus.get_messages_for_agent(self.name)
        if not messages:
            return None

        latest_task = messages[-1]
        startup_idea = latest_task["payload"].get("startup_idea", "FAST BookSwap")

        prompt = f"""
You are a Product Manager for this startup:

{startup_idea}

Create a structured product specification as ONLY valid JSON with exactly these keys:
{{
  "product_name": "FAST BookSwap",
  "startup_idea": "same startup idea string",
  "value_proposition": "one sentence describing what the product does and for whom",
  "personas": [
    {{
      "name": "persona name",
      "role": "persona role",
      "pain_point": "specific pain point"
    }}
  ],
  "features": [
    {{
      "name": "feature name",
      "description": "feature description",
      "priority": 1
    }}
  ],
  "user_stories": [
    "As a [user], I want to [action] so that [benefit]."
  ],
  "reasoning": "brief explanation of why these choices fit the startup"
}}

Rules:
- Provide exactly 3 personas.
- Provide exactly 5 features.
- Priorities must be 1 to 5.
- Provide exactly 3 user stories.
- Keep the output relevant to FAST BookSwap.
"""

        raw = self._call_gemini(prompt)
        parsed = self._extract_json(raw)

        if not parsed:
            parsed = self._fallback_spec(startup_idea)

        spec = parsed

        # Send spec to Engineer and Marketing so they can consume it directly
        for recipient in ["Engineer", "Marketing", "CEO"]:
            self.bus.create_message(
                from_agent=self.name,
                to_agent=recipient,
                message_type="result",
                payload={
                    "result_type": "product_spec",
                    "data": spec
                },
                parent_message_id=latest_task["message_id"]
            )

        return spec