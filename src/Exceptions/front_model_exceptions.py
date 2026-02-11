class PmidTxtFileIsNone(Exception):
    def __init__(self, message="PMID text file is None"):
        self.message = message
        super().__init__(self.message)


class NotEnoughPmidsInTxtFile(Exception):
    def __init__(self, message="Not enough PMIDs in text file"):
        self.message = message
        super().__init__(self.message)
