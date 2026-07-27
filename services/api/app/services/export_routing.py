from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from services.api.app.domain.contracts import ApiError, ErrorCategory, ThreadSnapshot
from services.api.app.domain.export_package import (
    ExportCategory,
    ExportFolderLayout,
    ExportRoute,
    category_first_route,
    domain_first_route,
    normalize_route_segment,
)


class ExportRouteReason:
    SENDER_DOMAIN = "sender_domain"
    SENDER_DOMAIN_OVERRIDE = "sender_domain_override"
    REVIEW_FIRST_CATEGORY = "review_first_category"


@dataclass(frozen=True)
class ExportRoutingPlan:
    thread_id: str
    gmail_thread_id: str
    sender_domain: str
    category: ExportCategory
    layout: ExportFolderLayout
    route: ExportRoute
    reason: str


def plan_export_route(
    thread: ThreadSnapshot,
    category: ExportCategory,
    layout: ExportFolderLayout = ExportFolderLayout.DOMAIN_FIRST,
    sender_domain_override: str | None = None,
) -> ExportRoutingPlan:
    """Choose the export folder route for a thread before files are written."""

    sender_domain = (
        normalize_sender_domain(sender_domain_override)
        if sender_domain_override
        else primary_sender_domain(thread)
    )
    reason = ExportRouteReason.SENDER_DOMAIN_OVERRIDE if sender_domain_override else ExportRouteReason.SENDER_DOMAIN
    effective_layout = layout

    if layout == ExportFolderLayout.CATEGORY_FIRST:
        route = category_first_route(sender_domain, category)
    elif layout == ExportFolderLayout.MIXED:
        if category in {ExportCategory.NEEDS_REVIEW, ExportCategory.UNKNOWN}:
            route = category_first_route(sender_domain, category)
            reason = ExportRouteReason.REVIEW_FIRST_CATEGORY
        else:
            route = domain_first_route(sender_domain, category)
    else:
        route = domain_first_route(sender_domain, category)

    return ExportRoutingPlan(
        thread_id=thread.thread_id,
        gmail_thread_id=thread.gmail_thread_id,
        sender_domain=sender_domain,
        category=category,
        layout=effective_layout,
        route=route,
        reason=reason,
    )


def primary_sender_domain(thread: ThreadSnapshot) -> str:
    if not thread.messages:
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Thread must include messages for export routing.", "thread.messages")

    ordered_domains = tuple(normalize_sender_domain(message.from_participant.email) for message in thread.messages)
    counts = Counter(ordered_domains)
    return max(ordered_domains, key=lambda domain: (counts[domain], -ordered_domains.index(domain)))


def normalize_sender_domain(email_or_domain: str) -> str:
    raw = email_or_domain.strip().lower()
    if "@" in raw:
        raw = raw.rsplit("@", 1)[1]
    raw = raw.strip(" <>.,;:")
    domain = normalize_route_segment(raw)
    if "." not in domain:
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Sender domain must include a dot.", "sender_domain")
    return domain
