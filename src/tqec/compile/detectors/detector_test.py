import pytest
import stim

from tqec.circuit.measurement import Measurement
from tqec.circuit.measurement_map import MeasurementRecordsMap
from tqec.circuit.qubit import GridQubit
from tqec.compile.detectors.detector import Detector
from tqec.utils.coordinates import StimCoordinates
from tqec.utils.exceptions import TQECError


@pytest.fixture(name="measurement")
def measurement_fixture() -> Measurement:
    return Measurement(GridQubit(0, 0), -1)


@pytest.fixture(name="mrecords_map")
def mrecords_map_fixture() -> MeasurementRecordsMap:
    return MeasurementRecordsMap({GridQubit(0, 0): [-1]})


def test_detector_creation(measurement: Measurement) -> None:
    with pytest.raises(TQECError, match="^Trying to create a detector without any measurement.$"):
        Detector(frozenset(), StimCoordinates(0, 0, 0))

    Detector(frozenset([measurement]), StimCoordinates(0, 3, 0))


def test_detector_to_instruction(
    measurement: Measurement, mrecords_map: MeasurementRecordsMap
) -> None:
    detector = Detector(frozenset([measurement]), StimCoordinates(1, 1, 0))
    instruction = detector.to_instruction(mrecords_map)
    assert instruction.name == "DETECTOR"
    assert instruction.targets_copy() == [stim.target_rec(-1)]
    assert instruction.gate_args_copy() == [1, 1, 0]

    empty_mrecords_map = MeasurementRecordsMap()
    with pytest.raises(TQECError):
        detector.to_instruction(empty_mrecords_map)


def test_detector_offset_spatially_by(measurement: Measurement) -> None:
    detector = Detector(frozenset([measurement]), StimCoordinates(1, 1, 0))
    offset_detector = detector.offset_spatially_by(45, -2)
    assert offset_detector.measurements == frozenset([measurement.offset_spatially_by(45, -2)])
    assert offset_detector.coordinates.to_stim_coordinates() == (46, -1, 0)


def test_detector_dict(measurement: Measurement) -> None:
    detector = Detector(frozenset([measurement]), StimCoordinates(1, 1, 0))
    detector_dict = detector.to_dict()
    assert detector_dict["measurements"] == [measurement.to_dict()]
    assert detector_dict["coordinates"] == StimCoordinates(1, 1, 0).to_dict()

    new_detector = Detector.from_dict(detector_dict)
    assert new_detector.measurements == frozenset([measurement])
    assert new_detector.coordinates == StimCoordinates(1, 1, 0)
