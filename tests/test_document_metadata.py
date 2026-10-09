"""Pruebas de extracción de metadatos de documentos."""

import unittest
from urllib.parse import parse_qs, urlparse

from src.ieee_client import IEEEAPIClient
from src.models import ScopusFilters
from src.scopus_client import ScopusAPIClient
from src.wos_client import WOSAPIClient


class DocumentMetadataTests(unittest.TestCase):
    def test_scopus_extracts_title_and_publication_year(self) -> None:
        documents = ScopusAPIClient().extract_documents([
            {"dc:title": "Scopus document", "prism:coverDate": "2024-06-01"}
        ])

        self.assertEqual(
            [{"titulo": "Scopus document", "año_publicacion": "2024"}],
            documents,
        )

    def test_ieee_extracts_title_and_publication_year(self) -> None:
        documents = IEEEAPIClient().extract_documents([
            {"title": "IEEE document", "publication_year": "2023"}
        ])

        self.assertEqual(
            [{"titulo": "IEEE document", "año_publicacion": "2023"}],
            documents,
        )

    def test_wos_extracts_title_and_publication_year(self) -> None:
        documents = WOSAPIClient().extract_documents([{
            "static_data": {
                "summary": {
                    "titles": {
                        "title": [{"type": "item", "content": "WOS document"}]
                    },
                    "pub_info": {"pubyear": "2022"},
                }
            }
        }])

        self.assertEqual(
            [{"titulo": "WOS document", "año_publicacion": "2022"}],
            documents,
        )

    def test_scopus_document_pagination_starts_at_zero(self) -> None:
        client = ScopusAPIClient()
        requested_starts = []

        def get(url, **_kwargs):
            start = int(parse_qs(urlparse(url).query)["start"][0])
            requested_starts.append(start)
            return {
                "search-results": {
                    "opensearch:totalResults": "2",
                    "entry": [
                        {
                            "dc:title": f"Document {start}",
                            "prism:coverDate": "2026-01-01",
                        },
                        {
                            "dc:title": "Document 1",
                            "prism:coverDate": "2026-01-01",
                        },
                    ],
                }
            }

        client.http.get = get

        documents = client.get_documents(
            '"keyword"', ScopusFilters(year_from=2020, year_to=2026)
        )

        self.assertEqual([0], requested_starts)
        self.assertEqual(
            [
                {"titulo": "Document 0", "año_publicacion": "2026"},
                {"titulo": "Document 1", "año_publicacion": "2026"},
            ],
            documents,
        )


if __name__ == "__main__":
    unittest.main()
