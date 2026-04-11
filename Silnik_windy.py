from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Protocol, Set, Tuple
import heapq
import itertools
import math


class Direction(Enum):
    DOWN = -1
    IDLE = 0
    UP = 1


class DoorState(Enum):
    OPEN = auto()
    CLOSED = auto()
    OPENING = auto()
    CLOSING = auto()


class MotionState(Enum):
    IDLE = auto()
    MOVING = auto()


class RequestSource(Enum):
    BUTTON = auto()
    SYSTEM = auto()
    MANUAL = auto()
    ML = auto()


class RequestType(Enum):
    HALL_CALL = auto()
    CAR_CALL = auto()


class ControlMode(Enum):
    AUTO = auto()
    MANUAL = auto()


class StopReason(Enum):
    HALL_UP = auto()
    HALL_DOWN = auto()
    CAR = auto()
    MANUAL_TARGET = auto()


_event_id_counter = itertools.count(1)
_request_id_counter = itertools.count(1)


@dataclass(slots=True)
class ElevatorEvent:
    time: float
    event_type: str
    payload: dict
    event_id: int = field(default_factory=lambda: next(_event_id_counter))


@dataclass(slots=True)
class ElevatorRequest:
    request_type: RequestType
    source: RequestSource
    created_at: float
    floor: int
    direction: Optional[Direction] = None
    target_floor: Optional[int] = None
    priority: int = 0
    request_id: int = field(default_factory=lambda: next(_request_id_counter))

    def __post_init__(self) -> None:
        if self.request_type == RequestType.HALL_CALL:
            if self.direction not in (Direction.UP, Direction.DOWN):
                raise ValueError("HALL_CALL wymaga direction = UP albo DOWN")
            if self.target_floor is not None:
                raise ValueError("HALL_CALL nie może mieć target_floor")
        elif self.request_type == RequestType.CAR_CALL:
            if self.target_floor is None:
                raise ValueError("CAR_CALL wymaga target_floor")
            if self.direction is not None:
                raise ValueError("CAR_CALL nie może mieć direction")
        else:
            raise ValueError("Nieznany typ zgłoszenia")

    @property
    def key(self) -> Tuple:
        if self.request_type == RequestType.HALL_CALL:
            return ("HALL", self.floor, self.direction)
        return ("CAR", self.target_floor)


class DispatchStrategy(Protocol):
    def choose_direction(self, elevator: "Elevator") -> Direction:
        ...

    def choose_manual_fallback_target(self, elevator: "Elevator") -> Optional[int]:
        ...


class ScanDispatchStrategy:
    def choose_direction(self, elevator: "Elevator") -> Direction:
        current = elevator.current_floor_rounded()

        above_exists = elevator.has_any_pending_above(current)
        below_exists = elevator.has_any_pending_below(current)

        if elevator.direction == Direction.UP:
            if above_exists:
                return Direction.UP
            if below_exists:
                return Direction.DOWN
            return Direction.IDLE

        if elevator.direction == Direction.DOWN:
            if below_exists:
                return Direction.DOWN
            if above_exists:
                return Direction.UP
            return Direction.IDLE

        nearest = elevator.nearest_pending_floor()
        if nearest is None:
            return Direction.IDLE
        if nearest > current:
            return Direction.UP
        if nearest < current:
            return Direction.DOWN
        return Direction.IDLE

    def choose_manual_fallback_target(self, elevator: "Elevator") -> Optional[int]:
        return elevator.nearest_pending_floor()


@dataclass(slots=True)
class ElevatorConfig:
    num_floors: int
    floor_travel_time: float = 2.0
    door_opening_time: float = 1.0
    door_open_time: float = 2.0
    door_closing_time: float = 1.0
    start_floor: int = 0

    def __post_init__(self) -> None:
        if self.num_floors < 2:
            raise ValueError("num_floors musi być >= 2")
        if not (0 <= self.start_floor < self.num_floors):
            raise ValueError("start_floor poza zakresem")
        if self.floor_travel_time <= 0:
            raise ValueError("floor_travel_time musi być > 0")
        if self.door_opening_time < 0 or self.door_open_time < 0 or self.door_closing_time < 0:
            raise ValueError("Czasy drzwi nie mogą być ujemne")


