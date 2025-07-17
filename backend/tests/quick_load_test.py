# quick_load_test.py - Quick test to find breaking point
import asyncio
import aiohttp
import time
from datetime import datetime
import sys

class QuickLoadTest:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.metrics = {
            "requests": 0,
            "success": 0,
            "errors": 0,
            "timeouts": 0,
            "response_times": [],
            "error_details": {}
        }
        
    async def test_endpoint(self, session, endpoint, method="GET", data=None):
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        start = time.time()
        
        try:
            async with session.request(method, url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response_time = time.time() - start
                self.metrics["requests"] += 1
                
                if response.status < 400:
                    self.metrics["success"] += 1
                else:
                    self.metrics["errors"] += 1
                    error_key = f"{response.status}_{endpoint}"
                    self.metrics["error_details"][error_key] = self.metrics["error_details"].get(error_key, 0) + 1
                
                self.metrics["response_times"].append(response_time)
                return response.status, response_time
                
        except asyncio.TimeoutError:
            self.metrics["timeouts"] += 1
            self.metrics["errors"] += 1
            return 0, 10.0
        except Exception as e:
            self.metrics["errors"] += 1
            error_key = f"Exception_{type(e).__name__}"
            self.metrics["error_details"][error_key] = self.metrics["error_details"].get(error_key, 0) + 1
            return 0, 0
    
    async def user_session(self, session, user_id):
        """Simulate a single user session"""
        email = f"loadtest_{user_id}_{int(time.time())}@test.com"
        
        # Test critical endpoints
        endpoints = [
            ("GET", f"/api/status/{email}", None),
            ("POST", "/auth/email/register-instant", {"email": email, "referral_code": "TEST"}),
            ("GET", f"/api/status/{email}", None),
            ("GET", f"/api/dashboard/{email}", None),
        ]
        
        for method, endpoint, data in endpoints:
            await self.test_endpoint(session, endpoint, method, data)
            await asyncio.sleep(0.1)  # Small delay between requests
    
    async def run_concurrent_users(self, num_users):
        """Run test with specified number of concurrent users"""
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for i in range(num_users):
                task = asyncio.create_task(self.user_session(session, i))
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def print_results(self, num_users, duration):
        """Print test results"""
        avg_response = sum(self.metrics["response_times"]) / len(self.metrics["response_times"]) if self.metrics["response_times"] else 0
        success_rate = (self.metrics["success"] / self.metrics["requests"] * 100) if self.metrics["requests"] > 0 else 0
        
        print(f"\n--- Results for {num_users} concurrent users ---")
        print(f"Duration: {duration:.2f}s")
        print(f"Total requests: {self.metrics['requests']}")
        print(f"Requests/sec: {self.metrics['requests'] / duration:.2f}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Errors: {self.metrics['errors']}")
        print(f"Timeouts: {self.metrics['timeouts']}")
        print(f"Avg response time: {avg_response:.3f}s")
        
        if self.metrics["error_details"]:
            print("\nError breakdown:")
            for error, count in self.metrics["error_details"].items():
                print(f"  {error}: {count}")

async def find_breaking_point(base_url):
    """Gradually increase load until system breaks"""
    print(f"Finding breaking point for {base_url}")
    print("="*60)
    
    user_counts = [1, 10, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    
    for num_users in user_counts:
        print(f"\nTesting with {num_users} concurrent users...")
        
        test = QuickLoadTest(base_url)
        start_time = time.time()
        
        try:
            await test.run_concurrent_users(num_users)
            duration = time.time() - start_time
            test.print_results(num_users, duration)
            
            # Check if system is failing
            success_rate = (test.metrics["success"] / test.metrics["requests"] * 100) if test.metrics["requests"] > 0 else 0
            
            if success_rate < 50 or test.metrics["timeouts"] > test.metrics["requests"] * 0.1:
                print(f"\n⚠️  BREAKING POINT FOUND: System failing at {num_users} concurrent users!")
                print(f"Success rate: {success_rate:.1f}%")
                print(f"Timeout rate: {test.metrics['timeouts'] / test.metrics['requests'] * 100:.1f}%")
                break
                
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
            break
        except Exception as e:
            print(f"\nTest failed with error: {e}")
            break
        
        # Cool down between tests
        if num_users < user_counts[-1]:
            print("\nCooling down for 10 seconds...")
            await asyncio.sleep(10)

async def monitor_system(base_url, duration=300):
    """Monitor system performance over time"""
    print(f"Monitoring system for {duration} seconds")
    print("Time\t\tActive\tReq/s\tAvg RT\tErrors")
    print("="*50)
    
    connector = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession(connector=connector) as session:
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Test health endpoint
            health_start = time.time()
            try:
                async with session.get(f"{base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    health_time = time.time() - health_start
                    status = "✓" if resp.status == 200 else "✗"
            except:
                health_time = 5.0
                status = "✗"
            
            # Test a few status checks
            tasks = []
            for i in range(10):
                email = f"monitor_{i}@test.com"
                task = session.get(f"{base_url}/api/status/{email}", timeout=aiohttp.ClientTimeout(total=5))
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            success = sum(1 for r in responses if not isinstance(r, Exception) and r.status < 400)
            errors = 10 - success
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"{timestamp}\t{status}\t{success}/10\t{health_time:.3f}s\t{errors}")
            
            await asyncio.sleep(5)

# Main execution
async def main():
    BASE_URL = "https://api.badge.iopn.io"  # Change to your URL
    
    print("Badge System Load Tester")
    print("="*60)
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now()}")
    print("="*60)
    
    while True:
        print("\nSelect test type:")
        print("1. Quick health check")
        print("2. Find breaking point")
        print("3. Monitor system (5 min)")
        print("4. Stress test (1000 users)")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ")
        
        if choice == "1":
            # Quick health check
            test = QuickLoadTest(BASE_URL)
            async with aiohttp.ClientSession() as session:
                status, response_time = await test.test_endpoint(session, "/health")
                print(f"\nHealth check: Status={status}, Response time={response_time:.3f}s")
                
        elif choice == "2":
            await find_breaking_point(BASE_URL)
            
        elif choice == "3":
            await monitor_system(BASE_URL, 300)
            
        elif choice == "4":
            print("\nRunning stress test with 1000 concurrent users...")
            test = QuickLoadTest(BASE_URL)
            start = time.time()
            await test.run_concurrent_users(1000)
            test.print_results(1000, time.time() - start)
            
        elif choice == "5":
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    # Install required packages:
    # pip install aiohttp
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest suite terminated by user")