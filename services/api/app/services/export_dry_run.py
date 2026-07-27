from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from services.api.app.domain.contracts import ThreadSnapshot
from services.api.app.domain.export_package import ExportFolderLayout, ExportPackageMode
from services.api.app.services.export_classification import ClassificationEvidence, classify_thread
from services.api.app.services.export_routing import ExportRoutingPlan, plan_export_route


class PlannedGmailAction(StrEnum):
    EXPORT_ONLY = "export_only"
    LABEL_ONLY = "label_only"
    LABEL_ARCHIVE = "label_archive"
    LABEL_MARK_READ = "label_mark_read"
    LABEL_MARK_READ_ARCHIVE = "label_mark_read_archive"
    NEEDS_REVIEW = "needs_review"
    TRASH_REVIEW_QUEUE = "trash_review_queue"


@dataclass(frozen=True)
class ExportDryRunItem:
    thread_id: str
    gmail_thread_id: str
    subject: str
    category: str
    sender_domain: str
    export_path: str
    route: ExportRoutingPlan
    evidence: tuple[ClassificationEvidence, ...]
    review_required: bool
    planned_gmail_action: PlannedGmailAction


@dataclass(frozen=True)
class ExportDryRunSummary:
    total_threads: int
    review_required_count: int
    by_category: dict[str, int]
    by_sender_domain: dict[str, int]
    by_export_path: dict[str, int]
    by_gmail_action: dict[str, int]


@dataclass(frozen=True)
class ExportDryRunPlan:
    mode: ExportPackageMode
    layout: ExportFolderLayout
    label_name: str
    mark_read: bool
    archive: bool
    items: tuple[ExportDryRunItem, ...]
    summary: ExportDryRunSummary


def plan_export_dry_run(
    threads: Iterable[ThreadSnapshot],
    mode: ExportPackageMode = ExportPackageMode.PRESERVE,
    layout: ExportFolderLayout = ExportFolderLayout.DOMAIN_FIRST,
    label_name: str = "EmailVault/Vaulted",
    mark_read: bool = False,
    archive: bool = True,
    sender_domain_overrides: dict[str, str] | None = None,
) -> ExportDryRunPlan:
    """Preview export routing and Gmail actions without writing files or mutating Gmail."""

    override_by_thread = sender_domain_overrides or {}
    items = tuple(
        _plan_item(
            thread,
            mode=mode,
            layout=layout,
            mark_read=mark_read,
            archive=archive,
            sender_domain_override=override_by_thread.get(thread.thread_id)
            or override_by_thread.get(thread.gmail_thread_id),
        )
        for thread in threads
    )
    return ExportDryRunPlan(
        mode=mode,
        layout=layout,
        label_name=label_name,
        mark_read=mark_read,
        archive=archive,
        items=items,
        summary=_summarize(items),
    )


def _plan_item(
    thread: ThreadSnapshot,
    mode: ExportPackageMode,
    layout: ExportFolderLayout,
    mark_read: bool,
    archive: bool,
    sender_domain_override: str | None,
) -> ExportDryRunItem:
    classification = classify_thread(thread)
    route = plan_export_route(
        thread,
        classification.category,
        layout=layout,
        sender_domain_override=sender_domain_override,
    )
    review_required = classification.review_required or mode == ExportPackageMode.FREE_SPACE
    action = _planned_gmail_action(
        mode,
        risky_or_unknown=classification.review_required,
        mark_read=mark_read,
        archive=archive,
    )
    return ExportDryRunItem(
        thread_id=thread.thread_id,
        gmail_thread_id=thread.gmail_thread_id,
        subject=thread.subject,
        category=classification.category.value,
        sender_domain=route.sender_domain,
        export_path=route.route.relative_path,
        route=route,
        evidence=classification.evidence,
        review_required=review_required,
        planned_gmail_action=action,
    )


def _planned_gmail_action(
    mode: ExportPackageMode,
    risky_or_unknown: bool,
    mark_read: bool,
    archive: bool,
) -> PlannedGmailAction:
    if mode == ExportPackageMode.PRESERVE:
        return PlannedGmailAction.EXPORT_ONLY

    if mode == ExportPackageMode.FREE_SPACE:
        return PlannedGmailAction.NEEDS_REVIEW if risky_or_unknown else PlannedGmailAction.TRASH_REVIEW_QUEUE

    if risky_or_unknown:
        return PlannedGmailAction.NEEDS_REVIEW
    if mark_read and archive:
        return PlannedGmailAction.LABEL_MARK_READ_ARCHIVE
    if mark_read:
        return PlannedGmailAction.LABEL_MARK_READ
    if archive:
        return PlannedGmailAction.LABEL_ARCHIVE
    return PlannedGmailAction.LABEL_ONLY


def _summarize(items: tuple[ExportDryRunItem, ...]) -> ExportDryRunSummary:
    return ExportDryRunSummary(
        total_threads=len(items),
        review_required_count=sum(1 for item in items if item.review_required),
        by_category=_counts(item.category for item in items),
        by_sender_domain=_counts(item.sender_domain for item in items),
        by_export_path=_counts(item.export_path for item in items),
        by_gmail_action=_counts(item.planned_gmail_action.value for item in items),
    )


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))
