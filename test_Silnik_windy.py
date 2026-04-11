import unittest

from Silnik_windy import (
    Direction,
    Elevator,
    ElevatorConfig,
    ElevatorRequest,
    RequestSource,
    RequestType,
)


class ElevatorCoreTests(unittest.TestCase):
    def setUp(self):
        self.config = ElevatorConfig(
            num_floors=10,
            floor_travel_time=1.0,
            door_opening_time=0.5,
            door_open_time=0.5,
            door_closing_time=0.5,
            start_floor=0,
        )
        self.elevator = Elevator("E1", self.config)

    def run_for(self, seconds: float, dt: float = 0.1):
        steps = int(seconds / dt)
        for _ in range(steps):
            self.elevator.step(dt)

    def test_single_hall_call(self):
        self.elevator.submit_request(ElevatorRequest(
            request_type=RequestType.HALL_CALL,
            source=RequestSource.BUTTON,
            created_at=0.0,
            floor=3,
            direction=Direction.UP,
        ))

        self.run_for(6.0)
        snap = self.elevator.snapshot()

        self.assertEqual(round(snap["position"]), 3)
        self.assertEqual(snap["pending_total"], 0)

    def test_car_call(self):
        self.elevator.submit_request(ElevatorRequest(
            request_type=RequestType.CAR_CALL,
            source=RequestSource.BUTTON,
            created_at=0.0,
            floor=0,
            target_floor=5,
        ))

        self.run_for(8.0)
        snap = self.elevator.snapshot()

        self.assertEqual(round(snap["position"]), 5)
        self.assertEqual(snap["pending_total"], 0)

    def test_stop_on_the_way(self):
        self.elevator.submit_request(ElevatorRequest(
            request_type=RequestType.CAR_CALL,
            source=RequestSource.BUTTON,
            created_at=0.0,
            floor=0,
            target_floor=7,
        ))

        self.run_for(2.2)

        self.elevator.submit_request(ElevatorRequest(
            request_type=RequestType.HALL_CALL,
            source=RequestSource.BUTTON,
            created_at=2.2,
            floor=3,
            direction=Direction.UP,
        ))

        self.run_for(10.0)

        event_types = [e.event_type for e in self.elevator.event_log]
        self.assertIn("doors_opening", event_types)

        served_floors = [
            e.payload["floor"] for e in self.elevator.event_log
            if e.event_type == "doors_opening"
        ]
        self.assertIn(3, served_floors)
        self.assertIn(7, served_floors)

    def test_duplicate_request_not_added_as_new_active_stop(self):
        added_1 = self.elevator.submit_request(ElevatorRequest(
            request_type=RequestType.HALL_CALL,
            source=RequestSource.BUTTON,
            created_at=0.0,
            floor=4,
            direction=Direction.UP,
        ))
        added_2 = self.elevator.submit_request(ElevatorRequest(
            request_type=RequestType.HALL_CALL,
            source=RequestSource.SYSTEM,
            created_at=0.1,
            floor=4,
            direction=Direction.UP,
        ))

        self.assertTrue(added_1)
        self.assertFalse(added_2)
        self.assertEqual(self.elevator.pending_count(), 1)

    def test_manual_target(self):
        self.elevator.set_manual_target(6)
        self.run_for(10.0)
        snap = self.elevator.snapshot()

        self.assertEqual(round(snap["position"]), 6)
        self.assertEqual(snap["control_mode"], "AUTO")

    def test_invalid_floor_raises(self):
        with self.assertRaises(ValueError):
            self.elevator.submit_request(ElevatorRequest(
                request_type=RequestType.HALL_CALL,
                source=RequestSource.BUTTON,
                created_at=0.0,
                floor=99,
                direction=Direction.UP,
            ))


if __name__ == "__main__":
    unittest.main()