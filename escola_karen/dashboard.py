"""Public report schema, history and static-site generation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .core import (
    RegionResult,
    is_target_specialty,
    load_json,
    save_json,
)


SCHEMA_VERSION = 1


def clean_title(value: str) -> str:
    return value.replace("(Obre en una nova finestra)", "").strip()


def run_status(results: list[RegionResult]) -> str:
    successful_documents = [
        document
        for region in results
        if not region.error
        for document in region.documents
        if document.status != "error"
    ]
    problems = any(
        region.error
        or any(document.status == "error" or document.warning for document in region.documents)
        for region in results
    )
    if not successful_documents:
        return "error"
    return "partial" if problems else "success"


def stable_offer_key(offer: dict) -> str:
    explicit = "|".join(
        str(offer.get(field) or "").strip().lower()
        for field in ("region", "document_url", "identifier", "specialty")
    )
    if offer.get("identifier"):
        return explicit
    fallback = "|".join(
        str(offer.get(field) or "").strip().lower()
        for field in (
            "region",
            "document_url",
            "specialty",
            "institution",
            "municipality",
            "vacancies",
        )
    )
    return hashlib.sha256(fallback.encode("utf-8")).hexdigest()


def offer_signature(offer: dict) -> str:
    comparable = {
        key: offer.get(key)
        for key in (
            "specialty",
            "institution",
            "municipality",
            "vacancies",
            "deadline",
        )
    }
    return json.dumps(comparable, ensure_ascii=False, sort_keys=True)


def calculate_changes(
    previous: dict | None,
    current_offers: list[dict],
    ignored_regions: set[str] | None = None,
) -> dict:
    ignored_regions = ignored_regions or set()
    previous_offers = [
        offer
        for offer in (previous or {}).get("offers", [])
        if offer.get("region") not in ignored_regions
    ]
    current_offers = [
        offer for offer in current_offers if offer.get("region") not in ignored_regions
    ]
    old = {
        stable_offer_key(offer): {
            key: value for key, value in offer.items() if key != "detail"
        }
        for offer in previous_offers
    }
    new = {stable_offer_key(offer): offer for offer in current_offers}
    added = [new[key] for key in new.keys() - old.keys()]
    removed = [old[key] for key in old.keys() - new.keys()]
    updated = [
        {"before": old[key], "after": new[key]}
        for key in new.keys() & old.keys()
        if offer_signature(old[key]) != offer_signature(new[key])
    ]
    return {"added": added, "removed": removed, "updated": updated}


def flatten_offers(results: Iterable[RegionResult]) -> list[dict]:
    flattened = []
    for region in results:
        for document in region.documents:
            for offer in document.offers:
                public_offer = asdict(offer)
                public_offer.pop("detail", None)
                flattened.append(
                    {
                        **public_offer,
                        "region": region.name,
                        "region_page_url": region.page_url,
                        "document_title": clean_title(document.title),
                        "document_url": document.url,
                        "document_status": document.status,
                    }
                )
    return flattened


def previous_document_urls(previous: dict | None) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for region in (previous or {}).get("collection", {}).get("regions", []):
        grouped[region.get("name", "")] = {
            document.get("url", "")
            for document in region.get("documents", [])
            if document.get("url")
        }
    return grouped


def document_summary(results: Iterable[RegionResult], previous: dict | None) -> dict:
    results = list(results)
    statuses = Counter(
        document.status for region in results for document in region.documents
    )
    old_urls = previous_document_urls(previous)
    removed = 0
    for region in results:
        if region.error:
            continue
        current_urls = {document.url for document in region.documents}
        removed += len(old_urls.get(region.name, set()) - current_urls)
    return {
        "new": statuses.get("nou", 0),
        "updated": statuses.get("actualitzat", 0),
        "unchanged": statuses.get("sense canvis", 0),
        "error": statuses.get("error", 0),
        "removed": removed,
    }


def vacancies_total(offers: Iterable[dict]) -> float | None:
    values = [offer["vacancies"] for offer in offers if offer.get("vacancies") is not None]
    return sum(values) if values else None


def make_region_payload(region: RegionResult, targets: set[str]) -> dict:
    offers = [
        {
            **asdict(offer),
            "document_url": document.url,
            "document_status": document.status,
        }
        for document in region.documents
        for offer in document.offers
    ]
    specialties = Counter(offer["specialty"] for offer in offers)
    interesting = [
        offer for offer in offers if is_target_specialty(offer["specialty"], targets)
    ]
    warnings = [
        document.warning for document in region.documents if document.warning
    ]
    if region.error:
        warnings.insert(0, region.error)
    return {
        "name": region.name,
        "page_url": region.page_url,
        "offers_count": len(offers),
        "vacancies_total": vacancies_total(offers),
        "top_specialties": [
            {"code": code, "count": count}
            for code, count in specialties.most_common(3)
        ],
        "specialties": dict(specialties.most_common()),
        "interesting_count": len(interesting),
        "interesting_by_specialty": dict(
            Counter(offer["specialty"] for offer in interesting)
        ),
        "documents": [
            {
                "title": clean_title(document.title),
                "url": document.url,
                "status": document.status,
                "note": document.note,
                "warning": document.warning,
            }
            for document in region.documents
        ],
        "warnings": warnings,
        "error": region.error,
    }


def actions_run_url() -> str | None:
    server = os.environ.get("GITHUB_SERVER_URL")
    repository = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repository and run_id:
        return f"{server}/{repository}/actions/runs/{run_id}"
    return None


def build_report(
    results: list[RegionResult],
    targets: set[str],
    now: datetime,
    previous: dict | None = None,
    run_url: str | None = None,
) -> dict:
    status = run_status(results)
    offers = flatten_offers(results)
    specialty_totals = Counter(offer["specialty"] for offer in offers)
    interesting = [
        offer for offer in offers if is_target_specialty(offer["specialty"], targets)
    ]
    regions = [make_region_payload(region, targets) for region in results]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(),
        "status": status,
        "last_successful_at": (
            now.isoformat()
            if status == "success"
            else (previous or {}).get("last_successful_at")
            or (previous or {}).get("generated_at")
        ),
        "actions_run_url": run_url or actions_run_url(),
        "targets": sorted(targets),
        "summary": {
            "offers_count": len(offers),
            "vacancies_total": vacancies_total(offers),
            "active_regions": sum(region["offers_count"] > 0 for region in regions),
            "documents": document_summary(results, previous),
            "top_specialties": [
                {"code": code, "count": count}
                for code, count in specialty_totals.most_common(3)
            ],
            "interesting_count": len(interesting),
            "interesting_by_specialty": dict(
                Counter(offer["specialty"] for offer in interesting)
            ),
        },
        "regions": regions,
        "offers": offers,
        "interesting_offers": interesting,
        "changes": (
            {"added": [], "removed": [], "updated": []}
            if status == "error"
            else calculate_changes(
                previous,
                offers,
                {region.name for region in results if region.error},
            )
        ),
        "collection": {
            "regions": [
                {
                    "name": region.name,
                    "page_url": region.page_url,
                    "documents": [
                        {
                            "title": clean_title(document.title),
                            "url": document.url,
                            "status": document.status,
                        }
                        for document in region.documents
                    ],
                }
                for region in results
            ]
        },
    }


def history_entry(report: dict) -> dict:
    changes = report.get("changes", {})
    return {
        "date": report["generated_at"][:10],
        "generated_at": report["generated_at"],
        "status": report["status"],
        "offers_count": report["summary"]["offers_count"],
        "vacancies_total": report["summary"]["vacancies_total"],
        "interesting_count": report["summary"]["interesting_count"],
        "interesting_by_specialty": report["summary"]["interesting_by_specialty"],
        "changes": {
            "added": len(changes.get("added", [])),
            "removed": len(changes.get("removed", [])),
            "updated": len(changes.get("updated", [])),
        },
    }


def update_history(public_data_dir: Path, report: dict) -> None:
    history_dir = public_data_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    date_key = report["generated_at"][:10]
    save_json(history_dir / f"{date_key}.json", report)
    index_path = history_dir / "index.json"
    existing = load_json(index_path, {"entries": []})
    entries = [
        entry for entry in existing.get("entries", []) if entry.get("date") != date_key
    ]
    entries.append(history_entry(report))
    entries.sort(key=lambda entry: entry["date"], reverse=True)
    save_json(
        index_path,
        {
            "schema_version": SCHEMA_VERSION,
            "updated_at": report["generated_at"],
            "entries": entries[:90],
        },
    )


def persist_dashboard_run(
    results: list[RegionResult],
    targets: set[str],
    now: datetime,
    public_data_dir: Path,
    state_path: Path,
    run_url: str | None = None,
) -> dict:
    previous = load_json(public_data_dir / "latest.json", None)
    report = build_report(results, targets, now, previous, run_url)
    status_payload = {
        "schema_version": SCHEMA_VERSION,
        "attempted_at": now.isoformat(),
        "status": report["status"],
        "last_successful_at": report.get("last_successful_at"),
        "actions_run_url": report.get("actions_run_url"),
        "errors": [
            {"region": region.name, "message": region.error}
            for region in results
            if region.error
        ]
        + [
            {"region": region.name, "message": document.warning}
            for region in results
            for document in region.documents
            if document.warning
        ],
    }
    save_json(public_data_dir / "status.json", status_payload)
    update_history(public_data_dir, report)
    if report["status"] != "error" or previous is None:
        save_json(public_data_dir / "latest.json", report)
    old_state = load_json(state_path, {"documents": {}})
    merged_documents = dict(old_state.get("documents", {}))
    for region in results:
        if region.error:
            continue
        current_urls = {document.url for document in region.documents}
        merged_documents = {
            url: value
            for url, value in merged_documents.items()
            if value.get("region") != region.name or url in current_urls
        }
        for document in region.documents:
            if document.sha256:
                merged_documents[document.url] = {
                    "sha256": document.sha256,
                    "last_seen": now.isoformat(),
                    "region": region.name,
                }
    save_json(
        state_path,
        {"last_run": now.isoformat(), "documents": merged_documents},
    )
    return report


def build_static_site(source_dir: Path, public_data_dir: Path, output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    for name in ("index.html", "styles.css", "app.js"):
        shutil.copy2(source_dir / name, output_dir / name)
    font = source_dir / "assets" / "source-sans-3-latin.woff2"
    if font.exists():
        assets = output_dir / "assets"
        assets.mkdir()
        shutil.copy2(font, assets / font.name)
    shutil.copytree(public_data_dir, output_dir / "data")
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
