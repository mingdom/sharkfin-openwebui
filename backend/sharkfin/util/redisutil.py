import redis
import datetime

redis_client = redis.Redis(host="localhost", port=6379)


def delete_pattern():
    # Scan for keys matching the pattern
    cursor = "0"
    pattern = "AAPL*"  # Example pattern
    while cursor != 0:
        cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=1000)
        if keys:
            print(f"deleting keys: {keys}")
            redis_client.delete(*keys)


def scan():
    # Use the SCAN command for retrieving keys iteratively
    cursor = "0"  # Initial cursor
    while cursor != 0:
        cursor, keys = redis_client.scan(cursor=cursor, match="*", count=100)
        for key in keys:
            print(key.decode("utf-8"))


def check_cache():
    keys = redis_client.keys()  # Get all keys in the cache
    for key in keys:
        # Get the value associated with each key
        print(f"Key: {key}")


def basic_test():
    # Set a value in the cache
    redis_client.set("test_key", "test_value")

    # Retrieve the value from the cache
    cached_value = redis_client.get("test_key")
    print("Cached value:", cached_value.decode("utf-8"))


basic_test()
check_cache()
