import os
import json
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from github import Github, Auth
from message_bus import MessageBus
from llm_client import call_llm
from logging_utils import log, log_skip, log_success
from text_utils import extract_json
import requests

load_dotenv()


class QAAgent:
    def __init__(self, bus: MessageBus):
        self.bus = bus
        self.name = "QA"

    def _call_gemini(self, prompt: str) -> str:
        return call_llm(prompt, self.name)

    def _extract_json(self, text: str):
        return extract_json(text)

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
            return None
        return None

    def _get_repo(self):
        token = os.getenv("GITHUB_TOKEN")
        repo_name = os.getenv("GITHUB_REPO")

        if not token or not repo_name:
            raise ValueError("GitHub config missing for QA.")

        g = Github(auth=Auth.Token(token))
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

    def _fallback_review(self, html_path="landing_page.html"):
        path = Path(html_path)
        html = path.read_text(encoding="utf-8", errors="ignore").lower() if path.exists() else ""
        issues = []

        has_strong_cta = any(
            phrase in html
            for phrase in ["get early access", "join the waitlist", "join waitlist", "start swapping"]
        )
        has_contact = "mailto:" in html or "contact" in html or "@" in html
        has_urgency = any(
            phrase in html
            for phrase in ["before classes", "semester rush", "this semester", "early access"]
        )

        if not has_strong_cta:
            issues.append("Landing page needs a stronger CTA button.")
        if not has_contact:
            issues.append("Landing page should include a visible contact email.")
        if not has_urgency:
            issues.append("Marketing copy should create more urgency.")

        return {
            "verdict": "fail" if issues else "pass",
            "issues": issues,
            "revision_focus": "Improve CTA strength, add contact email, and add urgency." if issues else ""
        }

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
            log_skip("QA", "GitHub PR comments skipped (PR URL unavailable).")
            return None

        try:
            repo = self._get_repo()
            pr_number = self._parse_pr_number(pr_url)
        except Exception as e:
            log_skip("QA", f"GitHub PR comments skipped ({e}).")
            return None

        if not pr_number:
            log_skip("QA", "GitHub PR comments skipped (PR number could not be parsed).")
            return None

        comments = self._find_inline_targets("landing_page.html")
        if not comments:
            log_skip("QA", "GitHub PR comments skipped (no suitable inline targets).")
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
                log_skip("QA", f"Inline PR comment failed; trying issue comment ({e}).")
                try:
                    pr = repo.get_pull(pr_number)
                    pr.create_issue_comment(c["body"])
                    posted += 1
                except Exception as e2:
                    log_skip("QA", f"Fallback issue comment failed ({e2}).")

        if posted > 0:
            log_success("QA", "GitHub PR comments posted.")
        return posted

    def review_outputs(self):
        engineering_output, marketing_output, pr_url = self._latest_outputs()

        if not engineering_output and not marketing_output:
            return None

        eng_text = json.dumps(engineering_output, ensure_ascii=False, indent=2) if engineering_output else "{}"
        mkt_text = json.dumps(marketing_output, ensure_ascii=False, indent=2) if marketing_output else "{}"
        landing_html = Path("landing_page.html").read_text(encoding="utf-8", errors="ignore") if Path("landing_page.html").exists() else ""

        prompt = f"""
You are a strict QA reviewer for a multi-agent startup system.

Review these outputs:

ENGINEERING OUTPUT:
{eng_text}

MARKETING OUTPUT:
{mkt_text}

CURRENT LANDING PAGE HTML:
{landing_html}

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
        local_review = self._fallback_review("landing_page.html")

        if not review:
            review = local_review
        elif local_review.get("verdict") == "pass":
            log("QA", "Local checks passed; treating LLM stylistic feedback as non-blocking.")
            review = local_review

        feedback_text = " | ".join(review.get("issues", [])) if review.get("issues") else "QA passed local landing page checks."
        if review.get("verdict") == "pass":
            log_success("QA", "Local checks passed.")
        else:
            log("QA", "Issues found; sending feedback to CEO.")

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
