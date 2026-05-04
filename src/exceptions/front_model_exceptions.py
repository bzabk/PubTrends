class FileValidationError(Exception):
    pass


class PmidTxtFileIsNoneException(Exception):
    pass


class NotEnoughPmidsInTxtFileException(Exception):
    pass


class EmptyDataFrameException(Exception):
    pass
