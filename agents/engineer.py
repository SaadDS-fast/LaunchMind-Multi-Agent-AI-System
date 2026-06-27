import os
from pathlib import Path
from dotenv import load_dotenv
from github import Github, Auth, GithubException
from github.GithubException import UnknownObjectException
from message_bus import MessageBus
from llm_client import call_llm
from logging_utils import log, log_skip, log_success


class EngineerAgent:
    def __init__(self, bus: MessageBus):
        self.bus = bus
        self.name = "Engineer"
        load_dotenv()

    def _call_gemini(self, prompt):
        return call_llm(prompt, self.name)

    def _clean_html(self, html_content):
        cleaned = (html_content or "").strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        start = cleaned.lower().find("<!doctype html")
        if start == -1:
            start = cleaned.lower().find("<html")
        if start > 0:
            cleaned = cleaned[start:].strip()
        return cleaned

    def _is_relevant_landing_page(self, html_content):
        lowered = (html_content or "").lower()
        return "<html" in lowered and "bookswap" in lowered and "used book" in lowered

    def _latest_startup_idea(self):
        messages = self.bus.get_messages()
        for msg in reversed(messages):
            payload = msg.get("payload", {})
            if payload.get("startup_idea"):
                return payload["startup_idea"]
            data = payload.get("data", {})
            if isinstance(data, dict) and data.get("startup_idea"):
                return data["startup_idea"]
        return "FAST BookSwap: campus marketplace for used books"

    def _fallback_landing_page(self, startup_idea="FAST BookSwap"):
        product_name = startup_idea.split(":")[0].strip() or "FAST BookSwap"
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{product_name}</title>
  <style>
    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      color: #17202a;
      background: #f7faf8;
      line-height: 1.6;
    }}

    main {{
      width: min(1080px, calc(100% - 32px));
      margin: 0 auto;
      padding: 56px 0;
    }}

    .hero {{
      display: grid;
      gap: 24px;
      padding: 48px;
      border-radius: 8px;
      background: #ffffff;
      border: 1px solid #dfe8e3;
      box-shadow: 0 18px 48px rgba(23, 32, 42, 0.08);
    }}

    h1 {{
      max-width: 760px;
      margin: 0;
      font-size: clamp(2.2rem, 6vw, 4.5rem);
      line-height: 1.02;
    }}

    .subheadline {{
      max-width: 680px;
      margin: 0;
      font-size: 1.2rem;
      color: #3d4f45;
    }}

    .cta-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: center;
    }}

    .button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 48px;
      padding: 0 22px;
      border-radius: 6px;
      border: 0;
      background: #0b7a53;
      color: #ffffff;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
    }}

    .contact {{
      color: #315444;
      font-weight: 700;
    }}

    .features {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      margin-top: 28px;
    }}

    .feature {{
      padding: 22px;
      border-radius: 8px;
      background: #ffffff;
      border: 1px solid #dfe8e3;
    }}

    .feature h2 {{
      margin: 0 0 8px;
      font-size: 1.05rem;
    }}

    .feature p {{
      margin: 0;
      color: #4d5e55;
    }}

    @media (max-width: 760px) {{
      main {{
        padding: 24px 0;
      }}

      .hero {{
        padding: 28px;
      }}

      .features {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>Find the books you need before classes fill up.</h1>
      <p class="subheadline">{product_name} helps FAST students buy, sell, and swap used textbooks on campus without hunting through scattered group chats.</p>
      <div class="cta-row">
        <a class="button" href="mailto:hello@fastbookswap.com?subject=Join%20FAST%20BookSwap">Get Early Access</a>
        <span class="contact">Questions? hello@fastbookswap.com</span>
      </div>
    </section>

    <section class="features" aria-label="Key features">
      <article class="feature">
        <h2>List in minutes</h2>
        <p>Add your used books fast with course, condition, price, and pickup details.</p>
      </article>
      <article class="feature">
        <h2>Search by course</h2>
        <p>Find books by title, ISBN, semester, or course code from nearby students.</p>
      </article>
      <article class="feature">
        <h2>Swap on campus</h2>
        <p>Coordinate safe handoffs at familiar campus spots and save money before the semester rush.</p>
      </article>
    </section>
  </main>
</body>
</html>
"""

    def process_task(self):
        messages = self.bus.get_messages_for_agent(self.name)
        if not messages:
            return None

        latest_task = messages[-1]
        startup_idea = latest_task["payload"].get("startup_idea", "FAST BookSwap")

        prompt = f"""
You are a frontend engineer.

Startup:
{startup_idea}

Generate a COMPLETE HTML landing page including:
- headline
- subheadline
- features section (3 items)
- CTA button
- basic CSS styling

Return ONLY valid HTML.
"""

        html_content = self._clean_html(self._call_gemini(prompt))
        generation_source = "llm"

        if not html_content or not self._is_relevant_landing_page(html_content):
            html_content = self._fallback_landing_page(startup_idea)
            generation_source = "fallback"

        Path("landing_page.html").write_text(html_content, encoding="utf-8")
        log_success("Engineer", f"Landing page created using {generation_source}.")

        return self.bus.create_message(
            from_agent=self.name,
            to_agent="CEO",
            message_type="result",
            payload={
                "result_type": "engineering_output",
                "status": "landing_page_created",
                "details": f"Landing page generated with hero section, CTA button, features list, and contact email using {generation_source}."
            },
            parent_message_id=latest_task["message_id"]
        )

    def handle_revision(self):
        messages = self.bus.get_messages_for_agent(self.name)

        revision_msg = None
        for msg in reversed(messages):
            if msg["message_type"] == "revision_request":
                revision_msg = msg
                break

        if not revision_msg:
            return None

        feedback = revision_msg["payload"]["revision_instruction"]
        startup_idea = self._latest_startup_idea()
        current_html = Path("landing_page.html").read_text(encoding="utf-8") if Path("landing_page.html").exists() else ""

        prompt = f"""
You are updating the FAST BookSwap landing page.

Startup:
{startup_idea}

Current HTML:
{current_html}

Update the landing page HTML based on this feedback, while keeping the page specifically about FAST BookSwap, a campus marketplace for used books:

{feedback}

Return full updated valid HTML only. Do not wrap it in Markdown fences.
"""

        updated_html = self._clean_html(self._call_gemini(prompt))

        if not updated_html or not self._is_relevant_landing_page(updated_html):
            updated_html = self._fallback_landing_page(startup_idea)

        if updated_html:
            Path("landing_page.html").write_text(updated_html, encoding="utf-8")
            log_success("Engineer", "Landing page revision applied.")

        return self.bus.create_message(
            from_agent=self.name,
            to_agent="CEO",
            message_type="confirmation",
            payload={
                "result_type": "revision_completed",
                "status": "Landing page updated"
            },
            parent_message_id=revision_msg["message_id"]
        )

    def _github_message(self, status, pr_url=None, issue_url=None, reason=None, error=None):
        payload = {
            "result_type": "github_artifacts",
            "status": status,
            "pr_url": pr_url,
            "issue_url": issue_url,
        }
        if reason:
            payload["reason"] = reason
        if error:
            payload["error"] = error
        return self.bus.create_message(
            from_agent=self.name,
            to_agent="CEO",
            message_type="confirmation",
            payload=payload
        )

    def _ensure_github_branch(self, repo, branch):
        base_branch = repo.default_branch or "main"
        try:
            repo.get_branch(branch)
        except UnknownObjectException:
            repo.create_git_ref(
                ref=f"refs/heads/{branch}",
                sha=repo.get_branch(base_branch).commit.sha
            )
        log_success("GitHub", "Branch ready")

    def _upsert_landing_page(self, repo, branch):
        content = Path("landing_page.html").read_text(encoding="utf-8")
        try:
            contents = repo.get_contents("landing_page.html", ref=branch)
            repo.update_file(
                contents.path,
                "Agent landing page update",
                content,
                contents.sha,
                branch=branch
            )
        except UnknownObjectException:
            repo.create_file(
                "landing_page.html",
                "Agent landing page",
                content,
                branch=branch
            )
        log_success("GitHub", "Landing page updated")

    def _get_existing_pr_url(self, repo, branch):
        pulls = repo.get_pulls(state="open", head=f"{repo.owner.login}:{branch}")
        if pulls.totalCount > 0:
            log_success("GitHub", "Existing PR detected")
            return pulls[0].html_url
        return None

    def _create_or_reuse_pr(self, repo, branch):
        existing_pr_url = self._get_existing_pr_url(repo, branch)
        if existing_pr_url:
            log_success("GitHub", "Existing PR reused")
            return existing_pr_url

        pr = repo.create_pull(
            title="Agent Landing Page",
            body="Generated by Engineer agent",
            head=branch,
            base=repo.default_branch or "main"
        )
        log_success("GitHub", "Pull request created")
        return pr.html_url

    def create_github_issue(self, repo):
        title = "Initial landing page"
        try:
            existing_issues = repo.get_issues(state="open")
            for issue in existing_issues:
                if issue.title == title:
                    log_success("GitHub", "Existing issue reused")
                    return issue.html_url

            issue = repo.create_issue(
                title=title,
                body="Generated by Engineer agent"
            )
            log_success("GitHub", "Issue created")
            return issue.html_url
        except GithubException as e:
            log_skip("GitHub", f"Issue creation failed ({e.status}).")
            return None

    def create_github_pr(self):
        """Create or reuse GitHub artifacts for the generated landing page."""
        load_dotenv()

        token = os.getenv("GITHUB_TOKEN")
        repo_name = os.getenv("GITHUB_REPO")

        if not token or not repo_name:
            log_skip("GitHub", "Required credentials are not configured.")
            return self._github_message("skipped", reason="missing GitHub configuration")

        g = Github(auth=Auth.Token(token))
        try:
            repo = g.get_repo(repo_name)
        except GithubException as e:
            log_skip("GitHub", f"Repository lookup failed ({e.status}).")
            return self._github_message("skipped", reason="repository lookup failed", error=str(e))

        branch = "agent-update-landing"

        try:
            self._ensure_github_branch(repo, branch)
            self._upsert_landing_page(repo, branch)
            pr_url = self._create_or_reuse_pr(repo, branch)
        except GithubException as e:
            log_skip("GitHub", f"PR workflow failed ({e.status}).")
            return self._github_message("skipped", reason="GitHub PR workflow failed", error=str(e))

        issue_url = self.create_github_issue(repo)

        return self._github_message(
            "created" if pr_url or issue_url else "skipped",
            pr_url=pr_url,
            issue_url=issue_url
        )
