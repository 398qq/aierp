"""CJK font discovery for ReportLab PDF generation.

Locates a usable CJK-capable TrueType font on the host so the
quotation and sales-order PDFs render Chinese characters correctly
across common Linux distros. Tries the curated CHINESE_FONT_PATHS
first, then queries fontconfig (fc-match) for any installed CJK
font, then walks the standard font directories. Falls back to
ReportLab's bundled STSong-Light CID font and ultimately to
Helvetica when nothing else is available.
"""
from __future__ import annotations

import logging
import os
import subprocess

logger = logging.getLogger(__name__)

# Known CJK fonts that ReportLab can embed on common Linux distributions. Prefer
# these over broad directory scanning so we do not accidentally pick a partial
# test font such as Unifont sample variants.
CHINESE_FONT_PATHS = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/truetype/arphic/ukai.ttc",
    "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
]

# Font filename keywords to try in order. Keep these broad because distro font
# filenames often omit spaces, e.g. NotoSansCJK-Regular.otf.
CHINESE_FONT_KEYWORDS = [
    "notosanscjk",
    "noto sans cjk",
    "sourcehansans",
    "source han sans",
    "wenquanyi",
    "wqy",
    "uming",
    "ukai",
    "unifont",
    "ipag",
    "ipa",
]
PARTIAL_FONT_KEYWORDS = ["sample", "csur", "upper"]

# Fallback font if no Chinese font is available
FALLBACK_FONT = "Helvetica"

font_dirs = [
    "/usr/share/fonts",
    "/usr/local/share/fonts",
]


def _register_font(font_path: str) -> str | None:
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        registered_name = "AIERP_CJK"
        pdfmetrics.registerFont(TTFont(registered_name, font_path))
        logger.info("Registered PDF CJK font: %s", font_path)
        return registered_name
    except Exception as e:
        logger.debug("Could not register CJK font %s: %s", font_path, e)
        return None


def get_chinese_font() -> str:
    """Find an available Chinese font, falling back to Helvetica if none found."""
    try:
        for font_path in CHINESE_FONT_PATHS:
            if os.path.exists(font_path):
                registered = _register_font(font_path)
                if registered:
                    return registered

        try:
            fc_match = subprocess.run(
                ["fc-match", "-f", "%{file}\n", "sans:lang=zh-cn"],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
            for font_path in fc_match.stdout.splitlines():
                if not font_path:
                    continue
                registered = _register_font(font_path)
                if registered:
                    return registered
        except Exception as e:
            logger.debug("Could not query fontconfig for Chinese fonts: %s", e)

        try:
            for font_dir in font_dirs:
                if not os.path.exists(font_dir):
                    continue
                for root, dirs, files in os.walk(font_dir):
                    for f in files:
                        if f.endswith((".ttf", ".otf", ".ttc")):
                            font_path = os.path.join(root, f)
                            font_name = os.path.splitext(f)[0].replace("_", " ").replace("-", " ")
                            normalized_name = font_name.lower().replace(" ", "")
                            if any(keyword in normalized_name for keyword in PARTIAL_FONT_KEYWORDS):
                                continue
                            if not any(keyword.replace(" ", "") in normalized_name for keyword in CHINESE_FONT_KEYWORDS):
                                continue
                            registered = _register_font(font_path)
                            if registered:
                                return registered
        except Exception as e:
            logger.warning("Could not register custom fonts: %s", e)

        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont

            cid_font = "STSong-Light"
            pdfmetrics.registerFont(UnicodeCIDFont(cid_font))
            return cid_font
        except Exception as e:
            logger.warning("Could not register ReportLab CID Chinese font: %s", e)
    except Exception as e:
        logger.warning("PDF font discovery failed: %s", e)

    return FALLBACK_FONT


# Cache the font name
_CHINESE_FONT = get_chinese_font()
logger.info(f"PDF service using font: {_CHINESE_FONT}")


__all__ = [
    "CHINESE_FONT_PATHS",
    "CHINESE_FONT_KEYWORDS",
    "PARTIAL_FONT_KEYWORDS",
    "FALLBACK_FONT",
    "get_chinese_font",
]
