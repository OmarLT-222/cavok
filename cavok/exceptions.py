class ParseError(ValueError):
    def __init__(self, message: str, token: str, position: int) -> None:
        super().__init__(message)
        self.token = token
        self.position = position
