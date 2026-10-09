"""Pruebas de selección de keywords por tesis."""

import json
import tempfile
import unittest
from pathlib import Path

from src.input_config import InputConfig


class ThesisSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config_data = {
            "titulo_tesis": "1",
            "tesis": {
                "1": {
                    "descripcion": "Tesis principal",
                    "keywords": ["keyword one", "keyword two", "keyword three"],
                },
                "2": {
                    "descripcion": "Tesis alternativa",
                    "keywords": ["alternative one", "alternative two", "alternative three"],
                },
            },
            "year_from": 2020,
            "year_to": 2026,
            "scopus": {"doc_types": ["ar"], "subject_areas": []},
            "ieee": {"content_types": []},
            "wos": {"database": "WOS", "document_types": []},
            "rate_limits": {"ieee": {"calls_per_second": 10, "calls_per_day": 200}},
        }

    def _load_config(self, thesis_id=None) -> InputConfig:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "input.json"
            path.write_text(json.dumps(self.config_data), encoding="utf-8")
            return InputConfig.load(str(path), thesis_id=thesis_id)

    def test_uses_default_thesis_and_preserves_transversal_configuration(self) -> None:
        config = self._load_config()

        self.assertEqual("1", config.thesis_id)
        self.assertEqual("Tesis principal", config.thesis_description)
        self.assertEqual(2020, config.year_from)
        self.assertEqual(2026, config.year_to)
        self.assertEqual(["ar"], config.scopus.doc_types)
        self.assertEqual(200, config.rate_limits["ieee"]["calls_per_day"])

    def test_command_line_selection_overrides_default_thesis(self) -> None:
        config = self._load_config(thesis_id="2")

        self.assertEqual("2", config.thesis_id)
        self.assertEqual(["alternative one", "alternative two", "alternative three"], config.keywords)

    def test_unknown_thesis_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "no existe"):
            self._load_config(thesis_id="3")


if __name__ == "__main__":
    unittest.main()
