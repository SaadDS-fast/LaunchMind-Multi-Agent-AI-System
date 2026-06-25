import os
import json
import time
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from github import Github
from message_bus import MessageBus
from google import genai
import requests

load_dotenv()


class QAAgent:
    def __init__(self, bus: MessageBus):
        self.bus = bus
        self.name = "QA"
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")

    def _call_gemini(self, prompt: str) -> str:
        for attempt in range(3):
            try:
                client = genai.Client()
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                if response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"Gemini error (QA attempt {attempt + 1}):", e)
                time.sleep(2 ** attempt)
        return ""

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

    def _latest_outputs(self):
        messages = self.bus.get_messages()
        engineering_output = None
        marketing_output = None
        pr_url = None

        for msg in messages:
            if msg["message_type"] == "result":
                payload = msg.get("payload", {})
                if payload.get("result_type") == "engineering_output":
                    engineering_output = msg
                elif payload.get("result_type") == "marketing_output":
                    marketing_output = msg
            elif msg["message_type"] == "confirmation":
                payload = msg.get("payload", {})
                if payload.get("result_type") == "github_artifacts":
                    pr_url = payload.get("pr_url", pr_url)

        return engineering_output, marketing_output, pr_url

    def _parse_pr_number(self, pr_url: str):
        try:
            path = urlparse(pr_url).path.strip("/")
            parts = path.split("/")
            if len(parts) >= 4 and parts[-2] == "pull":
                return int(parts[-1])
            if len(parts) >= 3 and parts[-2] == "pull":
                return int(parts[-1])
        except Exception:
            pass
        return None

    def _get_repo(self):
        token = os.getenv("GITHUB_TOKEN")
        repo_name = os.getenv("GITHUB_REPO")

        if not token or not repo_name:
            raise ValueError("GitHub config missing for QA.")

        g = Github(token)
        return g.get_repo(repo_name)

    def _get_head_sha(self, repo, pr_number: int):
        pr = repo.get_pull(pr_number)
        return pr.head.sha

    def _find_inline_targets(self, html_path="landing_page.html"):
        path = Path(html_path)
        if not path.exists():
            return []

        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        targets = []

        for idx, line in enumerate(lines, start=1):
            low = line.lower()

            if len(targets) < 1 and ("button" in low or "cta" in low):
                targets.append({
                    "path": html_path,
                    "line": idx,
                    "body": "QA Review: Make the CTA more prominent and action-oriented, for example 'Get Early Access' or 'Join the Waitlist'."
                })

            if len(targets) < 2 and ("contact" in low or "email" in low or "mailto:" in low):
                targets.append({
                    "path": html_path,
                    "line": idx,
                    "body": "QA Review: Add a visible contact email or support link so visitors can follow up easily."
                })

        if len(targets) < 2:
            for idx, line in enumerate(lines, start=1):
                if len(targets) < 2 and ("h1" in line.lower() or "bookswap" in line.lower()):
                    targets.append({
                        "path": html_path,
                        "line": idx,
                        "body": "QA Review: Add stronger urgency in the hero copy to drive immediate signups."
                    })

        return targets[:2]

    def _post_inline_comment(self, repo, pr_number: int, body: str, path: str, line: int):
        token = os.getenv("GITHUB_TOKEN")
        api_url = f"https://api.github.com/repos/{repo.full_name}/pulls/{pr_number}/comments"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json"
        }

        pr = repo.get_pull(pr_number)
        payload = {
            "body": body,
            "commit_id": pr.head.sha,
            "path": path,
            "line": line,
            "side": "RIGHT"
        }

        r = requests.post(api_url, headers=headers, json=payload, timeout=30)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Failed to post inline comment: {r.status_code} {r.text}")

    def post_github_comments(self, pr_url: str):
        if not pr_url:
            print("No PR URL found for QA review.")
            return None

        repo = self._get_repo()
        pr_number = self._parse_pr_number(pr_url)

        if not pr_number:
            print("Could not parse PR number for QA review.")
            return None

        comments = self._find_inline_targets("landing_page.html")
        if not comments:
            print("No suitable inline targets found in landing_page.html.")
            return None

        posted = 0
        for c in comments[:2]:
            try:
                self._post_inline_comment(
                    repo=repo,
                    pr_number=pr_number,
                    body=c["body"],
                    path=c["path"],
                    line=c["line"]
                )
                posted += 1
            except Exception as e:
                print("Inline comment failed, falling back to issue comment:", e)
                try:
                    pr = repo.get_pull(pr_number)
                    pr.create_issue_comment(c["body"])
                    posted += 1
                except Exception as e2:
                    print("Fallback issue comment also failed:", e2)

        if posted > 0:
            print("QA comments posted on GitHub PR.")
        return posted

    def review_outputs(self):
        engineering_output, marketing_output, pr_url = self._latest_outputs()

        if not engineering_output and not marketing_output:
            return None

        eng_text = json.dumps(engineering_output, ensure_ascii=False, indent=2) if engineering_output else "{}"
        mkt_text = json.dumps(marketing_output, ensure_ascii=False, indent=2) if marketing_output else "{}"

        prompt = f"""
You are a strict QA reviewer for a multi-agent startup system.

Review these outputs:

ENGINEERING OUTPUT:
{eng_text}

MARKETING OUTPUT:
{mkt_text}

Return ONLY valid JSON with this schema:
{{
  "verdict": "pass" or "fail",
  "issues": [
    "issue 1",
    "issue 2"
  ],
  "revision_focus": "short instruction for the Engineer"
}}

Be strict. Fail if the landing page is generic, lacks urgency, weak CTA, or missing contact details.
"""

        raw = self._call_gemini(prompt)
        review = self._extract_json(raw)

        if not review:
            review = {
                "verdict": "fail",
                "issues": [
                    "Landing page needs a stronger CTA button.",
                    "Landing page should include a visible contact email.",
                    "Marketing copy should create more urgency."
                ],
                "revision_focus": "Improve CTA strength, add contact email, and add urgency."
            }

        feedback_text = " | ".join(review.get("issues", [])) if review.get("issues") else "QA found issues."

        self.post_github_comments(pr_url)

        return self.bus.create_message(
            from_agent=self.name,
            to_agent="CEO",
            message_type="result",
            payload={
                "result_type": "qa_feedback",
                "verdict": review.get("verdict", "fail"),
                "issues": review.get("issues", []),
                "revision_focus": review.get("revision_focus", ""),
                "feedback": feedback_text,
                "pr_url": pr_url
            }
        )