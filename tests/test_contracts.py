"""Contratos de src/draw/contracts.py: validação e imutabilidade."""

import subprocess
import sys
from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from draw.contracts import FramePacket, InkState, PageIdentity, SheetQuad

QUAD = np.array(
    [[100.0, 100.0], [500.0, 100.0], [500.0, 400.0], [100.0, 400.0]],
    dtype=np.float32,
)


def _frame(shape=(4, 4, 3), dtype=np.uint8):
    return np.zeros(shape, dtype=dtype)


# --- FramePacket --------------------------------------------------------


def test_frame_packet_valid():
    packet = FramePacket(image=_frame(), captured_at=1.5, sequence=3)
    assert packet.image.shape == (4, 4, 3)
    assert packet.sequence == 3


@pytest.mark.parametrize(
    "image",
    [
        _frame((4, 4)),  # 2D
        _frame((4,)),  # 1D
        _frame((4, 4, 1)),  # canal único
        _frame((4, 4, 4)),  # RGBA
        _frame(dtype=np.float32),  # dtype errado
        [[0, 1], [2, 3]],  # não é ndarray
    ],
)
def test_frame_packet_rejects_bad_image(image):
    with pytest.raises(ValueError):
        FramePacket(image=image, captured_at=0.0, sequence=0)


def test_frame_packet_rejects_negative_sequence():
    with pytest.raises(ValueError, match="sequence"):
        FramePacket(image=_frame(), captured_at=0.0, sequence=-1)


def test_frame_packet_is_frozen():
    packet = FramePacket(image=_frame(), captured_at=0.0, sequence=0)
    with pytest.raises(FrozenInstanceError):
        packet.sequence = 9


# --- SheetQuad ------------------------------------------------------------


def test_sheet_quad_valid_and_present():
    quad = SheetQuad(corners=QUAD, verdict="paper", detector="neural")
    assert quad.present
    assert quad.corners.dtype == np.float32
    assert quad.corners.shape == (4, 2)


def test_sheet_quad_absent():
    quad = SheetQuad(corners=None, verdict=None)
    assert not quad.present
    assert quad.detector == ""


def test_sheet_quad_normalizes_and_copies_corners():
    source = QUAD.astype(np.float64)
    quad = SheetQuad(corners=source, verdict="paper")
    assert quad.corners.dtype == np.float32
    source[0, 0] = -999.0
    assert quad.corners[0, 0] == 100.0, "o contrato não pode ver o array externo"


@pytest.mark.parametrize(
    "corners",
    [
        np.zeros((3, 2), dtype=np.float32),
        np.zeros((4, 3), dtype=np.float32),
        np.zeros((8,), dtype=np.float32),
    ],
)
def test_sheet_quad_rejects_bad_corners(corners):
    with pytest.raises(ValueError, match="4, 2"):
        SheetQuad(corners=corners, verdict="paper")


def test_sheet_quad_rejects_bad_verdict():
    with pytest.raises(ValueError, match="verdict"):
        SheetQuad(corners=QUAD, verdict="table")


def test_sheet_quad_is_frozen():
    quad = SheetQuad(corners=QUAD, verdict="paper")
    with pytest.raises(FrozenInstanceError):
        quad.verdict = None


# --- PageIdentity ---------------------------------------------------------


def test_page_identity_valid():
    ident = PageIdentity(generation=2, decision="new_page", recall=0.5)
    assert ident.decision == "new_page"
    assert ident.containment is None


@pytest.mark.parametrize("decision", ["same", "new_page", "defer"])
def test_page_identity_decisions(decision):
    assert PageIdentity(generation=0, decision=decision).decision == decision


def test_page_identity_rejects_bad_decision():
    with pytest.raises(ValueError, match="decision"):
        PageIdentity(generation=0, decision="maybe")


@pytest.mark.parametrize("name", ["recall", "containment"])
@pytest.mark.parametrize("value", [-0.1, 1.5])
def test_page_identity_rejects_evidence_out_of_range(name, value):
    with pytest.raises(ValueError, match=name):
        PageIdentity(generation=0, decision="same", **{name: value})


