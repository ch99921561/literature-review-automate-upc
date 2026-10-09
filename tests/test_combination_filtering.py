"""Pruebas del filtrado de ternas sin resultados individuales."""

import unittest

from src.models import CombinationResult, SearchResult
from src.search_engine import SearchEngine


class CombinationFilteringTests(unittest.TestCase):
    def test_omits_combinations_with_any_zero_keyword(self) -> None:
        keywords = ["A", "B", "C", "D"]
        individual_results = [
            SearchResult(keyword="A", query='"A"', count=9),
            SearchResult(keyword="B", query='"B"', count=7),
            SearchResult(keyword="C", query='"C"', count=0),
            SearchResult(keyword="D", query='"D"', count=0),
        ]

        combinations = SearchEngine._eligible_combinations(keywords, individual_results)

        self.assertEqual([], combinations)

    def test_keeps_combination_when_all_keywords_have_results(self) -> None:
        keywords = ["A", "B", "C", "D"]
        individual_results = [
            SearchResult(keyword="A", query='"A"', count=3),
            SearchResult(keyword="B", query='"B"', count=2),
            SearchResult(keyword="C", query='"C"', count=1),
            SearchResult(keyword="D", query='"D"', count=0),
        ]

        self.assertEqual(
            [("A", "B", "C")],
            SearchEngine._eligible_combinations(keywords, individual_results),
        )

    def test_generates_one_combination_regardless_of_keyword_order(self) -> None:
        keywords = ["A", "B", "C"]
        individual_results = [
            SearchResult(keyword="A", query='"A"', count=3),
            SearchResult(keyword="B", query='"B"', count=4),
            SearchResult(keyword="C", query='"C"', count=14),
        ]

        self.assertEqual(
            [("A", "B", "C")],
            SearchEngine._eligible_combinations(keywords, individual_results),
        )

    def test_deduplicates_repeated_keywords_before_generating_combinations(self) -> None:
        keywords = ["A", "B", "C", "a"]
        individual_results = [
            SearchResult(keyword="A", query='"A"', count=3),
            SearchResult(keyword="B", query='"B"', count=4),
            SearchResult(keyword="C", query='"C"', count=14),
            SearchResult(keyword="a", query='"a"', count=3),
        ]

        self.assertEqual(
            [("A", "B", "C")],
            SearchEngine._eligible_combinations(keywords, individual_results),
        )

    def test_reports_keywords_not_used_in_combinations(self) -> None:
        individual_results = [
            SearchResult(keyword="A", query='"A"', count=3),
            SearchResult(keyword="B", query='"B"', count=2),
            SearchResult(keyword="C", query='"C"', count=0),
            SearchResult(keyword="D", query='"D"', count=None, error=True),
        ]
        combinations = [
            CombinationResult(
                keywords=["A", "B", "C"],
                query='"A" AND "B" AND "C"',
                count=0,
            )
        ]

        unused = SearchEngine._unused_keywords(
            ["A", "B", "C", "D"], individual_results, combinations
        )

        self.assertEqual(
            [{
                "keyword": "D",
                "individual_count": None,
                "reason": "No se obtuvo el conteo individual",
            }],
            unused,
        )

    def test_identifies_remaining_eligible_combinations_after_a_quota_stop(self) -> None:
        keywords = ["A", "B", "C", "D"]
        individual_results = [
            SearchResult(keyword="A", query='"A"', count=3),
            SearchResult(keyword="B", query='"B"', count=2),
            SearchResult(keyword="C", query='"C"', count=1),
            SearchResult(keyword="D", query='"D"', count=4),
        ]
        combinations = SearchEngine._eligible_combinations(keywords, individual_results)

        self.assertEqual(
            [("A", "B", "D"), ("A", "C", "D"), ("B", "C", "D")],
            combinations[1:],
        )

    def test_identifies_executed_combinations_with_zero_results(self) -> None:
        combinations = [
            CombinationResult(keywords=["A", "B", "C"], query="query 1", count=0),
            CombinationResult(keywords=["A", "B", "D"], query="query 2", count=2),
            CombinationResult(keywords=["A", "C", "D"], query="query 3", count=None, error=True),
        ]

        self.assertEqual(
            [combinations[0]],
            SearchEngine._zero_result_combinations(combinations),
        )


if __name__ == "__main__":
    unittest.main()
