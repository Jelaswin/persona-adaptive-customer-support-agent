import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

PERSONAS = {
    "technical_expert": "Technical Expert",
    "frustrated_user": "Frustrated User",
    "business_executive": "Business Executive",
}

TECHNICAL_KEYWORDS = [
    "api", "endpoint", "authentication", "token", "oauth", "sdk",
    "error code", "stack trace", "exception", "debug", "log",
    "integration", "deploy", "pipeline", "workflow", "webhook",
    "json", "rest", "graphql", "query", "payload", "response code",
    "header", "rate limit", "throttle", "timeout", "latency",
    "server", "database", "schema", "migration", "connection string",
    "ssl", "tls", "certificate", "encryption", "hash", "salt",
    "version", "release", "rollback", "caching", "load balancer",
    "docker", "container", "microservice", "config", "environment variable",
    "cli", "terminal", "curl", "postman", "swagger", "openapi",
    "bearer", "oauth2", "client_id", "client_secret", "grant_type",
]

FRUSTRATED_KEYWORDS = [
    "not working", "broken", "doesn't work", "won't work", "useless",
    "terrible", "awful", "horrible", "annoying", "irritating",
    "frustrat", "angry", "mad", "upset", "disappointed",
    "unacceptable", "ridiculous", "absurd", "joke", "pathetic",
    "waste", "incompetent", "clueless", "unbelievable",
    "fix this", "fix it", "please fix", "help me", "please help",
    "urgent", "asap", "immediately", "right now", "hurry",
    "sick of", "tired of", "fed up", "done with", "had enough",
    "stupid", "nonsense", "inexcusable", "appalling",
    "complaint", "issue", "problem", "bug", "glitch",
    "failing", "crashing", "freezing", "stuck", "hung",
    "never works", "always fails", "yet again", "again",
    "hours", "days", "weeks", "months", "still not",
    "nothing works", "nothing is working", "anything works",
    "trying", "tried", "attempt",
    "waste of time", "wasting my time",
]

FRUSTRATED_PATTERNS = [
    r"\bfor\s+(an?\s+)?(hour|hours|day|days|week|weeks|month|months|ages|ever)\b",
    r"\b(still|yet|again)\s+(not|no|nothing|won't|doesn't)\b",
    r"\b(can't|cannot|can not)\s+(even\s+)?(log|login|access|find|get|do|use|work)\b",
    r"\b(why\s+is|why\s+does|why\s+can't|why\s+won't)\b",
    r"\b(nothing|no one|nobody)\s+(works?|helps?|is working)\b",
    r"\bi've?\s+been\s+(trying|waiting|stuck)\b",
    r"\b(already|still)\s+(told|said|asked|reported|contacted)\b",
    r"\b(this\s+is|that\s+is)\s+(unacceptable|ridiculous|absurd|insane)\b",
]

BUSINESS_KEYWORDS = [
    "roi", "revenue", "cost", "budget", "quarterly", "q1", "q2", "q3", "q4",
    "stakeholder", "investor", "executive", "management", "board",
    "timeline", "roadmap", "milestone", "deadline", "deliverable",
    "efficiency", "productivity", "bottom line", "growth", "scalability",
    "market", "competition", "competitive", "strategy", "strategic",
    "business", "enterprise", "organization", "team",
    "kpi", "metric", "performance", "analytics", "dashboard",
    "report", "summary", "overview", "update", "status",
    "impact", "value", "benefit", "advantage", "outcome",
    "launch", "go live", "rollout", "release date", "schedule",
    "contract", "agreement", "partnership", "client", "customer",
    "pricing", "subscription", "plan", "tier", "upgrade",
    "support sla", "downtime", "availability", "uptime",
    "decision", "approval", "authorization", "go ahead",
    "operations", "resolution timeline", "expected", "affecting",
]


