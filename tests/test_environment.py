"""Pruebas de carga y validación de la configuración de entorno."""

import tempfile
import unittest
from pathlib import Path

from src.config import load_dotenv, validate_environment


class EnvironmentConfigurationTests(unittest.TestCase):
    def test_load_dotenv_preserves_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            dotenv_path = Path(temporary_directory) / ".env"
            dotenv_path.write_text(
                "APP_ENV=production\nSCOPUS_API_KEY=from-file\n",
                encoding="utf-8",
            )
            environment = {"SCOPUS_API_KEY": "from-system"}

            loaded = load_dotenv(dotenv_path, environment)

        self.assertTrue(loaded)
        self.assertEqual("production", environment["APP_ENV"])
        self.assertEqual("from-system", environment["SCOPUS_API_KEY"])

    def test_validate_environment_accepts_allowed_value(self) -> None:
        self.assertEqual("test", validate_environment({"APP_ENV": "TEST"}))

    def test_validate_environment_rejects_missing_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "Falta APP_ENV"):
            validate_environment({})

    def test_validate_environment_rejects_unknown_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "no es válido"):
            validate_environment({"APP_ENV": "staging"})


if __name__ == "__main__":
    unittest.main()
