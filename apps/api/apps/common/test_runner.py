from __future__ import annotations

from unittest import TestSuite

from django.conf import settings
from django.test.runner import DiscoverRunner


class SelectiveDiscoverRunner(DiscoverRunner):
    def build_suite(self, *args, **kwargs):
        suite = super().build_suite(*args, **kwargs)
        excluded_prefixes = tuple(getattr(settings, "TEST_EXCLUDED_LABEL_PREFIXES", ()))
        if not excluded_prefixes:
            return suite
        return self._filter_suite(suite, excluded_prefixes)

    def _filter_suite(self, suite, excluded_prefixes: tuple[str, ...]):
        filtered_suite = TestSuite()
        for test in suite:
            if isinstance(test, TestSuite):
                nested_suite = self._filter_suite(test, excluded_prefixes)
                if nested_suite.countTestCases():
                    filtered_suite.addTest(nested_suite)
                continue

            test_id = test.id()
            if any(test_id.startswith(prefix) for prefix in excluded_prefixes):
                continue
            filtered_suite.addTest(test)
        return filtered_suite
