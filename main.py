import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
from config import validate_environment
from logging_utils import log, log_success
from message_bus import MessageBus
from agents.ceo import CEOAgent
from agents.product import ProductAgent
from agents.engineer import EngineerAgent
from agents.marketing import MarketingAgent
from agents.qa import QAAgent

validate_environment()

bus = MessageBus()
bus.clear_messages()

ceo = CEOAgent(bus)
product = ProductAgent(bus)
engineer = EngineerAgent(bus)
marketing = MarketingAgent(bus)
qa = QAAgent(bus)

startup_idea = "FAST BookSwap: campus marketplace for used books"

log("CEO", "Starting project...")
ceo.start_project(startup_idea)

log("Product", "Generating product specification...")
product.process_task()

log("Engineer", "Creating landing page...")
engineer.process_task()

log("Marketing", "Generating launch content...")
marketing_content = marketing.process_task()

log("GitHub", "Preparing pull request...")
pr_artifacts = engineer.create_github_pr()
pr_url = None
if isinstance(pr_artifacts, dict):
    pr_url = pr_artifacts.get("payload", {}).get("pr_url")

log("Marketing", "Posting Slack launch message...")
if marketing_content and pr_url:
    marketing.post_slack(marketing_content, pr_url)
else:
    log("Marketing", "Slack launch message skipped because marketing content or PR URL is unavailable.")

log("QA", "Reviewing outputs...")
qa_result = qa.review_outputs()

log("CEO", "Reviewing QA decision...")
ceo.handle_qa_feedback()

log("Engineer", "Checking for revision request...")
revision_result = engineer.handle_revision()

if revision_result:
    log("QA", "Reviewing revised output...")
    qa_result = qa.review_outputs()

log("CEO", "Posting final summary...")
qa_payload = qa_result.get("payload", {}) if isinstance(qa_result, dict) else {}
ceo.post_final_summary(
    pr_url=pr_url,
    marketing_content=marketing_content or {},
    qa_result=qa_payload
)

log_success("CEO", "Workflow completed successfully.")
log("MessageBus", "Final messages:")
for msg in bus.get_messages():
    print(json.dumps(msg, indent=2, ensure_ascii=False))
