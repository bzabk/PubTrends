class AppException(Exception):
    pass


class TransientException(AppException):
    pass


class PermanentException(AppException):
    pass


class GatewayException(TransientException):
    pass


class RequestException(TransientException):
    pass


class RedisRequestException(TransientException):
    pass


class HttpStatusException(TransientException):
    pass


class ParserError(PermanentException):
    pass


class CacheSerializationError(PermanentException):
    pass


class InvalidApiKeyException(PermanentException):
    pass


class MissingAPIKeyError(PermanentException):
    pass


class ApiUnavailableException(PermanentException):
    pass


class SessionNotInitializedError(PermanentException):
    pass
