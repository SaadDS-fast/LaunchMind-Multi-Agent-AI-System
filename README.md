# 🚀 LaunchMind – Multi-Agent AI Startup Builder

LaunchMind is an autonomous **Multi-Agent AI system** that transforms a startup idea into a complete product workflow using coordinated AI agents. It demonstrates how specialized AI agents collaborate through structured communication to perform product planning, software generation, quality assurance, and marketing automation while integrating with real-world developer tools.

The project showcases concepts in **Agentic AI**, **Large Language Models (LLMs)**, **Multi-Agent Systems**, **Workflow Automation**, and **GitHub Automation**.

---

## ✨ Features

- 🤖 Multi-Agent AI Collaboration
- 🧠 LLM-powered Decision Making
- 📦 Product Specification Generation
- 🛠 Landing Page Generation
- 🔄 Structured Inter-Agent Communication
- 🧪 QA Feedback & Revision Loop
- 📂 Automated GitHub Issue Creation
- 🔀 Automated GitHub Pull Request Creation
- 📢 Slack Notification Integration
- 📧 SendGrid Email Integration
- ⚙️ Configuration Validation
- 🛡 Graceful Error Handling
- 📜 Production-style Logging

---

# 💡 Demo Startup

To demonstrate the complete workflow, LaunchMind uses the following startup idea:

### FAST BookSwap

A university marketplace where students can buy, sell, and exchange used textbooks using verified university accounts.

The system is generic and can be adapted to any startup idea by changing the initial prompt.

---

# 🧠 AI Agents

| Agent | Responsibility |
|--------|----------------|
| 👨‍💼 CEO Agent | Project planning, task delegation, reasoning, and final decision making |
| 📦 Product Agent | Product specification and feature planning |
| 🛠 Engineer Agent | Landing page generation, GitHub automation, revisions |
| 📢 Marketing Agent | Marketing content, email campaigns, Slack notifications |
| 🧪 QA Agent | Quality review and feedback generation |
| 📨 Message Bus | Structured communication between all agents |

---

# 🏗 System Architecture

```text
                +----------------+
                |    CEO Agent   |
                +--------+-------+
                         |
    -------------------------------------------
    |                     |                  |
+------------+   +--------------+   +------------+
| Product    |   |  Engineer    |   | Marketing  |
|   Agent    |   |    Agent     |   |   Agent    |
+------------+   +--------------+   +------------+
       |                |                  |
 Product Spec      Landing Page      Email + Slack
                         |
                     GitHub Issue
                         |
                     GitHub PR
                         |
                     +--------+
                     |  QA    |
                     | Agent  |
                     +---+----+
                         |
                    Feedback Loop
                         |
                     CEO Decision
                         |
                 Engineer Revision
```

---

# 🔄 Workflow

```text
CEO Agent
      │
      ├────────► Product Agent
      │
      ├────────► Engineer Agent
      │
      ├────────► Marketing Agent
      │
      ▼
GitHub Automation
      │
      ▼
QA Review
      │
      ▼
CEO Decision
      │
      ▼
(Optional Revision)
      │
      ▼
Final Summary
```

---

# 🔗 Platform Integrations

| Platform | Purpose |
|-----------|---------|
| GitHub | Issue creation, Pull Request creation |
| Slack | Launch notifications |
| SendGrid | Marketing email generation |

> **Note:** Slack and SendGrid integrations are optional. If credentials are not configured, the workflow continues successfully.

---

# 🛠 Tech Stack

- Python 3.11+
- Google Gemini API
- GitHub API
- PyGithub
- SendGrid
- Slack SDK
- python-dotenv
- HTML
- JSON
- Git

---

# 📂 Project Structure

```text
LaunchMind-Multi-Agent-AI-System/

├── agents/
│   ├── ceo.py
│   ├── product.py
│   ├── engineer.py
│   ├── marketing.py
│   └── qa.py
│
├── message_bus.py
├── main.py
├── landing_page.html
├── messages.json
├── requirements.txt
├── .env.example
└── README.md
```

---

# ⚙️ Installation

## Clone Repository

```bash
git clone https://github.com/SaadDS-fast/LaunchMind-Multi-Agent-AI-System.git
cd LaunchMind-Multi-Agent-AI-System
```

---

## Create Virtual Environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create a `.env` file in the project root.

### Required

```env
GEMINI_API_KEY=
GITHUB_TOKEN=
GITHUB_REPO=username/repository
```

### Optional

```env
SLACK_BOT_TOKEN=
SLACK_CHANNEL=

SENDGRID_API_KEY=
EMAIL_FROM=
EMAIL_TO=
```

Optional integrations are skipped automatically if credentials are not provided.

---

# ▶️ Run the Project

```bash
python main.py
```

---

# 📸 Example Console Output

```text
[Config] Environment validation completed.

[CEO] Starting project...

[Product] Product specification generated.

[Engineer] Landing page generated successfully.

[GitHub] Branch ready.

[GitHub] Landing page updated.

[GitHub] Existing PR detected.

[GitHub] Existing PR reused.

[QA] Local checks passed.

[CEO] Workflow completed successfully.
```

---

# 📷 Screenshots

> Add screenshots here after running the project.

Suggested screenshots:

- System execution
- Landing page generated
- GitHub Issue
- GitHub Pull Request
- Slack notification
- Generated marketing content

---

# 🎯 Learning Outcomes

This project demonstrates practical implementation of:

- Agentic AI
- Multi-Agent Systems
- LLM Orchestration
- Prompt Engineering
- Workflow Automation
- GitHub Automation
- Software Engineering
- Structured Agent Communication

---

# ⚠️ Known Limitations

- Requires valid API credentials for external integrations.
- LLM outputs may vary between executions.
- External APIs may enforce rate limits.
- Optional services (Slack and SendGrid) require valid credentials.

---

# 🚀 Future Improvements

- Retrieval-Augmented Generation (RAG)
- Memory-enabled agents
- Multi-model LLM support
- Docker deployment
- Web dashboard
- Human-in-the-loop approval workflow
- Multi-agent parallel execution

---

# 👨‍💻 Author

**Muhammad Saad**

MS Data Science | AI & Machine Learning

GitHub: https://github.com/SaadDS-fast

LinkedIn: https://www.linkedin.com/in/saad-saboor

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.