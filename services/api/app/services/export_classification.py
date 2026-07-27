from __future__ import annotations

from dataclasses import dataclass

from services.api.app.domain.contracts import MessageHeader, MessageSnapshot, ThreadSnapshot
from services.api.app.domain.export_package import ExportCategory


class ClassificationReason:
    NEWSLETTER_HEADER = "newsletter_header"
    AUTOMATED_HEADER = "automated_header"
    NO_REPLY_SENDER = "no_reply_sender"
    BANK_KEYWORD = "bank_keyword"
    HUMAN_QUESTION = "human_question"
    ATTACHMENT_COUNT = "attachment_count"
    UNKNOWN = "unknown"


REVIEW_REQUIRED_CATEGORIES = {
    ExportCategory.BANK_FINANCIAL,
    ExportCategory.HUMAN,
    ExportCategory.NEEDS_REVIEW,
    ExportCategory.ATTACHMENTS_HEAVY,
    ExportCategory.UNKNOWN,
}


@dataclass(frozen=True)
class ClassificationEvidence:
    reason: str
    detail: str


@dataclass(frozen=True)
class ClassificationResult:
    category: ExportCategory
    evidence: tuple[ClassificationEvidence, ...]

    @property
    def review_required(self) -> bool:
        return self.category in REVIEW_REQUIRED_CATEGORIES


def classify_thread(thread: ThreadSnapshot) -> ClassificationResult:
    """Classify a thread using deterministic, explainable local rules."""

    messages = thread.messages
    all_headers = tuple(header for message in messages for header in message.headers)
    all_from_addresses = tuple(message.from_participant.email.lower() for message in messages)
    all_text = " ".join(
        (
            thread.subject,
            *(message.from_participant.display_name or "" for message in messages),
            *(body.content for message in messages for body in message.bodies),
        )
    ).lower()
    attachment_count = sum(len(message.attachments) for message in messages)

    newsletter = _newsletter_evidence(all_headers)
    if newsletter:
        return ClassificationResult(ExportCategory.NEWSLETTER, newsletter)

    automated = _automated_evidence(all_headers, all_from_addresses)
    if automated:
        return ClassificationResult(ExportCategory.AUTOMATED, automated)

    bank = _bank_evidence(all_text)
    if bank:
        return ClassificationResult(ExportCategory.BANK_FINANCIAL, bank)

    if attachment_count >= 3:
        return ClassificationResult(
            ExportCategory.ATTACHMENTS_HEAVY,
            (
                ClassificationEvidence(
                    ClassificationReason.ATTACHMENT_COUNT,
                    f"{attachment_count} attachments",
                ),
            ),
        )

    human = _human_evidence(messages, all_text)
    if human:
        return ClassificationResult(ExportCategory.HUMAN, human)

    return ClassificationResult(
        ExportCategory.UNKNOWN,
        (ClassificationEvidence(ClassificationReason.UNKNOWN, "No deterministic classifier rule matched."),),
    )


def _newsletter_evidence(headers: tuple[MessageHeader, ...]) -> tuple[ClassificationEvidence, ...]:
    evidence: list[ClassificationEvidence] = []
    for header in headers:
        name = header.name.lower()
        if name in {"list-id", "list-unsubscribe"}:
            evidence.append(ClassificationEvidence(ClassificationReason.NEWSLETTER_HEADER, header.name))
    return tuple(evidence)


def _automated_evidence(
    headers: tuple[MessageHeader, ...],
    from_addresses: tuple[str, ...],
) -> tuple[ClassificationEvidence, ...]:
    evidence: list[ClassificationEvidence] = []
    for header in headers:
        name = header.name.lower()
        value = header.value.lower()
        if name == "auto-submitted" and value not in {"", "no"}:
            evidence.append(ClassificationEvidence(ClassificationReason.AUTOMATED_HEADER, f"{header.name}: {header.value}"))
        if name == "x-auto-response-suppress":
            evidence.append(ClassificationEvidence(ClassificationReason.AUTOMATED_HEADER, header.name))
    if any(address.split("@", 1)[0] in {"no-reply", "noreply", "donotreply", "do-not-reply"} for address in from_addresses):
        evidence.append(ClassificationEvidence(ClassificationReason.NO_REPLY_SENDER, "Sender address is no-reply style."))
    return tuple(evidence)


def _bank_evidence(text: str) -> tuple[ClassificationEvidence, ...]:
    for keyword in ("bank", "financial", "secure notice", "account alert"):
        if keyword in text:
            return (ClassificationEvidence(ClassificationReason.BANK_KEYWORD, keyword),)
    return ()


def _human_evidence(
    messages: tuple[MessageSnapshot, ...],
    text: str,
) -> tuple[ClassificationEvidence, ...]:
    if "?" in text or any(phrase in text for phrase in ("could you", "can you", "when you have a moment")):
        if not any(message.from_participant.email.lower().split("@", 1)[0] in {"no-reply", "noreply"} for message in messages):
            return (ClassificationEvidence(ClassificationReason.HUMAN_QUESTION, "Message asks for user attention."),)
    return ()
