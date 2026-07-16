"""Collection, PDF extraction and parsing shared by e-mail and dashboard."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 EscolaKarenJobWatch/2.0"
)


@dataclass
class Offer:
    identifier: str
    specialty: str
    institution: str | None = None
    municipality: str | None = None
    vacancies: float | None = None
    deadline: str | None = None
    detail: str = ""


@dataclass
class DocumentResult:
    title: str
    url: str
    status: str
    sha256: str
    offers: list[Offer]
    note: str = ""
    warning: str = ""


@dataclass
class RegionResult:
    name: str
    page_url: str
    documents: list[DocumentResult]
    error: str = ""

    @property
    def offers(self) -> list[Offer]:
        return [offer for document in self.documents for offer in document.offers]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def results_from_dicts(values: list[dict]) -> list[RegionResult]:
    results = []
    for region in values:
        documents = []
        for document in region.get("documents", []):
            offers = [
                Offer(
                    identifier=offer.get("identifier", ""),
                    specialty=offer.get("specialty", "No especificada"),
                    institution=offer.get("institution"),
                    municipality=offer.get("municipality"),
                    vacancies=offer.get("vacancies"),
                    deadline=offer.get("deadline"),
                    detail=offer.get("detail", ""),
                )
                for offer in document.get("offers", [])
            ]
            documents.append(
                DocumentResult(
                    title=document.get("title", ""),
                    url=document.get("url", ""),
                    status=document.get("status", "sense canvis"),
                    sha256=document.get("sha256", ""),
                    offers=offers,
                    note=document.get("note", ""),
                    warning=document.get("warning", ""),
                )
            )
        results.append(
            RegionResult(
                name=region.get("name", ""),
                page_url=region.get("page_url", ""),
                documents=documents,
                error=region.get("error", ""),
            )
        )
    return results


def results_to_dicts(results: Iterable[RegionResult]) -> list[dict]:
    return [asdict(result) for result in results]


def http_get(url: str, timeout: int = 40) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def find_offer_pdfs(page_url: str) -> list[tuple[str, str]]:
    parser = LinkParser()
    parser.feed(http_get(page_url).decode("utf-8", errors="replace"))
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for href, title in parser.links:
        absolute = urllib.parse.urljoin(page_url, href)
        parsed = urllib.parse.urlparse(absolute)
        filename = Path(parsed.path).name.lower()
        path = parsed.path.lower()
        if not filename.endswith(".pdf") or "/secundaria/" not in path:
            continue
        if not re.search(r"oferta|vacant|pendent", filename):
            continue
        if re.search(r"cobertes|resultat|adjudic", filename):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        found.append((absolute, title or Path(parsed.path).stem))
    return found


def pdf_to_text(pdf_path: Path) -> str:
    executable = shutil.which("pdftotext")
    if not executable:
        raise RuntimeError("No s’ha trobat pdftotext. Cal instal·lar Poppler.")
    process = subprocess.run(
        [executable, "-layout", str(pdf_path), "-"],
        check=True,
        capture_output=True,
    )
    return process.stdout.decode("utf-8", errors="replace")


def normalize_specialty(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def is_target_specialty(value: str, targets: Iterable[str]) -> bool:
    normalized_targets = {normalize_specialty(target) for target in targets}
    return normalize_specialty(value) in normalized_targets


def clean_specialty(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" :-")
    if not value:
        return "No especificada"
    match = re.match(r"([A-ZÀ-Ü]{2,5}|[A-Z]\d{2}|\d{3})\b", value, re.I)
    return match.group(1).upper() if match else value[:60]


def specialty_from_fragment(value: str) -> str | None:
    value = re.sub(r"\s+", " ", value).strip(" :-")
    if not value:
        return None
    match = re.search(
        r"(?:^|[^A-ZÀ-Ü0-9])"
        r"([A-ZÀ-Ü]{2,5}|[A-Z]\d{2}|\d{3})"
        r"(?=\s|[-–—]|$)",
        value,
    )
    return match.group(1).upper() if match else None


def parse_number(value: str) -> float | None:
    match = re.search(r"(?<!\d)(\d+(?:[,.]\d+)?)(?!\d)", value)
    return float(match.group(1).replace(",", ".")) if match else None


def left_field(line: str) -> str:
    return re.split(r"\s{3,}", line.strip(), maxsplit=1)[0].strip()


def clean_text(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", value).strip(" :-")
    return cleaned or None


def labelled_field(block: str, labels: Iterable[str]) -> str | None:
    alternatives = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?:{alternatives})\s*:\s*([^\n]+)", block, re.I
    )
    return clean_text(left_field(match.group(1))) if match else None


DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"
    r"|\b(\d{1,2}\s+(?:de\s+)?(?:gener|febrer|març|abril|maig|juny|"
    r"juliol|agost|setembre|octubre|novembre|desembre)\s+(?:de\s+)?\d{4})\b",
    re.I,
)


def extract_deadline(value: str) -> str | None:
    context = re.search(
        r"(?:data\s+l[ií]mit|termini|presentaci[oó]\s+de\s+sol[·l]licituds)"
        r"[\s\S]{0,180}",
        value,
        re.I,
    )
    match = DATE_PATTERN.search(context.group(0) if context else value)
    return clean_text(match.group(0)) if match else None


def parse_form_offers(text: str) -> list[Offer]:
    matches = list(
        re.finditer(
            r"Identificador\s+de\s+la\s+pla[çc]a\s*:\s*([^\n]+)", text, re.I
        )
    )
    offers: list[Offer] = []
    for index, match in enumerate(matches):
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start() : block_end]
        identifier = left_field(match.group(1))
        specialty = "No especificada"
        lines = block.splitlines()
        for line_index, line in enumerate(lines):
            specialty_match = re.search(r"Especialitat\s*:\s*(.*)", line, re.I)
            if not specialty_match:
                continue
            inline = re.split(
                r"Presentaci[oó]\s+de\s+sol",
                specialty_match.group(1),
                maxsplit=1,
                flags=re.I,
            )[0]
            candidate = clean_text(left_field(inline))
            if not candidate:
                candidate = next(
                    (
                        clean_text(left_field(following))
                        for following in lines[line_index + 1 : line_index + 4]
                        if clean_text(left_field(following))
                    ),
                    None,
                )
            specialty = candidate or specialty
            break
        vacancy_match = re.search(
            r"\s(\d+(?:[,.]\d+)?)\s+Vacants?\b", identifier, re.I
        )
        vacancy = (
            float(vacancy_match.group(1).replace(",", ".")) if vacancy_match else 1.0
        )
        offers.append(
            Offer(
                identifier=identifier,
                specialty=clean_specialty(specialty),
                institution=labelled_field(
                    block, ("Nom del centre", "Centre", "Nom centre")
                ),
                municipality=labelled_field(block, ("Municipi", "Localitat")),
                vacancies=vacancy,
                deadline=extract_deadline(block),
                detail=" ".join(lines[:12]).strip()[:500],
            )
        )
    return offers


ROW_START = re.compile(r"^\s*(\d{1,8}(?:-\d{5,8})?)\s+")


def column_position(lines: list[str], *labels: str) -> int | None:
    for line in lines:
        lowered = line.lower()
        positions = [lowered.find(label.lower()) for label in labels]
        positions = [position for position in positions if position >= 0]
        if positions:
            return min(positions)
    return None


def next_column(lines: list[str], start: int, labels: Iterable[str]) -> int | None:
    positions = []
    for label in labels:
        position = column_position(lines, label)
        if position is not None and position > start:
            positions.append(position)
    return min(positions) if positions else None


def joined_slice(lines: list[str], start: int | None, end: int | None) -> str | None:
    if start is None:
        return None
    values = [clean_text(line[start:end]) for line in lines]
    return clean_text(" ".join(value for value in values if value))


def parse_table_offers(text: str) -> list[Offer]:
    lines = text.splitlines()
    offers: list[Offer] = []
    columns: dict[str, tuple[int | None, int | None]] = {}
    row_lines: list[str] = []
    identifier = ""
    document_deadline = extract_deadline(text[:2500])

    def finish_row() -> None:
        nonlocal row_lines, identifier
        specialty_start, specialty_end = columns.get("specialty", (None, None))
        if not row_lines or specialty_start is None:
            row_lines = []
            identifier = ""
            return
        specialty = next(
            (
                parsed
                for line in row_lines
                if (
                    parsed := specialty_from_fragment(
                        line[max(0, specialty_start - 6) : specialty_end]
                    )
                )
            ),
            "No especificada",
        )
        vacancies_start, vacancies_end = columns.get("vacancies", (None, None))
        vacancies = None
        if vacancies_start is not None:
            vacancies = next(
                (
                    parsed
                    for line in row_lines
                    if (
                        parsed := parse_number(line[vacancies_start:vacancies_end])
                    )
                    is not None
                ),
                None,
            )
        institution = joined_slice(row_lines, *columns.get("institution", (None, None)))
        municipality = joined_slice(
            row_lines, *columns.get("municipality", (None, None))
        )
        offers.append(
            Offer(
                identifier=identifier,
                specialty=specialty,
                institution=institution,
                municipality=municipality,
                vacancies=vacancies,
                deadline=document_deadline,
                detail=" ".join(part.strip() for part in row_lines if part.strip())[:500],
            )
        )
        row_lines = []
        identifier = ""

    for line_index, line in enumerate(lines):
        lowered = line.lower()
        is_header = (
            "especialitat" in lowered
            and "identificador de la plaça:" not in lowered
            and any(marker in lowered for marker in ("identificador", "codi centre", "municipi"))
        )
        if is_header:
            finish_row()
            header_lines = lines[line_index : line_index + 3]
            specialty_start = column_position(header_lines, "especialitat")
            institution_start = column_position(
                header_lines, "nom centre", "nom del centre"
            )
            municipality_start = column_position(header_lines, "municipi", "localitat")
            vacancies_start = column_position(header_lines, "vacants", "places")
            if specialty_start is not None:
                columns["specialty"] = (
                    specialty_start,
                    next_column(
                        header_lines,
                        specialty_start,
                        ("qualificador", "perfil", "cos", "vacants", "observacions", "correu"),
                    ),
                )
            if institution_start is not None:
                columns["institution"] = (
                    institution_start,
                    municipality_start or specialty_start,
                )
            if municipality_start is not None:
                columns["municipality"] = (municipality_start, specialty_start)
            if vacancies_start is not None:
                columns["vacancies"] = (
                    vacancies_start,
                    next_column(
                        header_lines,
                        vacancies_start,
                        ("observacions", "correu", "presentació"),
                    ),
                )
            continue

        row_match = ROW_START.match(line)
        if row_match and "specialty" in columns:
            finish_row()
            identifier = row_match.group(1)
            row_lines = [line]
        elif row_lines:
            row_lines.append(line)
    finish_row()
    return offers


def parse_offers(text: str) -> list[Offer]:
    return parse_form_offers(text) or parse_table_offers(text)


def is_blank_offer_template(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).lower()
    required_labels = (
        "identificador de la plaça",
        "especialitat",
        "nom del centre",
        "municipi",
        "jornada",
    )
    return all(label in normalized for label in required_labels)


def document_status(url: str, digest: str, old_state: dict) -> str:
    previous = old_state.get("documents", {}).get(url)
    if not previous:
        return "nou"
    if previous.get("sha256") != digest:
        return "actualitzat"
    return "sense canvis"


def edubcn_api_url(page_url: str) -> str:
    parsed = urllib.parse.urlparse(page_url)
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, "/pdc_rest/convocatories/ca", "", "", "")
    )


def edubcn_deadline(entry: dict, today: date) -> date | None:
    value = str(entry.get("INFO_TERMINI", ""))
    match = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", value)
    if not match:
        return None
    day, month = int(match.group(1)), int(match.group(2))
    raw_year = match.group(3)
    if raw_year:
        year = int(raw_year)
        if year < 100:
            year += 2000
    else:
        publication_match = re.match(r"(\d{4})-", str(entry.get("DATA", "")))
        year = int(publication_match.group(1)) if publication_match else today.year
    try:
        return date(year, month, day)
    except ValueError:
        return None


def edubcn_vacancies(profile: str) -> float:
    match = re.search(
        r"\((\d+(?:[,.]\d+)?)\s+(?:vacants?|places?)\)", profile, re.I
    )
    return float(match.group(1).replace(",", ".")) if match else 1.0


def analyze_edubcn_region(
    name: str, page_url: str, old_state: dict, today: date
) -> RegionResult:
    result = RegionResult(name=name, page_url=page_url, documents=[])
    try:
        payload = json.loads(http_get(edubcn_api_url(page_url)).decode("utf-8"))
        for entry in payload:
            deadline = edubcn_deadline(entry, today)
            if deadline is not None and deadline < today:
                continue
            if not entry.get("DOC_CONVOCATORIA"):
                continue

            url = urllib.parse.urljoin(page_url, str(entry["DOC_CONVOCATORIA"]))
            profile = re.sub(r"\s+", " ", str(entry.get("PERFIL", ""))).strip()
            identifier = str(entry.get("CODI") or entry.get("ID") or profile)
            institution = " ".join(
                value
                for value in (
                    str(entry.get("CENTRE", "")).strip(),
                    str(entry.get("CENTRE_ALTRES", "")).strip(),
                )
                if value
            ) or None
            deadline_text = str(entry.get("INFO_TERMINI", "")).strip() or None
            try:
                digest = hashlib.sha256(http_get(url)).hexdigest()
                warning = ""
            except Exception as exc:
                digest = hashlib.sha256(
                    json.dumps(entry, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest()
                warning = f"No s’ha pogut descarregar el PDF: {exc}"

            result.documents.append(
                DocumentResult(
                    title=f"{identifier} — {profile}",
                    url=url,
                    status=document_status(url, digest, old_state),
                    sha256=digest,
                    offers=[
                        Offer(
                            identifier=identifier,
                            specialty=clean_specialty(profile),
                            institution=institution,
                            municipality="Barcelona",
                            vacancies=edubcn_vacancies(profile),
                            deadline=deadline_text,
                            detail=" · ".join(
                                value
                                for value in (profile, institution, deadline_text)
                                if value
                            ),
                        )
                    ],
                    warning=warning,
                )
            )
        if not result.documents:
            result.error = "No hi ha cap convocatòria oberta a la pàgina."
    except Exception as exc:
        result.error = str(exc)
    return result


def analyze_region(name: str, page_url: str, old_state: dict) -> RegionResult:
    if urllib.parse.urlparse(page_url).netloc.lower().endswith("edubcn.cat"):
        return analyze_edubcn_region(
            name, page_url, old_state, datetime.now().astimezone().date()
        )
    result = RegionResult(name=name, page_url=page_url, documents=[])
    try:
        links = find_offer_pdfs(page_url)
        if not links:
            result.error = "No s’ha detectat cap PDF d’ofertes a la pàgina."
            return result
        with tempfile.TemporaryDirectory(prefix="escola-karen-") as temp:
            temp_path = Path(temp)
            for index, (url, title) in enumerate(links):
                try:
                    content = http_get(url)
                    digest = hashlib.sha256(content).hexdigest()
                    pdf_path = temp_path / f"{index}.pdf"
                    pdf_path.write_bytes(content)
                    text = pdf_to_text(pdf_path)
                    offers = parse_offers(text)
                    note = ""
                    warning = ""
                    if not offers:
                        if is_blank_offer_template(text):
                            note = (
                                "El PDF publicat és un formulari buit: "
                                "actualment no hi consta cap oferta."
                            )
                        else:
                            warning = "No s’ha pogut analitzar el format del PDF."
                    result.documents.append(
                        DocumentResult(
                            title=title,
                            url=url,
                            status=document_status(url, digest, old_state),
                            sha256=digest,
                            offers=offers,
                            note=note,
                            warning=warning,
                        )
                    )
                except Exception as exc:
                    result.documents.append(
                        DocumentResult(
                            title=title,
                            url=url,
                            status="error",
                            sha256="",
                            offers=[],
                            warning=str(exc),
                        )
                    )
    except Exception as exc:
        result.error = str(exc)
    return result


def specialty_counts(offers: Iterable[Offer]) -> Counter:
    return Counter(offer.specialty for offer in offers)


def build_document_state(results: Iterable[RegionResult], now: datetime) -> dict:
    documents = {}
    for region in results:
        for document in region.documents:
            if document.sha256:
                documents[document.url] = {
                    "sha256": document.sha256,
                    "last_seen": now.isoformat(),
                    "region": region.name,
                }
    return {"last_run": now.isoformat(), "documents": documents}
