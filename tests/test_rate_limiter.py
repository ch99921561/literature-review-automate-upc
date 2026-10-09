"""Pruebas del límite local de solicitudes."""

import unittest

from src.search_engine import RequestLimiter


class RequestLimiterTests(unittest.TestCase):
    def test_stops_after_daily_limit(self) -> None:
        limiter = RequestLimiter(calls_per_second=None, calls_per_day=2)

        self.assertTrue(limiter.acquire())
        self.assertTrue(limiter.acquire())
        self.assertFalse(limiter.acquire())
        self.assertEqual(2, limiter.calls_made)

    def test_allows_unlimited_requests_when_limits_are_null(self) -> None:
        limiter = RequestLimiter(calls_per_second=None, calls_per_day=None)

        self.assertTrue(limiter.acquire())
        self.assertTrue(limiter.acquire())
        self.assertEqual(2, limiter.calls_made)


if __name__ == "__main__":
    unittest.main()
