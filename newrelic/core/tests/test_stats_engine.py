import unittest


from newrelic.core.config import (global_settings, SPAN_EVENT_RESERVOIR_SIZE,
                                  DEFAULT_RESERVOIR_SIZE)
from newrelic.core.stats_engine import StatsEngine


class TestStatsEngineCustomEvents(unittest.TestCase):

    def setUp(self):
        self.settings = global_settings()

    def test_custom_events_initial_values(self):
        stats = StatsEngine()
        self.assertEqual(stats.custom_events.capacity, 100)
        self.assertEqual(stats.custom_events.num_samples, 0)
        self.assertEqual(stats.custom_events.num_seen, 0)

    def test_custom_events_reset_stats_set_capacity(self):
        stats = StatsEngine()
        self.assertEqual(stats.custom_events.capacity, 100)

        self.settings.custom_insights_events.max_samples_stored = 500
        stats.reset_stats(self.settings)

        self.assertEqual(stats.custom_events.capacity, 500)

    def test_custom_events_capacity_same_as_transaction_events(self):
        stats = StatsEngine()

        ce_settings = self.settings.custom_insights_events
        ce_settings.max_samples_stored = DEFAULT_RESERVOIR_SIZE
        stats.reset_stats(self.settings)

        self.assertEqual(stats.custom_events.capacity,
                stats.transaction_events.capacity)

    def test_custom_events_reset_stats_after_adding_samples(self):
        stats = StatsEngine()

        stats.custom_events.add('event')
        self.assertEqual(stats.custom_events.num_samples, 1)
        self.assertEqual(stats.custom_events.num_seen, 1)

        stats.reset_stats(self.settings)
        self.assertEqual(stats.custom_events.num_samples, 0)
        self.assertEqual(stats.custom_events.num_seen, 0)


class TestStatsEngineSpanEvents(unittest.TestCase):

    def setUp(self):
        self.settings = global_settings()

    def test_span_events_initial_values(self):
        stats = StatsEngine()
        self.assertEqual(stats.span_events.capacity, SPAN_EVENT_RESERVOIR_SIZE)
        self.assertEqual(stats.span_events.num_samples, 0)
        self.assertEqual(stats.span_events.num_seen, 0)

    def test_span_events_reset_stats_set_capacity_enabled(self):
        stats = StatsEngine()
        self.assertEqual(stats.span_events.capacity, SPAN_EVENT_RESERVOIR_SIZE)

        self.settings.span_events.max_samples_stored = 321
        stats.reset_stats(self.settings)

        self.assertEqual(stats.span_events.capacity, 321)

    def test_span_events_reset_stats_set_capacity_disabled(self):
        stats = StatsEngine()
        self.assertEqual(stats.span_events.capacity, SPAN_EVENT_RESERVOIR_SIZE)

        self.settings.span_events.max_samples_stored = 321
        stats.reset_stats(None)

        self.assertEqual(stats.span_events.capacity, SPAN_EVENT_RESERVOIR_SIZE)

    def test_span_events_reset_stats_after_adding_samples(self):
        stats = StatsEngine()

        stats.span_events.add('event')
        self.assertEqual(stats.span_events.num_samples, 1)
        self.assertEqual(stats.span_events.num_seen, 1)

        stats.reset_stats(self.settings)
        self.assertEqual(stats.span_events.num_samples, 0)
        self.assertEqual(stats.span_events.num_seen, 0)

    def test_span_events_harvest_snapshot(self):
        stats = StatsEngine()

        stats.span_events.add('event')
        self.assertEqual(stats.span_events.num_samples, 1)
        self.assertEqual(stats.span_events.num_seen, 1)

        snapshot = stats.harvest_snapshot()
        self.assertEqual(snapshot.span_events.num_samples, 1)
        self.assertEqual(snapshot.span_events.num_seen, 1)

        self.assertEqual(stats.span_events.num_samples, 0)
        self.assertEqual(stats.span_events.num_seen, 0)
        self.assertEqual(stats.span_events.capacity, SPAN_EVENT_RESERVOIR_SIZE)

    def test_span_events_merge(self):
        stats = StatsEngine()
        stats.reset_stats(self.settings)

        stats.span_events.add('event')
        self.assertEqual(stats.span_events.num_samples, 1)
        self.assertEqual(stats.span_events.num_seen, 1)

        snapshot = StatsEngine()
        snapshot.span_events.add('event')
        self.assertEqual(snapshot.span_events.num_samples, 1)
        self.assertEqual(snapshot.span_events.num_seen, 1)

        stats.merge(snapshot)
        self.assertEqual(stats.span_events.num_samples, 2)
        self.assertEqual(stats.span_events.num_seen, 2)

    def test_span_events_rollback(self):
        stats = StatsEngine()
        stats.reset_stats(self.settings)

        stats.span_events.add('event')
        self.assertEqual(stats.span_events.num_samples, 1)
        self.assertEqual(stats.span_events.num_seen, 1)

        snapshot = StatsEngine()
        snapshot.span_events.add('event')
        self.assertEqual(snapshot.span_events.num_samples, 1)
        self.assertEqual(snapshot.span_events.num_seen, 1)

        stats.rollback(snapshot)
        self.assertEqual(stats.span_events.num_samples, 2)
        self.assertEqual(stats.span_events.num_seen, 2)


if __name__ == '__main__':
    unittest.main()