@pytest.mark.parametrize("value", [0.0, 0.5, 1.0])
def test_page_identity_accepts_evidence_at_bounds(value):
    ident = PageIdentity(
        generation=0, decision="defer", recall=value, containment=value
    )
    assert ident.recall == value


def test_page_identity_is_frozen():
    ident = PageIdentity(generation=0, decision="same")
    with pytest.raises(FrozenInstanceError):
        ident.decision = "defer"


# --- InkState -------------------------------------------------------------


def _mask(shape=(8, 8), dtype=np.uint8):
    return np.zeros(shape, dtype=dtype)


def test_ink_state_valid():
    state = InkState(
        confirmed=_mask(), provisional=_mask(), generation=1, anchor_corners=QUAD
    )
    assert state.generation == 1
    assert state.anchor_corners.dtype == np.float32


def test_ink_state_allows_none_masks():
    state = InkState(confirmed=None, provisional=None, generation=0)
    assert state.anchor_corners is None


@pytest.mark.parametrize("name", ["confirmed", "provisional"])
@pytest.mark.parametrize(
    "mask",
    [
        _mask((8, 8, 3)),  # 3D
        _mask(dtype=np.float32),  # dtype errado
        _mask(dtype=np.bool_),  # dtype errado
    ],
)
def test_ink_state_rejects_bad_masks(name, mask):
    kwargs = {"confirmed": None, "provisional": None, "generation": 0}
    kwargs[name] = mask
    with pytest.raises(ValueError, match=name):
        InkState(**kwargs)


def test_ink_state_rejects_bad_anchor_corners():
    with pytest.raises(ValueError):
        InkState(
            confirmed=None,
            provisional=None,
            generation=0,
            anchor_corners=np.zeros((3, 2), dtype=np.float32),
        )


def test_ink_state_is_frozen():
    state = InkState(confirmed=None, provisional=None, generation=0)
    with pytest.raises(FrozenInstanceError):
        state.generation = 7


def test_sheet_quad_rejects_corners_without_verdict():
    with pytest.raises(ValueError, match="juntos"):
        SheetQuad(corners=QUAD, verdict=None)


def test_sheet_quad_rejects_verdict_without_corners():
    with pytest.raises(ValueError, match="juntos"):
        SheetQuad(corners=None, verdict="paper")


def test_sheet_quad_corners_are_read_only():
    quad = SheetQuad(corners=QUAD, verdict="paper")
    with pytest.raises(ValueError):
        quad.corners[0, 0] = 99.0
    # a fonte do chamador continua gravável
    source = QUAD.copy()
    SheetQuad(corners=source, verdict="paper")
    source[0, 0] = 1.0


def test_frame_packet_image_is_read_only_view():
    frame = np.zeros((4, 5, 3), dtype=np.uint8)
    pkt = FramePacket(image=frame, captured_at=0.0, sequence=0)
    with pytest.raises(ValueError):
        pkt.image[0, 0, 0] = 7
    frame[0, 0, 0] = 7  # o buffer original segue gravável


def test_ink_state_masks_and_anchor_are_read_only():
    confirmed = np.zeros((3, 3), dtype=np.uint8)
    anchor = QUAD.copy()
    state = InkState(
        confirmed=confirmed,
        provisional=None,
        generation=0,
        anchor_corners=anchor,
    )
    with pytest.raises(ValueError):
        state.confirmed[0, 0] = 255
    with pytest.raises(ValueError):
        state.anchor_corners[0, 0] = 0.0
    confirmed[0, 0] = 255  # a fonte segue gravável


# --- fronteira de dependências --------------------------------------------


def test_contracts_import_leaves_out_heavy_dependencies():
    """Importar draw.contracts não pode puxar torch, pandas ou cv2."""
    code = (
        "import sys\n"
        "import draw.contracts\n"
        "for name in ('torch', 'pandas', 'cv2'):\n"
        "    assert name not in sys.modules, name\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
