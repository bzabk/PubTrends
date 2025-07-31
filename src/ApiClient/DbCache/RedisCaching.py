import redis.asyncio as aioredis


class RedisCaching:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        self.client = aioredis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    async def set_key(self, key: str, value: str, expiration: int = None):
        await self.client.set(key, value, ex=expiration)

    def get_key(self, key: str):
        return self.client.get(key)

    async def check_if_exists(self,key):
        return bool(self.client.exists(key))



if __name__ == "__main__":
    redis = RedisCaching()
    print(redis.check_if_exists("37871105"))

