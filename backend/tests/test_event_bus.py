import unittest
from app.core.event_bus import EventBus


class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()

    def test_subscribe_and_publish(self):
        results = []

        def callback(data):
            results.append(data)

        self.bus.subscribe("test_event", callback)
        self.bus.publish("test_event", "test_data")

        self.assertEqual(results, ["test_data"])

    def test_multiple_subscribers(self):
        results1 = []
        results2 = []

        def callback1(data):
            results1.append(data)

        def callback2(data):
            results2.append(data)

        self.bus.subscribe("test_event", callback1)
        self.bus.subscribe("test_event", callback2)
        self.bus.publish("test_event", "test_data")

        self.assertEqual(results1, ["test_data"])
        self.assertEqual(results2, ["test_data"])

    def test_unsubscribe(self):
        results = []

        def callback(data):
            results.append(data)

        self.bus.subscribe("test_event", callback)
        self.bus.unsubscribe("test_event", callback)
        self.bus.publish("test_event", "test_data")

        self.assertEqual(results, [])


if __name__ == '__main__':
    unittest.main()