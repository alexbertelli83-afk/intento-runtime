class IntentoError(Exception):
    """Base class for INTENTO runtime errors."""

    category = "Runtime error"

    def __init__(self, message: str, line: int | None = None):
        super().__init__(message)
        self.message = message
        self.line = line

    def __str__(self) -> str:
        if self.line is not None:
            return f"{self.category} on line {self.line}: {self.message}"
        return f"{self.category}: {self.message}"


class IntentoSyntaxError(IntentoError):
    category = "Syntax error"


class IntentoSemanticError(IntentoError):
    category = "Semantic error"


class IntentoTypeError(IntentoError):
    category = "Type error"


class IntentoRuntimeError(IntentoError):
    category = "Runtime error"


class IntentoFileError(IntentoError):
    category = "File error"


class IntentoSafetyError(IntentoError):
    category = "Safety error"


class IntentoLibraryError(IntentoError):
    category = "Library error"


class IntentoActionError(IntentoError):
    category = "Action error"


class IntentoModuleError(IntentoError):
    category = "Module error"


class IntentoProjectError(IntentoError):
    category = "Project error"


class IntentoDateError(IntentoError):
    category = "Date error"


class IntentoJSONError(IntentoError):
    category = "JSON error"


class IntentoCSVError(IntentoError):
    category = "CSV error"


class IntentoConversionError(IntentoError):
    category = "Conversion error"
