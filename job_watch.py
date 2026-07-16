#!/usr/bin/env python3
"""Local Catalan e-mail report for difficult-to-fill teaching vacancies."""

from __future__ import annotations

import argparse
import html
import os
import smtplib
import subprocess
import sys
from collections import Counter
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from escola_karen.core import (
    Offer,
    RegionResult,
    analyze_region,
    build_document_state,
    is_blank_offer_template,
    is_target_specialty,
    load_json,
    parse_offers,
    results_to_dicts,
    save_json,
    specialty_counts,
)


ROOT = Path(__file__).resolve().parent
PUBLIC_CONFIG_PATH = ROOT / "config.json"
EMAIL_CONFIG_PATH = ROOT / "email_config.local.json"
STATE_PATH = ROOT / "data" / "email-state.json"
REPORTS_DIR = ROOT / "reports"
KEYCHAIN_SERVICE = "escola-karen-gmail"


def format_decimal(value: float) -> str:
    return f"{value:g}".replace(".", ",")


def format_offer_count(count: int) -> str:
    return f"{count} oferta" if count == 1 else f"{count} ofertes"


def format_vacancies(offers: list[Offer]) -> str:
    values = [offer.vacancies for offer in offers if offer.vacancies is not None]
    if not values:
        return "nombre de places no especificat"
    total = sum(values)
    label = "plaça" if total == 1 else "places"
    return f"{format_decimal(total)} {label}"


def clean_document_title(title: str) -> str:
    return title.replace("(Obre en una nova finestra)", "").strip()


def render_reports(
    results: list[RegionResult], targets: set[str], now: datetime
) -> tuple[str, str]:
    date_label = now.strftime("%d/%m/%Y")
    targeted = [
        (region, offer)
        for region in results
        for offer in region.offers
        if is_target_specialty(offer.specialty, targets)
    ]
    summary = (
        f"S’han detectat {format_offer_count(len(targeted))} GE/CLA."
        if targeted
        else "Avui no s’ha detectat cap oferta GE o CLA."
    )
    plain = [f"Seguiment d’ofertes docents — {date_label}", "", summary, ""]
    cards = []

    for region in results:
        counts = specialty_counts(region.offers)
        top = ", ".join(
            f"{code} ({count})" for code, count in counts.most_common(3)
        ) or "cap"
        region_targets = [
            offer
            for offer in region.offers
            if is_target_specialty(offer.specialty, targets)
        ]
        statuses = Counter(document.status for document in region.documents)
        status_text = ", ".join(
            f"{count} {status}" for status, count in statuses.items()
        )
        region_summary = (
            f"{format_offer_count(len(region.offers))}, "
            f"{format_vacancies(region.offers)}. "
            f"Especialitats predominants: {top}."
        )
        plain.extend([region.name, region_summary])
        if status_text:
            plain.append(f"Documents: {status_text}.")
        if region.error:
            plain.append(f"ERROR: {region.error}")
        for offer in region_targets:
            plain.append(
                f"- {offer.specialty} — {offer.identifier}"
                + (
                    f", {format_decimal(offer.vacancies)} places"
                    if offer.vacancies is not None
                    else ""
                )
            )
        for document in region.documents:
            plain.append(f"PDF ({document.status}): {document.url}")
            if document.warning:
                plain.append(f"Avís: {document.warning}")
            if document.note:
                plain.append(f"Nota: {document.note}")
        plain.append("")

        target_markup = "".join(
            "<li><strong>"
            f"{html.escape(offer.specialty)} — {html.escape(offer.identifier)}"
            "</strong>"
            + (
                f" · {html.escape(format_decimal(offer.vacancies))} places"
                if offer.vacancies is not None
                else ""
            )
            + "</li>"
            for offer in region_targets
        )
        document_markup = "".join(
            "<li>"
            f"<a href='{html.escape(document.url, quote=True)}'>"
            f"{html.escape(clean_document_title(document.title))}</a>"
            f" <span class='badge'>{html.escape(document.status)}</span>"
            + (
                f"<div class='warning'><strong>Avís:</strong> "
                f"{html.escape(document.warning)}</div>"
                if document.warning
                else ""
            )
            + (
                f"<div class='note'><strong>Nota:</strong> "
                f"{html.escape(document.note)}</div>"
                if document.note
                else ""
            )
            + "</li>"
            for document in region.documents
        )
        cards.append(
            "<section class='card'>"
            f"<h2>{html.escape(region.name)}</h2>"
            f"<p class='metric'>{html.escape(region_summary)}</p>"
            + (
                f"<p class='error'><strong>Error:</strong> "
                f"{html.escape(region.error)}</p>"
                if region.error
                else ""
            )
            + (
                "<h3>Ofertes GE / CLA</h3><ul>"
                f"{target_markup}</ul>"
                if region_targets
                else "<p>Cap oferta GE o CLA.</p>"
            )
            + f"<ul class='documents'>{document_markup}</ul></section>"
        )

    accent = "positive" if targeted else "neutral"
    rich = f"""<!doctype html>
<html lang="ca">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body{{margin:0;background:#f1f5f6;color:#18313f;font-family:Arial,sans-serif}}
    .shell{{max-width:680px;margin:auto;padding:24px 12px}}
    header{{background:#123c4a;color:white;padding:28px;border-radius:16px 16px 0 0}}
    main{{background:white;padding:20px;border-radius:0 0 16px 16px}}
    .summary{{padding:16px;border-radius:10px;background:#edf3f4;border-left:4px solid #718b94}}
    .summary.positive{{background:#e6f4ef;border-color:#17815f}}
    .card{{border:1px solid #d9e3e6;border-radius:12px;padding:18px;margin-top:16px}}
    h1{{font-size:26px;margin:4px 0}} h2{{color:#123c4a}} h3{{font-size:14px}}
    a{{color:#086b83}} li{{margin:8px 0}} .badge{{font-size:11px;background:#edf1f3;padding:3px 7px;border-radius:999px}}
    .warning{{background:#fff4db;color:#704708;padding:8px;margin-top:6px}} .note{{color:#526973;margin-top:6px}}
    .error{{background:#fdecec;color:#862525;padding:10px}} .metric{{line-height:1.6}}
    @media(max-width:520px){{header,main{{padding:18px}}}}
  </style>
</head>
<body><div class="shell">
  <header><small>INFORME DIARI</small><h1>Seguiment d’ofertes docents</h1><div>{date_label} · Especialitats GE i CLA</div></header>
  <main><div class="summary {accent}"><strong>{html.escape(summary)}</strong></div>
  {''.join(cards)}
  </main>
</div></body></html>"""
    return "\n".join(plain), rich


