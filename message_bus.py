import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4


class MessageBus:
    ALLOWED_MESSAGE_TYPES = {"task", "result", "revision_request", "confirmation"}

    def __init__(self, storage_file: str = "messages.json"):
        self.storage_file = storage_file
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)

    def _load_messages(self) -> List[Dict]:
        with open(self.storage_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_messages(self, messages: List[Dict]) -> None:
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)

    def create_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        payload: Dict,
        parent_message_id: Optional[str] = None,
    ) -> Dict:
        if message_type not in self.ALLOWED_MESSAGE_TYPES:
            raise ValueError(
                f"Invalid message_type '{message_type}'. "
                f"Allowed types are: {sorted(self.ALLOWED_MESSAGE_TYPES)}"
            )

        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")

        messages = self._load_messages()

        message = {
            "message_id": f"msg_{uuid4().hex[:8]}",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "parent_message_id": parent_message_id,
        }

        messages.append(message)
        self._save_messages(messages)
        return message

    def get_messages(self) -> List[Dict]:
        return self._load_messages()

    def get_messages_for_agent(self, agent_name: str) -> List[Dict]:
        messages = self._load_messages()
        return [msg for msg in messages if msg["to_agent"] == agent_name]

    def get_messages_from_agent(self, agent_name: str) -> List[Dict]:
        messages = self._load_messages()
        return [msg for msg in messages if msg["from_agent"] == agent_name]

    def clear_messages(self) -> None:
        self._save_messages([])