from agent.intent import IntentClassifier
from domain.chat import ChatMessage
from domain.intent import QueryIntent


def test_intent_classifier_explain() -> None:
    classifier = IntentClassifier()
    assert classifier.classify("What is S3?") == QueryIntent.EXPLAIN


def test_intent_classifier_compare() -> None:
    classifier = IntentClassifier()
    assert classifier.classify("How is it different from EFS?") == QueryIntent.COMPARE


def test_intent_classifier_summarize() -> None:
    classifier = IntentClassifier()
    assert classifier.classify("Summarize our discussion") == QueryIntent.SUMMARIZE_CONVERSATION


def test_intent_classifier_summarize_follow_up() -> None:
    classifier = IntentClassifier()
    history = [ChatMessage(role="assistant", content="Bedrock Guardrails restrict model outputs.")]
    assert classifier.classify("Can you summarize that?", history) == QueryIntent.SUMMARIZE_CONVERSATION


def test_intent_classifier_how_to() -> None:
    classifier = IntentClassifier()
    assert classifier.classify("How do I secure S3?") == QueryIntent.HOW_TO


def test_intent_classifier_troubleshoot() -> None:
    classifier = IntentClassifier()
    assert classifier.classify("My Lambda is timing out") == QueryIntent.TROUBLESHOOT
