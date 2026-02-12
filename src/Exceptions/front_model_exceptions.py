class PmidTxtFileIsNoneException(Exception):
    def __init__(self, message="PMID text file is None"):
        self.message = message
        super().__init__(self.message)


class NotEnoughPmidsInTxtFileException(Exception):
    def __init__(self, message="Not enough PMIDs in text file"):
        self.message = message
        super().__init__(self.message)

class EmptyDataFrameException(Exception):
    def __init__(self,message="Empty PMID dataframe, failed to load both saved and unsaved pmids"):
        self.message=message
        super().__init__(self.message)
