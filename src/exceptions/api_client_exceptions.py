class SingleAsyncCallException(Exception):
    def __init__(self, message="Error during single asynchronous API call"):
        self.message = message
        super().__init__(self.message)


class GatewayException(SingleAsyncCallException):
    pass
class InfoSummaryException(SingleAsyncCallException):
    def __init__(self, message="Error during info summary retrieval phase from API"):
        super().__init__(message)


class OverallDesignException(SingleAsyncCallException):
    def __init__(self, message="Error during overall design retrieval phase from API"):
        super().__init__(message)


class PmidException(SingleAsyncCallException):
    def __init__(self, message="Error during PMID processing phase from API"):
        super().__init__(message)


class ResponseStatusException(Exception):
    def __init__(self, message="Invalid API response status"):
        self.message = message
        super().__init__(self.message)

class ParserError(Exception):
    pass