class Elevator:
    def __init__(
        self,
        elevator_id: str,
        config: ElevatorConfig,
        strategy: Optional[DispatchStrategy] = None,
    ) -> None:
        self.elevator_id = elevator_id
        self.config = config
        self.strategy = strategy or ScanDispatchStrategy()

        self.position: float = float(config.start_floor)
        self.direction: Direction = Direction.IDLE
        self.motion_state: MotionState = MotionState.IDLE
        self.door_state: DoorState = DoorState.CLOSED
        self.control_mode: ControlMode = ControlMode.AUTO

        self.sim_time: float = 0.0
        self.phase_remaining: float = 0.0

        self.manual_target: Optional[int] = None

        self.hall_up_floors: Set[int] = set()
        self.hall_down_floors: Set[int] = set()
        self.car_floors: Set[int] = set()

        self.active_request_keys: Set[Tuple] = set()
        self.requests_by_key: Dict[Tuple, List[ElevatorRequest]] = {}

        self.event_log: List[ElevatorEvent] = []
        self.listeners: List[Callable[[ElevatorEvent], None]] = []

        self._last_reported_floor: int = config.start_floor

    def add_listener(self, listener: Callable[[ElevatorEvent], None]) -> None:
        self.listeners.append(listener)

    def submit_request(self, request: ElevatorRequest) -> bool:
        self._validate_request(request)

        if request.key in self.active_request_keys:
            self._store_request_instance(request)
            self._emit("request_duplicated", {
                "request_id": request.request_id,
                "key": request.key,
                "source": request.source.name,
            })
            return False

        self.active_request_keys.add(request.key)
        self._store_request_instance(request)

        if request.request_type == RequestType.HALL_CALL:
            if request.direction == Direction.UP:
                self.hall_up_floors.add(request.floor)
            else:
                self.hall_down_floors.add(request.floor)
        else:
            self.car_floors.add(request.target_floor)

        self._emit("request_submitted", {
            "request_id": request.request_id,
            "request_type": request.request_type.name,
            "source": request.source.name,
            "floor": request.floor,
            "direction": request.direction.name if request.direction else None,
            "target_floor": request.target_floor,
            "priority": request.priority,
        })

        self._try_start_if_idle()
        return True

    def set_manual_target(self, floor: Optional[int]) -> None:
        if floor is not None and not (0 <= floor < self.config.num_floors):
            raise ValueError("manual_target poza zakresem")
        self.manual_target = floor
        self.control_mode = ControlMode.MANUAL if floor is not None else ControlMode.AUTO
        self._emit("control_mode_changed", {
            "control_mode": self.control_mode.name,
            "manual_target": self.manual_target,
        })
        self._try_start_if_idle()

    def clear_manual_target(self) -> None:
        self.manual_target = None
        self.control_mode = ControlMode.AUTO
        self._emit("control_mode_changed", {
            "control_mode": self.control_mode.name,
            "manual_target": None,
        })
        self._try_start_if_idle()

    def step(self, dt: float) -> None:
        if dt <= 0:
            raise ValueError("dt musi być dodatnie")

        remaining = dt
        while remaining > 1e-9:
            self.sim_time += 0.0

            if self.motion_state == MotionState.IDLE and self.door_state == DoorState.CLOSED:
                self._try_start_if_idle()
                if self.motion_state == MotionState.IDLE:
                    self.sim_time += remaining
                    break

            if self.motion_state == MotionState.MOVING:
                consumed = self._step_moving(remaining)
                self.sim_time += consumed
                remaining -= consumed
                continue

            consumed = self._step_doors(remaining)
            self.sim_time += consumed
            remaining -= consumed

    def snapshot(self) -> dict:
        return {
            "elevator_id": self.elevator_id,
            "sim_time": round(self.sim_time, 4),
            "position": round(self.position, 4),
            "current_floor_if_aligned": self.current_floor_if_aligned(),
            "direction": self.direction.name,
            "motion_state": self.motion_state.name,
            "door_state": self.door_state.name,
            "control_mode": self.control_mode.name,
            "manual_target": self.manual_target,
            "pending": {
                "hall_up": sorted(self.hall_up_floors),
                "hall_down": sorted(self.hall_down_floors),
                "car": sorted(self.car_floors),
            },
            "pending_total": self.pending_count(),
        }

    def current_floor_if_aligned(self) -> Optional[int]:
        nearest = round(self.position)
        if abs(self.position - nearest) < 1e-9:
            return nearest
        return None

    def current_floor_rounded(self) -> int:
        return int(round(self.position))

    def pending_count(self) -> int:
        return len(self.active_request_keys)

    def has_pending(self) -> bool:
        return bool(self.hall_up_floors or self.hall_down_floors or self.car_floors or self.manual_target is not None)

    def has_any_pending_above(self, floor: int) -> bool:
        return any(f > floor for f in self._all_pending_floors())

    def has_any_pending_below(self, floor: int) -> bool:
        return any(f < floor for f in self._all_pending_floors())

    def nearest_pending_floor(self) -> Optional[int]:
        pending = self._all_pending_floors()
        if not pending:
            return None
        current = self.current_floor_rounded()
        return min(pending, key=lambda f: (abs(f - current), f))

    def _all_pending_floors(self) -> Set[int]:
        result = set(self.hall_up_floors) | set(self.hall_down_floors) | set(self.car_floors)
        if self.manual_target is not None:
            result.add(self.manual_target)
        return result

    def _store_request_instance(self, request: ElevatorRequest) -> None:
        self.requests_by_key.setdefault(request.key, []).append(request)

    def _validate_request(self, request: ElevatorRequest) -> None:
        floors = [request.floor]
        if request.target_floor is not None:
            floors.append(request.target_floor)
        for floor in floors:
            if not (0 <= floor < self.config.num_floors):
                raise ValueError(f"Piętro {floor} poza zakresem 0..{self.config.num_floors - 1}")

    def _try_start_if_idle(self) -> None:
        if self.motion_state != MotionState.IDLE:
            return
        if self.door_state != DoorState.CLOSED:
            return
        if not self.has_pending():
            self.direction = Direction.IDLE
            return

        aligned_floor = self.current_floor_if_aligned()
        if aligned_floor is not None and self._should_stop_at_floor(aligned_floor):
            self._start_door_opening(aligned_floor)
            return

        chosen_direction = self._choose_direction()
        if chosen_direction == Direction.IDLE:
            return

        self.direction = chosen_direction
        self.motion_state = MotionState.MOVING
        self._emit("moving_started", {
            "direction": self.direction.name,
            "position": self.position,
        })

    def _choose_direction(self) -> Direction:
        if self.control_mode == ControlMode.MANUAL and self.manual_target is not None:
            current = self.current_floor_rounded()
            if self.manual_target > current:
                return Direction.UP
            if self.manual_target < current:
                return Direction.DOWN
            return Direction.IDLE

        return self.strategy.choose_direction(self)

    def _step_moving(self, dt: float) -> float:
        speed = 1.0 / self.config.floor_travel_time
        if self.direction == Direction.IDLE:
            self.motion_state = MotionState.IDLE
            return 0.0

        next_floor_boundary = self._next_floor_boundary_in_direction()
        if next_floor_boundary is None:
            self.motion_state = MotionState.IDLE
            self.direction = Direction.IDLE
            return 0.0

        distance_to_boundary = abs(next_floor_boundary - self.position)
        time_to_boundary = distance_to_boundary / speed

        if dt + 1e-12 < time_to_boundary:
            delta = speed * dt
            self.position += delta * self.direction.value
            return dt

        self.position = float(next_floor_boundary)
        self._report_floor_cross_if_needed(next_floor_boundary)

        if self._should_stop_at_floor(next_floor_boundary):
            self.motion_state = MotionState.IDLE
            self._start_door_opening(next_floor_boundary)
            return time_to_boundary

        if not self._has_pending_in_current_direction_from(next_floor_boundary):
            opposite_has_work = (
                self.has_any_pending_below(next_floor_boundary)
                if self.direction == Direction.UP
                else self.has_any_pending_above(next_floor_boundary)
            )
            if opposite_has_work:
                self.direction = Direction.UP if self.direction == Direction.DOWN else Direction.DOWN
                self._emit("direction_changed", {
                    "direction": self.direction.name,
                    "floor": next_floor_boundary,
                })
            else:
                if not self.has_pending():
                    self.direction = Direction.IDLE
                    self.motion_state = MotionState.IDLE
                    self._emit("idle", {"floor": next_floor_boundary})

        return time_to_boundary

    def _step_doors(self, dt: float) -> float:
        if self.door_state == DoorState.CLOSED:
            return dt

        consume = min(dt, self.phase_remaining)
        self.phase_remaining -= consume

        if self.phase_remaining > 1e-12:
            return consume

        current_floor = self.current_floor_rounded()

        if self.door_state == DoorState.OPENING:
            self.door_state = DoorState.OPEN
            self.phase_remaining = self.config.door_open_time
            self._emit("doors_opened", {"floor": current_floor})
            return consume

        if self.door_state == DoorState.OPEN:
            self.door_state = DoorState.CLOSING
            self.phase_remaining = self.config.door_closing_time
            self._emit("doors_closing", {"floor": current_floor})
            return consume

        if self.door_state == DoorState.CLOSING:
            self.door_state = DoorState.CLOSED
            self._emit("doors_closed", {"floor": current_floor})

            if self.manual_target == current_floor:
                self.manual_target = None
                self.control_mode = ControlMode.AUTO
                self._emit("control_mode_changed", {
                    "control_mode": self.control_mode.name,
                    "manual_target": None,
                })

            self._try_start_if_idle()
            return consume

        return consume

    def _start_door_opening(self, floor: int) -> None:
        served = self._serve_floor(floor)
        self.door_state = DoorState.OPENING
        self.phase_remaining = self.config.door_opening_time
        self._emit("doors_opening", {
            "floor": floor,
            "served": served,
        })

    def _serve_floor(self, floor: int) -> dict:
        served_keys: List[Tuple] = []
        served_request_ids: List[int] = []
        stop_reasons: List[str] = []

        car_key = ("CAR", floor)
        if floor in self.car_floors:
            self.car_floors.remove(floor)
            served_keys.append(car_key)
            stop_reasons.append(StopReason.CAR.name)

        up_key = ("HALL", floor, Direction.UP)
        down_key = ("HALL", floor, Direction.DOWN)

        stop_up = floor in self.hall_up_floors
        stop_down = floor in self.hall_down_floors

        if self.direction == Direction.UP:
            if stop_up:
                self.hall_up_floors.remove(floor)
                served_keys.append(up_key)
                stop_reasons.append(StopReason.HALL_UP.name)
            if stop_down and not self.has_any_pending_above(floor) and floor not in self.car_floors:
                self.hall_down_floors.remove(floor)
                served_keys.append(down_key)
                stop_reasons.append(StopReason.HALL_DOWN.name)

        elif self.direction == Direction.DOWN:
            if stop_down:
                self.hall_down_floors.remove(floor)
                served_keys.append(down_key)
                stop_reasons.append(StopReason.HALL_DOWN.name)
            if stop_up and not self.has_any_pending_below(floor) and floor not in self.car_floors:
                self.hall_up_floors.remove(floor)
                served_keys.append(up_key)
                stop_reasons.append(StopReason.HALL_UP.name)

        else:
            if stop_up:
                self.hall_up_floors.remove(floor)
                served_keys.append(up_key)
                stop_reasons.append(StopReason.HALL_UP.name)
            if stop_down:
                self.hall_down_floors.remove(floor)
                served_keys.append(down_key)
                stop_reasons.append(StopReason.HALL_DOWN.name)

        if self.manual_target == floor:
            stop_reasons.append(StopReason.MANUAL_TARGET.name)

        for key in served_keys:
            self.active_request_keys.discard(key)
            items = self.requests_by_key.pop(key, [])
            served_request_ids.extend(r.request_id for r in items)

        return {
            "floor": floor,
            "served_request_ids": served_request_ids,
            "stop_reasons": stop_reasons,
        }

    def _should_stop_at_floor(self, floor: int) -> bool:
        if self.manual_target == floor:
            return True
        if floor in self.car_floors:
            return True

        if self.direction == Direction.UP:
            if floor in self.hall_up_floors:
                return True
            if floor in self.hall_down_floors and not self.has_any_pending_above(floor):
                return True
            return False

        if self.direction == Direction.DOWN:
            if floor in self.hall_down_floors:
                return True
            if floor in self.hall_up_floors and not self.has_any_pending_below(floor):
                return True
            return False

        return floor in self.hall_up_floors or floor in self.hall_down_floors

    def _has_pending_in_current_direction_from(self, floor: int) -> bool:
        if self.direction == Direction.UP:
            return any(f > floor for f in self._all_pending_floors())
        if self.direction == Direction.DOWN:
            return any(f < floor for f in self._all_pending_floors())
        return False

    def _next_floor_boundary_in_direction(self) -> Optional[int]:
        if self.direction == Direction.UP:
            next_floor = math.floor(self.position + 1e-12) + 1
            if next_floor >= self.config.num_floors:
                return None
            return next_floor

        if self.direction == Direction.DOWN:
            next_floor = math.ceil(self.position - 1e-12) - 1
            if next_floor < 0:
                return None
            return next_floor

        return None

    def _report_floor_cross_if_needed(self, floor: int) -> None:
        if floor != self._last_reported_floor:
            self._last_reported_floor = floor
            self._emit("floor_reached", {
                "floor": floor,
                "direction": self.direction.name,
            })

    def _emit(self, event_type: str, payload: dict) -> None:
        event = ElevatorEvent(
            time=round(self.sim_time, 6),
            event_type=event_type,
            payload=payload,
        )
        self.event_log.append(event)
        for listener in self.listeners:
            listener(event)


