from abc import abstractmethod, ABC

class AbstractApiDataFrameCreator(ABC):

    @abstractmethod
    async def create_data_frame(self):
        pass

    @abstractmethod
    async def send_request(self,idx):
        pass

    @abstractmethod
    async def response_parser(self,response,idx=None):
        pass

    @staticmethod
    def divide_into_packages(list_to_chunks, package_size=10):
        chunks = []
        for i in range(0, len(list_to_chunks), 10):
            chunks.append(list_to_chunks[i:i + package_size])
        return chunks