def classify_persona(query: str, conversation_history: list = None) -> Tuple[str, float, dict]:
    query_lower = query.lower()
    conversation_text = " ".join(
        [q.get("query", "") for q in (conversation_history or [])]
    ).lower()

    all_text = f"{query_lower} {conversation_text}"

    tech_score = _keyword_score(query_lower, TECHNICAL_KEYWORDS)
    frust_score = _keyword_score(query_lower, FRUSTRATED_KEYWORDS)
    biz_score = _keyword_score(query_lower, BUSINESS_KEYWORDS)

    pattern_score = _pattern_score(query_lower, FRUSTRATED_PATTERNS)
    frust_score = max(frust_score, pattern_score)

    scores = {
        "technical_expert": tech_score,
        "frustrated_user": frust_score,
        "business_executive": biz_score,
    }

    sentiment = _detect_sentiment(all_text)
    if sentiment["label"] == "negative" and sentiment["score"] > 0.3:
        scores["frustrated_user"] += sentiment["score"] * 0.4

    best_persona = max(scores, key=scores.get)
    confidence = scores[best_persona]

    if confidence < 0.1:
        best_persona = "frustrated_user"
        confidence = 0.1

    details = {
        "raw_scores": {k: round(v, 4) for k, v in scores.items()},
        "sentiment": sentiment,
        "confidence": round(confidence, 4),
    }

    logger.info(
        "Persona classified: %s (confidence=%.4f) | scores=%s | sentiment=%s",
        best_persona, confidence, details["raw_scores"], sentiment,
    )

    return PERSONAS[best_persona], confidence, details


def _keyword_score(text: str, keywords: list) -> float:
    matches = 0
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
            matches += 1
    if matches == 0:
        return 0.0
    return min(1.0, matches * 0.15)


def _pattern_score(text: str, patterns: list) -> float:
    matches = 0
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matches += 1
    if matches == 0:
        return 0.0
    return min(1.0, matches * 0.20)


def _detect_sentiment(text: str) -> dict:
    positive_words = [
        "great", "good", "excellent", "amazing", "wonderful",
        "fantastic", "helpful", "thank", "thanks", "appreciate",
        "love", "perfect", "awesome", "nice", "happy", "pleased",
        "satisfied", "working", "fixed", "solved", "resolved",
    ]
    negative_words = [
        "bad", "terrible", "awful", "horrible", "worst", "hate",
        "angry", "frustrat", "annoy", "upset", "disappoint",
        "broken", "failing", "crashing", "stuck", "useless",
        "unacceptable", "ridiculous", "pathetic", "incompetent",
    ]

    text_lower = text.lower()
    pos_count = sum(1 for w in positive_words if re.search(rf"\b{w}\b", text_lower))
    neg_count = sum(1 for w in negative_words if re.search(rf"\b{w}\b", text_lower))
    total = pos_count + neg_count

    if total == 0:
        return {"label": "neutral", "score": 0.0}

    score = (pos_count - neg_count) / (total + 1)
    if score > 0.2:
        return {"label": "positive", "score": abs(score)}
    elif score < -0.2:
        return {"label": "negative", "score": abs(score)}
    return {"label": "neutral", "score": abs(score)}


def detect_escalation_triggers(query: str) -> list:
    query_lower = query.lower()
    triggers = []

    billing_triggers = ["billing", "bill", "charged", "charge", "payment", "paid",
                         "overcharged", "double charge", "wrong amount", "invoice"]
    refund_triggers = ["refund", "reimburs", "money back", "return", "refund request"]
    legal_triggers = ["legal", "lawyer", "attorney", "lawsuit", "sue",
                       "breach of contract", "legal action", "attorney general"]
    account_sensitive_triggers = ["unauthorized", "hack", "stolen", "fraud",
                                    "identity theft", "security breach", "data breach",
                                    "account takeover"]
    frustration_repeat_triggers = ["repeated", "again", "still not", "never fixed",
                                    "third time", "spoke before", "still broken",
                                    "still happening", "still not working"]

    if any(re.search(rf"\b{re.escape(t)}\b", query_lower) for t in billing_triggers):
        triggers.append("billing_issue")
    if any(re.search(rf"\b{re.escape(t)}\b", query_lower) for t in refund_triggers):
        triggers.append("refund_request")
    if any(re.search(rf"\b{re.escape(t)}\b", query_lower) for t in legal_triggers):
        triggers.append("legal_concern")
    if any(re.search(rf"\b{re.escape(t)}\b", query_lower) for t in account_sensitive_triggers):
        triggers.append("account_sensitive")
    if any(re.search(rf"\b{re.escape(t)}\b", query_lower) for t in frustration_repeat_triggers):
        triggers.append("repeated_frustration")

    return triggers
