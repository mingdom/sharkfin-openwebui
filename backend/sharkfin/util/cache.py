import redis
from pandas import DataFrame
import pyarrow as pa

from sharkfin.util.logger import Log
logger = Log().get_logger()


class RedisCache:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            try:
                cls._instance = super().__new__(cls)
                cls._instance.pool = redis.ConnectionPool(
                    host='localhost', port=6379)
                cls._instance.redis = redis.Redis(
                    connection_pool=cls._instance.pool)
            except Exception as e:
                # Don't use Redis if it's not set up
                logger.warn(f'Error starting Redis:\n{e}')
                cls._instance = {}
        return cls._instance

    def set(self, key, value, ex):
        self.redis.set(key, value, ex)

    def get(self, key):
        if self.redis == {}:
            return None

        return self.redis.get(key)

    def set_dataframe(self, cache_key, value: DataFrame, ex):
        # serialize with pyarrow
        result = pa.serialize_pandas(value).to_pybytes()
        logger.debug(
            f'set_dataframe key={cache_key}:len={len(result)},type={type(result)}'
        )
        self.set(cache_key, result, ex=ex)

    def get_dataframe(self, cache_key):
        """ Function used specifically to load DataFrame objects from cache
        """
        logger.debug(f'get_dataframe: {cache_key}')
        cached_data = self.get(cache_key)
        if cached_data:
            logger.debug(
                f'get_dataframe: cached hit for {cache_key}:len={len(cached_data)},type={type(cached_data)}')
            result = pa.deserialize_pandas(cached_data)
            logger.debug(f'data from cache: {result}')
            return result
        return None
