"""Academic Writing domain error taxonomy."""


class AcademicDomainError(ValueError):
    """Base error for Academic Writing domain boundary."""

    def __init__(self, message: str, *, code: str = "academic_domain_error") -> None:
        super().__init__(message)
        self.code = code
