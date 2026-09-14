class DigipayException(Exception):
    def __init__(self, message, status_code=None, response_data=None):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class DigipayAuthenticationError(DigipayException):
    pass


class DigipayAPIError(DigipayException):
    pass


class DigipayValidationError(DigipayException):
    """Raised for client-side payload validation errors, before hitting the API."""
