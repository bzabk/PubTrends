import redis

class RedisCaching:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        self.client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


    def set_key(self, key: str, value: str, expiration: int = None):
        self.client.set(key, value, ex=expiration)

    def get_key(self, key: str):
        return self.client.get(key)

