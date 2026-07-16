"""Shared engine for the Escola Karen vacancy monitors."""

from .core import (
    DocumentResult,
    Offer,
    RegionResult,
    analyze_region,
    build_document_state,
    clean_specialty,
    document_status,
    edubcn_deadline,
    edubcn_vacancies,
    is_blank_offer_template,
    is_target_specialty,
    load_json,
    parse_offers,
    save_json,
    specialty_counts,
)

__all__ = [
    "DocumentResult",
    "Offer",
    "RegionResult",
    "analyze_region",
    "build_document_state",
    "clean_specialty",
    "document_status",
    "edubcn_deadline",
    "edubcn_vacancies",
    "is_blank_offer_template",
    "is_target_specialty",
    "load_json",
    "parse_offers",
    "save_json",
    "specialty_counts",
]
