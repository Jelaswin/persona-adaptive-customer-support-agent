import logging
from datetime import datetime
from typing import List, Dict, Any

from src.config import settings

logger = logging.getLogger(__name__)


class EscalationEngine:
    def __init__(self):
        self.escalation_counters = {
            "billing_issue": {"label": "Billing Issue", "priority": "high"},
            "refund_request": {"label": "Refund Request", "priority": "high"},
            "legal_concern": {"label": "Legal Concern", "priority": "critical"},
            "account_sensitive": {"label": "Account-Sensitive Request", "priority": "critical"},
            "repeated_frustration": {"label": "Repeated User Frustration", "priority": "medium"},
            "low_confidence": {"label": "Low Retrieval Confidence", "priority": "medium"},
        }

    def evaluate(
        self,
        query: str,
        persona: str,
        persona_confidence: float,
        retrieval_results: List[Dict],
        escalation_triggers: List[str],
        conversation_history: List[Dict] = None,
    ) -> Dict[str, Any]:
        reasons = []
        priority = "low"

        retrieval_conf = (
            max(r["confidence"] for r in retrieval_results)
            if retrieval_results
            else 0.0
        )

        # 1. Low retrieval confidence
        if retrieval_conf < settings.ESCALATION_CONFIDENCE_THRESHOLD:
            reasons.append({
                "type": "low_confidence",
                "detail": (
                    f"Retrieval confidence ({retrieval_conf:.2f}) is below "
                    f"the threshold ({settings.ESCALATION_CONFIDENCE_THRESHOLD}). "
                    "No sufficiently relevant support document found."
                ),
                "priority": "medium",
            })

        # 2. Content-based escalation triggers
        for trigger in escalation_triggers:
            if trigger in self.escalation_counters:
                meta = self.escalation_counters[trigger]
                reasons.append({
                    "type": trigger,
                    "detail": f"Detected trigger: {meta['label']}.",
                    "priority": meta["priority"],
                })

        # 3. Repeated frustration from conversation history
        if conversation_history and len(conversation_history) >= 2:
            frustration_count = sum(
                1
                for turn in conversation_history
                if turn.get("persona") == "Frustrated User"
            )
            if frustration_count >= 2:
                reasons.append({
                    "type": "repeated_frustration",
                    "detail": (
                        f"User has been classified as Frustrated User "
                        f"{frustration_count} times in this conversation."
                    ),
                    "priority": "medium",
                })

        # Determine overall priority
        if any(r["priority"] == "critical" for r in reasons):
            priority = "critical"
        elif any(r["priority"] == "high" for r in reasons):
            priority = "high"
        elif reasons:
            priority = "medium"

        should_escalate = len(reasons) > 0

        logger.info(
            "Escalation evaluation: escalate=%s | priority=%s | reasons=%d",
            should_escalate, priority, len(reasons),
        )

        return {
            "should_escalate": should_escalate,
            "priority": priority,
            "reasons": reasons,
            "retrieval_confidence": round(retrieval_conf, 4),
        }

    def generate_handoff(
        self,
        query: str,
        response: str,
        persona: str,
        persona_confidence: float,
        retrieval_results: List[Dict],
        escalation_result: Dict[str, Any],
        conversation_history: List[Dict] = None,
    ) -> Dict[str, Any]:
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        handoff = {
            "handoff_timestamp": timestamp,
            "escalation_priority": escalation_result.get("priority", "low"),
            "original_query": query,
            "detected_persona": persona,
            "persona_confidence": round(persona_confidence, 4),
            "retrieval_confidence": escalation_result.get("retrieval_confidence", 0.0),
            "escalation_reasons": escalation_result.get("reasons", []),
            "ai_response": response,
            "sources_used": [
                {
                    "source": r.get("source", "unknown"),
                    "confidence": r.get("confidence", 0),
                }
                for r in (retrieval_results or [])
            ],
            "conversation_turns": len(conversation_history or []),
            "summary": self._build_summary(
                query, persona, escalation_result,
            ),
        }

        return handoff

    @staticmethod
    def _build_summary(
        query: str,
        persona: str,
        escalation_result: Dict[str, Any],
    ) -> str:
        reasons = escalation_result.get("reasons", [])
        reason_summary = "; ".join(r["detail"] for r in reasons) if reasons else "No specific reason."

        return (
            f"[{escalation_result.get('priority', 'low').upper()} PRIORITY] "
            f"User was classified as '{persona}'. "
            f"Escalation triggered: {len(reasons)} reason(s). "
            f"Details: {reason_summary}"
        )


class AnalyticsCounter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.counts = {
            "total_queries": 0,
            "escalations": 0,
            "persona_counts": {
                "Technical Expert": 0,
                "Frustrated User": 0,
                "Business Executive": 0,
            },
        }

    def track_query(self, persona: str, escalated: bool):
        self.counts["total_queries"] += 1
        if persona in self.counts["persona_counts"]:
            self.counts["persona_counts"][persona] += 1
        if escalated:
            self.counts["escalations"] += 1

    def get_summary(self) -> Dict[str, Any]:
        return dict(self.counts)
