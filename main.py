import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
from message_bus import MessageBus
from agents.ceo import CEOAgent
from agents.product import ProductAgent
from agents.engineer import EngineerAgent
from agents.marketing import MarketingAgent
from agents.qa import QAAgent

bus = MessageBus()
bus.clear_messages()

ceo = CEOAgent(bus)
product = ProductAgent(bus)
engineer = EngineerAgent(bus)
marketing = MarketingAgent(bus)
qa = QAAgent(bus)

startup_idea = "FAST BookSwap: campus marketplace for used books"

print("\n--- CEO starting project ---")
ceo.start_project(startup_idea)

print("\n--- Product agent ---")
product.process_task()

print("\n--- Engineer agent ---")
engineer.process_task()

print("\n--- Marketing agent ---")
marketing_content = marketing.process_task()

print("\n--- GitHub PR creation ---")
pr_artifacts = engineer.create_github_pr()
pr_url = None
if isinstance(pr_artifacts, dict):
    pr_url = pr_artifacts.get("payload", {}).get("pr_url")

print("\n--- Marketing Slack message ---")
if marketing_content and pr_url:
    marketing.post_slack(marketing_content, pr_url)

print("\n--- QA agent ---")
qa_result = qa.review_outputs()

print("\n--- CEO revision decision ---")
ceo.handle_qa_feedback()

print("\n--- Engineer revision ---")
engineer.handle_revision()

print("\n--- CEO final summary ---")
qa_payload = qa_result.get("payload", {}) if isinstance(qa_result, dict) else {}
ceo.post_final_summary(
    pr_url=pr_url,
    marketing_content=marketing_content or {},
    qa_result=qa_payload
)

print("\n--- Final Messages ---")
for msg in bus.get_messages():
    print(json.dumps(msg, indent=2, ensure_ascii=False))