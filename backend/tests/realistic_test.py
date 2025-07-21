import asyncio
import aiohttp
import time

async def test_same_user():
    """Test with same users to show cache effectiveness"""
    url = "https://api.badge.iopn.io"
    
    # First, make 100 requests for NEW users
    print("Testing with NEW users (no cache)...")
    start = time.time()
    async with aiohttp.ClientSession() as session:
        for i in range(100):
            email = f"newuser{i}@test.com"
            try:
                async with session.get(f"{url}/api/status/{email}") as resp:
                    await resp.text()
            except:
                pass
    new_user_time = time.time() - start
    
    # Now make 100 requests for SAME users
    print("\nTesting with SAME users (cached)...")
    start = time.time()
    async with aiohttp.ClientSession() as session:
        for i in range(100):
            email = "cacheduser@test.com"  # Same user every time
            try:
                async with session.get(f"{url}/api/status/{email}") as resp:
                    await resp.text()
            except:
                pass
    cached_user_time = time.time() - start
    
    print(f"\nResults:")
    print(f"New users (no cache): {new_user_time:.2f}s")
    print(f"Same user (cached): {cached_user_time:.2f}s")
    print(f"Cache speedup: {new_user_time/cached_user_time:.1f}x faster")

asyncio.run(test_same_user())