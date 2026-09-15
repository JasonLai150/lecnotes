"""The single exception type every failure travels through.

cli.py catches this in one place and renders it as human text or JSON, which is
what keeps the two output modes from drifting apart.
"""

# Missing or broken external tooling is the user's environment, not their input,
# so it gets its own exit code.
_DEPENDENCY_CODES = {"missing_converter", "conversion_failed"}


class LecnotesError(Exception):
    def __init__(self, code: str, message: str, **detail):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail

    @property
    def exit_code(self) -> int:
        return 2 if self.code in _DEPENDENCY_CODES else 1

    def to_dict(self) -> dict:
        return {"ok": False, "error": self.code, "message": self.message, **self.detail}
