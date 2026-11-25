import re
import unicodedata


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE = re.compile(r"[ \t]+")


def sanitize_input(value, *, multiline=False):
    """Normalize user input; Django templates still perform output escaping."""
    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = _CONTROL_CHARS.sub("", normalized)
    if multiline:
        normalized = "\n".join(
            _WHITESPACE.sub(" ", line).strip()
            for line in normalized.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        ).strip()
    else:
        normalized = _WHITESPACE.sub(" ", normalized).strip()
    return normalized
