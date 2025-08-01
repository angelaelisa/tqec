from collections.abc import Iterable
from typing import cast

import numpy
import pytest

from tqec.circuit.measurement import Measurement
from tqec.circuit.qubit import GridQubit
from tqec.compile.detectors.database import (
    DetectorDatabase,
    _DetectorDatabaseKey,  # pyright: ignore[reportPrivateUsage]
)
from tqec.compile.detectors.detector import Detector
from tqec.compile.specs.library.generators.fixed_bulk import (
    FixedBulkConventionGenerator,
)
from tqec.plaquette.compilation.base import IdentityPlaquetteCompiler
from tqec.plaquette.plaquette import Plaquettes
from tqec.plaquette.rpng.translators.default import DefaultRPNGTranslator
from tqec.templates.qubit import QubitTemplate
from tqec.templates.subtemplates import (
    SubTemplateType,
    get_spatially_distinct_subtemplates,
)
from tqec.utils.coordinates import StimCoordinates
from tqec.utils.enums import Basis, Orientation
from tqec.utils.exceptions import TQECError

GENERATOR = FixedBulkConventionGenerator(DefaultRPNGTranslator(), IdentityPlaquetteCompiler)
# Pre-computing Plaquettes and SubTemplateType instances to be able to re-use them
# in tests.
# WARNING: the order in which values of the two constants below are defined is
#          important. If you change these lists, you will likely have to also
#          change a few pre-computed values in tests that check that the computed
#          hashes are reliable across OS, Python version, interpreter, ...
PLAQUETTE_COLLECTIONS: list[Plaquettes] = [
    GENERATOR.get_memory_qubit_plaquettes(Orientation.HORIZONTAL),
    GENERATOR.get_memory_qubit_plaquettes(reset=Basis.Z),
    GENERATOR.get_memory_qubit_plaquettes(reset=Basis.X),
    GENERATOR.get_memory_qubit_plaquettes(measurement=Basis.Z),
    GENERATOR.get_memory_qubit_plaquettes(Orientation.VERTICAL),
]
# Note: sorting is important here to guarantee the order in which subtemplates
#       are in the SUBTEMPLATES list. See comment above PLAQUETTE_COLLECTIONS
#       for more information.
SUBTEMPLATES: list[SubTemplateType] = list(
    cast(
        Iterable[SubTemplateType],
        numpy.sort(
            list(
                get_spatially_distinct_subtemplates(
                    QubitTemplate().instantiate(k=10), manhattan_radius=2
                ).subtemplates.values()
            ),
        ),
    )
)

DETECTORS: list[frozenset[Detector]] = [
    frozenset(
        [
            Detector(frozenset([Measurement(GridQubit(0, 0), -1)]), StimCoordinates(0, 0)),
            Detector(
                frozenset([Measurement(GridQubit(0, 0), -1), Measurement(GridQubit(0, 0), -2)]),
                StimCoordinates(0, 0, 1),
            ),
            Detector(
                frozenset(
                    [
                        Measurement(GridQubit(0, 0), -1),
                        Measurement(GridQubit(-1, -1), -1),
                        Measurement(GridQubit(-1, 1), -1),
                        Measurement(GridQubit(1, -1), -1),
                        Measurement(GridQubit(1, 1), -1),
                    ]
                ),
                StimCoordinates(0, 0, 2),
            ),
        ]
    ),
    frozenset(
        [
            Detector(frozenset([Measurement(GridQubit(0, 0), -1)]), StimCoordinates(0, 0)),
            Detector(
                frozenset([Measurement(GridQubit(0, 0), -1), Measurement(GridQubit(0, 0), -2)]),
                StimCoordinates(0, 0, 1),
            ),
        ]
    ),
]


def test_detector_database_key_creation() -> None:
    _DetectorDatabaseKey((SUBTEMPLATES[0],), (PLAQUETTE_COLLECTIONS[0],))
    _DetectorDatabaseKey(SUBTEMPLATES[1:5], PLAQUETTE_COLLECTIONS[1:5])
    with pytest.raises(
        TQECError,
        match="^DetectorDatabaseKey can only store an equal number of "
        "subtemplates and plaquettes. Got 4 subtemplates and 3 plaquettes.$",
    ):
        _DetectorDatabaseKey(SUBTEMPLATES[1:5], PLAQUETTE_COLLECTIONS[1:4])


def test_detector_database_key_num_timeslices() -> None:
    for i in range(min(len(PLAQUETTE_COLLECTIONS), len(SUBTEMPLATES))):
        assert _DetectorDatabaseKey(SUBTEMPLATES[:i], PLAQUETTE_COLLECTIONS[:i]).num_timeslices == i