def get_gmail_password(sender: str) -> str:
    environment_password = os.environ.get("GMAIL_APP_PASSWORD")
    if environment_password:
        return environment_password.replace(" ", "")
    process = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            sender,
            "-w",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return process.stdout.strip().replace(" ", "")


def send_email(sender: str, recipient: str, subject: str, plain: str, rich: str) -> None:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(plain)
    message.add_alternative(rich, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(sender, get_gmail_password(sender))
        smtp.send_message(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Crea l’informe sense enviar-lo")
    args = parser.parse_args()

    public_config = load_json(PUBLIC_CONFIG_PATH, {})
    email_config = load_json(EMAIL_CONFIG_PATH, {})
    if not args.dry_run and not email_config:
        raise SystemExit(
            "Falta email_config.local.json. Copieu email_config.example.json i completeu-lo."
        )

    old_state = load_json(STATE_PATH, {"documents": {}})
    now = datetime.now().astimezone()
    results = [
        analyze_region(name, url, old_state)
        for name, url in public_config["regions"].items()
    ]
    targets = set(public_config["specialties_of_interest"])
    plain, rich = render_reports(results, targets, now)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = REPORTS_DIR / f"informe-{now:%Y-%m-%d}"
    stem.with_suffix(".txt").write_text(plain, encoding="utf-8")
    stem.with_suffix(".html").write_text(rich, encoding="utf-8")
    save_json(
        stem.with_suffix(".json"),
        {"generated_at": now.isoformat(), "regions": results_to_dicts(results)},
    )

    if not args.dry_run:
        count = sum(
            is_target_specialty(offer.specialty, targets)
            for region in results
            for offer in region.offers
        )
        send_email(
            email_config["sender"],
            email_config["recipient"],
            f"Seguiment docent — {format_offer_count(count)} GE/CLA — {now:%d/%m/%Y}",
            plain,
            rich,
        )
        save_json(STATE_PATH, build_document_state(results, now))

    print(plain)
    print(f"\nInforme desat: {stem.with_suffix('.txt')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
