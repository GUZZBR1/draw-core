import cv2
import numpy as np

from draw.ink.occlusion import _has_dense_pixel_seed


def test_four_by_four_raster_blob_meets_four_pixel_seed_extent():
    region = np.zeros((12, 12), dtype=bool)
    region[4:8, 4:8] = True

    assert _has_dense_pixel_seed(region)


def test_seed_rejects_blob_smaller_than_four_pixel_extent():
    region = np.zeros((12, 12), dtype=bool)
    region[2:5, 2:10] = True

    assert not _has_dense_pixel_seed(region)


def test_seed_rejects_hollow_l_shape():
    region = np.zeros((40, 40), dtype=bool)
    region[4:8, 4:34] = True
    region[4:34, 4:8] = True

    assert not _has_dense_pixel_seed(region)


def test_seed_accepts_rotated_solid_stroke():
    region = np.zeros((32, 32), dtype=np.uint8)
    cv2.line(region, (4, 27), (27, 4), 1, thickness=5)

    assert _has_dense_pixel_seed(region.astype(bool))