def test_detector_database_key_hash() -> None:
    dbkey = _DetectorDatabaseKey(SUBTEMPLATES[1:5], PLAQUETTE_COLLECTIONS[1:5])
    assert hash(dbkey) == hash(dbkey)
    # This is a value that has been pre-computed locally. It is hard-coded here
    # to check that the hash of a dbkey is reliable and does not change depending
    # on the Python interpreter, Python version, host OS, process ID, ...
    assert hash(dbkey) == 1068059953232381272

    dbkey = _DetectorDatabaseKey(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1])
    assert hash(dbkey) == hash(dbkey)
    # This is a value that has been pre-computed locally. It is hard-coded here
    # to check that the hash of a dbkey is reliable and does not change depending
    # on the Python interpreter, Python version, host OS, process ID, ...
    assert hash(dbkey) == 1986764458427930321


def test_detector_database_creation() -> None:
    DetectorDatabase()


def test_detector_database_mutation() -> None:
    db = DetectorDatabase()
    db.add_situation(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1], DETECTORS[0])
    db.add_situation(SUBTEMPLATES[:2], PLAQUETTE_COLLECTIONS[:2], DETECTORS[1])
    with pytest.raises(
        TQECError,
        match="^DetectorDatabaseKey can only store an equal number of "
        "subtemplates and plaquettes. Got 1 subtemplates and 2 plaquettes.$",
    ):
        db.add_situation(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:2], DETECTORS[1])

    detectors = db.get_detectors(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1])
    assert detectors is not None
    assert detectors == DETECTORS[0]

    # Override
    db.add_situation(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1], DETECTORS[1])
    detectors2 = db.get_detectors(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1])
    assert detectors2 is not None
    assert detectors2 == DETECTORS[1]

    # Removing
    db.remove_situation(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1])
    detectors3 = db.get_detectors(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1])
    assert detectors3 is None


def test_detector_database_freeze() -> None:
    db = DetectorDatabase()
    db.add_situation(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1], DETECTORS[0])
    db.add_situation(SUBTEMPLATES[:2], PLAQUETTE_COLLECTIONS[:2], DETECTORS[1])

    db.freeze()
    with pytest.raises(TQECError, match="^Cannot remove a situation to a frozen database.$"):
        db.remove_situation(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1])
    with pytest.raises(TQECError, match="^Cannot add a situation to a frozen database.$"):
        db.add_situation(SUBTEMPLATES[:4], PLAQUETTE_COLLECTIONS[:4], DETECTORS[1])

    detectors = db.get_detectors(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1])
    assert detectors is not None
    assert detectors == DETECTORS[0]

    db.unfreeze()
    db.remove_situation(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1])
    db.add_situation(SUBTEMPLATES[:4], PLAQUETTE_COLLECTIONS[:4], DETECTORS[1])
    detectors2 = db.get_detectors(SUBTEMPLATES[:4], PLAQUETTE_COLLECTIONS[:4])
    assert detectors2 is not None
    assert detectors2 == DETECTORS[1]


def test_detector_database_translation_invariance() -> None:
    db = DetectorDatabase()
    db.add_situation(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1], DETECTORS[0])

    offset = 36
    translated_subtemplate = SUBTEMPLATES[0] + offset
    translated_plaquettes = PLAQUETTE_COLLECTIONS[0].map_indices(lambda i: i + offset)
    detectors = db.get_detectors((translated_subtemplate,), (translated_plaquettes,))
    assert detectors is not None
    assert detectors == DETECTORS[0]


def test_detector_database_dict() -> None:
    db = DetectorDatabase()
    db.add_situation(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1], DETECTORS[0])
    db.add_situation(SUBTEMPLATES[:2], PLAQUETTE_COLLECTIONS[:2], DETECTORS[1])

    # Check that the database can be converted to a dict and back
    db_dict = db.to_dict()
    new_db = DetectorDatabase.from_dict(db_dict)

    # Check that the new database has the same situations as the original
    detectors0 = new_db.get_detectors(SUBTEMPLATES[:1], PLAQUETTE_COLLECTIONS[:1])
    assert detectors0 is not None
    assert detectors0 == DETECTORS[0]
    detectors1 = new_db.get_detectors(SUBTEMPLATES[:2], PLAQUETTE_COLLECTIONS[:2])
    assert detectors1 is not None
    assert detectors1 == DETECTORS[1]