class ElevatorSystem:
    def __init__(self) -> None:
        self.elevators: Dict[str, Elevator] = {}

    def add_elevator(self, elevator: Elevator) -> None:
        if elevator.elevator_id in self.elevators:
            raise ValueError(f"Winda {elevator.elevator_id} już istnieje")
        self.elevators[elevator.elevator_id] = elevator

    def get_elevator(self, elevator_id: str) -> Elevator:
        return self.elevators[elevator_id]

    def step_all(self, dt: float) -> None:
        for elevator in self.elevators.values():
            elevator.step(dt)

    def snapshot(self) -> dict:
        return {eid: elevator.snapshot() for eid, elevator in self.elevators.items()}


if __name__ == "__main__":
    config = ElevatorConfig(
        num_floors=10,
        floor_travel_time=2.0,
        door_opening_time=1.0,
        door_open_time=2.0,
        door_closing_time=1.0,
        start_floor=0,
    )

    elevator = Elevator("E1", config)

    def printer(event: ElevatorEvent) -> None:
        print(f"[{event.time:6.2f}] {event.event_type} -> {event.payload}")

    elevator.add_listener(printer)

    elevator.submit_request(ElevatorRequest(
        request_type=RequestType.HALL_CALL,
        source=RequestSource.BUTTON,
        created_at=0.0,
        floor=3,
        direction=Direction.UP,
    ))

    elevator.submit_request(ElevatorRequest(
        request_type=RequestType.CAR_CALL,
        source=RequestSource.BUTTON,
        created_at=0.0,
        floor=3,
        target_floor=7,
    ))

    elevator.submit_request(ElevatorRequest(
        request_type=RequestType.HALL_CALL,
        source=RequestSource.SYSTEM,
        created_at=0.0,
        floor=5,
        direction=Direction.DOWN,
    ))

    for _ in range(40):
        elevator.step(0.5)
        print(elevator.snapshot())