import unittest
from datetime import date

from escola_karen.core import (
    document_status,
    edubcn_deadline,
    edubcn_vacancies,
    is_blank_offer_template,
    is_target_specialty,
    parse_offers,
)


class ParserTests(unittest.TestCase):
    def test_form_pdf_extracts_targets_and_plural_vacancies(self):
        text = """
Identificador de la plaça: DC-20 Vacant
Especialitat:                                      Presentació de sol·licituds
GE - Geografia                                     Fins demà

Identificador de la plaça: DC-21 2 Vacants
Especialitat: CLA - Cultura clàssica               Presentació de sol·licituds
"""
        offers = parse_offers(text)
        self.assertEqual([offer.specialty for offer in offers], ["GE", "CLA"])
        self.assertEqual([offer.vacancies for offer in offers], [1.0, 2.0])

    def test_table_pdf_handles_wrapped_rows(self):
        text = (
            "Identificador Codi centre Nom centre             Municipi"
            "                   Especialitat Qualificador\n"
            "                                                        "
            "                              COS    Vacants\n"
            "1260001 43000000 Institut Nom molt llarg\n"
            "                                                        "
            "Municipi llarg             GE         GEO     590EC        1\n"
            "1260002 43000001 Institut Dos              Municipi"
            "                   CLA        CLA     590EC        0,5\n"
        )
        offers = parse_offers(text)
        self.assertEqual([offer.specialty for offer in offers], ["GE", "CLA"])

    def test_blank_offer_template_is_not_an_extraction_error(self):
        text = """
Oferta de vacants o substitucions de difícil cobertura
Identificador de la plaça    Especialitat
Nom del centre
Municipi
Jornada
"""
        self.assertTrue(is_blank_offer_template(text))
        self.assertEqual(parse_offers(text), [])

    def test_form_extracts_institution_municipality_and_deadline(self):
        text = """
Identificador de la plaça: DC-22 Vacant
Especialitat: GE
Nom del centre: Institut Mediterrània
Municipi: Tarragona
Presentació de sol·licituds fins al 18/07/2026
"""
        offer = parse_offers(text)[0]
        self.assertEqual(offer.institution, "Institut Mediterrània")
        self.assertEqual(offer.municipality, "Tarragona")
        self.assertEqual(offer.deadline, "18/07/2026")

    def test_target_matching_is_exact_and_ignores_case_and_spaces(self):
        targets = {"GE", "CLA"}
        self.assertTrue(is_target_specialty(" ge ", targets))
        self.assertTrue(is_target_specialty("C L A", targets))
        self.assertFalse(is_target_specialty("GEO", targets))
        self.assertFalse(is_target_specialty("CLA1", targets))
        self.assertFalse(is_target_specialty("Oferta CLA", targets))

    def test_document_states(self):
        state = {"documents": {"https://example.test/a.pdf": {"sha256": "old"}}}
        self.assertEqual(document_status("https://example.test/new.pdf", "x", state), "nou")
        self.assertEqual(document_status("https://example.test/a.pdf", "new", state), "actualitzat")
        self.assertEqual(document_status("https://example.test/a.pdf", "old", state), "sense canvis")

    def test_edubcn_deadline_uses_publication_year(self):
        entry = {"DATA": "2026-07-14", "INFO_TERMINI": "fins al 17/07/2026 a les 8 h"}
        self.assertEqual(edubcn_deadline(entry, date(2026, 7, 16)), date(2026, 7, 17))

    def test_edubcn_deadline_supports_missing_year(self):
        entry = {"DATA": "2026-07-14", "INFO_TERMINI": "fins divendres 17/07 a les 8 h"}
        self.assertEqual(edubcn_deadline(entry, date(2026, 7, 16)), date(2026, 7, 17))

    def test_edubcn_plural_vacancies(self):
        self.assertEqual(edubcn_vacancies("REINICIA’t (4 vacants)"), 4.0)
        self.assertEqual(edubcn_vacancies("GE – Geografia"), 1.0)


if __name__ == "__main__":
    unittest.main()
