"""Customer AI — OpenCV-based business card region detection.

Lazily imports OpenCV/numpy/PIL so importing this module never breaks
when those packages are missing. Exposes ``opencv_business_card_region_variants``
which crops and warps the most likely card rectangles from a portrait.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _order_card_points(points: Any) -> Any:
    import numpy as np

    pts = np.asarray(points, dtype="float32")
    point_sum = pts.sum(axis=1)
    point_diff = np.diff(pts, axis=1)
    return np.array(
        [
            pts[np.argmin(point_sum)],
            pts[np.argmin(point_diff)],
            pts[np.argmax(point_sum)],
            pts[np.argmax(point_diff)],
        ],
        dtype="float32",
    )


def _warp_business_card_region(np_image: Any, points: Any) -> Any | None:
    import cv2
    import numpy as np

    rect = _order_card_points(points)
    _top_left, _top_right, bottom_right, bottom_left = rect
    width_a = np.linalg.norm(bottom_right - bottom_left)
    width_b = np.linalg.norm(_top_right - _top_left)
    height_a = np.linalg.norm(_top_right - bottom_right)
    height_b = np.linalg.norm(_top_left - bottom_left)
    target_width = int(max(width_a, width_b))
    target_height = int(max(height_a, height_b))
    if target_width < 80 or target_height < 40:
        return None

    dst = np.array(
        [
            [0, 0],
            [target_width - 1, 0],
            [target_width - 1, target_height - 1],
            [0, target_height - 1],
        ],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(np_image, matrix, (target_width, target_height))
    if warped.shape[0] > warped.shape[1]:
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
    return warped


def opencv_business_card_region_variants(image: Any) -> list[tuple[str, Any]]:
    """Use OpenCV contour detection to crop skewed business-card regions before OCR."""
    try:
        import cv2
        import numpy as np
        from PIL import Image
    except Exception as exc:
        logger.info("OpenCV business card detection is unavailable: %s", exc)
        return []

    np_image = np.array(image.convert("RGB"))
    image_height, image_width = np_image.shape[:2]
    image_area = image_width * image_height
    if image_area <= 0:
        return []

    longest = max(image_width, image_height)
    resize_factor = min(1.0, 1200 / longest) if longest else 1.0
    resized = cv2.resize(
        np_image, None, fx=resize_factor, fy=resize_factor, interpolation=cv2.INTER_AREA
    )
    gray = cv2.cvtColor(resized, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    scored_regions: list[tuple[float, Any, str]] = []
    kernels = {
        "plain": None,
        "closed": cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5)),
        "wide_closed": cv2.getStructuringElement(cv2.MORPH_RECT, (15, 7)),
    }
    canny_thresholds = ((50, 150), (80, 180), (130, 150))

    for canny_low, canny_high in canny_thresholds:
        edges = cv2.Canny(blurred, canny_low, canny_high)
        _, binary = cv2.threshold(edges, 0, 255, cv2.THRESH_BINARY)
        for kernel_name, kernel in kernels.items():
            mask = binary
            if kernel is not None:
                mask = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
                mask = cv2.dilate(mask, kernel, iterations=1)
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for contour in contours:
                if len(contour) < 4:
                    continue
                rotated_rect = cv2.minAreaRect(contour)
                (rect_width, rect_height) = rotated_rect[1]
                if rect_width <= 0 or rect_height <= 0:
                    continue

                box = cv2.boxPoints(rotated_rect) / resize_factor
                rect_area = float(rect_width * rect_height) / (
                    resize_factor * resize_factor
                )
                area_ratio = rect_area / image_area
                aspect = max(rect_width, rect_height) / max(
                    1.0, min(rect_width, rect_height)
                )

                if not (0.12 <= area_ratio <= 0.98 and 1.25 <= aspect <= 2.35):
                    continue

                aspect_score = max(0.0, 1.0 - abs(aspect - 1.75) / 0.75)
                area_score = min(area_ratio / 0.55, 1.0)
                center_x, center_y = rotated_rect[0]
                center_x /= resize_factor
                center_y /= resize_factor
                center_offset = (
                    abs(center_x - image_width / 2) / image_width
                    + abs(center_y - image_height / 2) / image_height
                )
                center_score = max(0.0, 1.0 - center_offset)
                score = area_score * 0.45 + aspect_score * 0.4 + center_score * 0.15
                scored_regions.append(
                    (score, box, f"opencv_card_{kernel_name}_{canny_low}_{canny_high}")
                )

    variants: list[tuple[str, Any]] = []
    seen_boxes: list[Any] = []
    for score, box, name in sorted(
        scored_regions, key=lambda item: item[0], reverse=True
    ):
        if score < 0.45:
            continue
        if any(
            np.linalg.norm(box.mean(axis=0) - seen.mean(axis=0)) < 24
            for seen in seen_boxes
        ):
            continue
        warped = _warp_business_card_region(np_image, box)
        if warped is None:
            continue
        seen_boxes.append(box)
        variants.append((name, Image.fromarray(warped)))
        if len(variants) >= 2:
            break

    return variants


__all__ = [
    "opencv_business_card_region_variants",
    "_opencv_business_card_region_variants",
]


# Back-compat alias for tests / external imports that reference the
# original underscored name from the monolithic ``customer_ai`` module.
_opencv_business_card_region_variants = opencv_business_card_region_variants
