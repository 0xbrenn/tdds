# load_test.py - Comprehensive Load Testing Suite
import asyncio
import aiohttp
import time
import random
import string
import json
from datetime import datetime
from typing import List, Dict, Tuple
import statistics
from collections import defaultdict
import csv
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('load_test_results.log'),
        logging.StreamHandler()
    ]
)

class LoadTestMetrics:
    def __init__(self):
        self.response_times = defaultdict(list)
        self.status_codes = defaultdict(int)
        self.errors = defaultdict(int)
        self.concurrent_users = []
        self.timestamps = []
        self.successful_requests = 0
        self.failed_requests = 0
        self.connection_errors = 0
        self.timeouts = 0
        
    def add_response(self, endpoint: str, response_time: float, status_code: int):
        self.response_times[endpoint].append(response_time)
        self.status_codes[status_code] += 1
        if status_code < 400:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            
    def add_error(self, endpoint: str, error_type: str):
        self.errors[f"{endpoint}:{error_type}"] += 1
        self.failed_requests += 1
        
        if "timeout" in error_type.lower():
            self.timeouts += 1
        elif "connection" in error_type.lower():
            self.connection_errors += 1
    
    def get_stats(self, endpoint: str) -> Dict:
        times = self.response_times.get(endpoint, [])
        if not times:
            return {}
            
        return {
            "count": len(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "p95": statistics.quantiles(times, n=20)[18] if len(times) > 20 else max(times),
            "p99": statistics.quantiles(times, n=100)[98] if len(times) > 100 else max(times),
            "min": min(times),
            "max": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def print_summary(self):
        print("\n" + "="*80)
        print("LOAD TEST RESULTS SUMMARY")
        print("="*80)
        
        print(f"\nTotal Requests: {self.successful_requests + self.failed_requests}")
        print(f"Successful: {self.successful_requests} ({self.successful_requests/(self.successful_requests + self.failed_requests)*100:.1f}%)")
        print(f"Failed: {self.failed_requests} ({self.failed_requests/(self.successful_requests + self.failed_requests)*100:.1f}%)")
        print(f"Connection Errors: {self.connection_errors}")
        print(f"Timeouts: {self.timeouts}")
        
        print("\nStatus Code Distribution:")
        for code, count in sorted(self.status_codes.items()):
            print(f"  {code}: {count}")
        
        print("\nResponse Time Statistics by Endpoint:")
        for endpoint in self.response_times:
            stats = self.get_stats(endpoint)
            if stats:
                print(f"\n  {endpoint}:")
                print(f"    Count: {stats['count']}")
                print(f"    Mean: {stats['mean']:.3f}s")
                print(f"    Median: {stats['median']:.3f}s")
                print(f"    95th percentile: {stats['p95']:.3f}s")
                print(f"    99th percentile: {stats['p99']:.3f}s")
                print(f"    Min: {stats['min']:.3f}s")
                print(f"    Max: {stats['max']:.3f}s")
        
        print("\nError Summary:")
        for error, count in self.errors.items():
            print(f"  {error}: {count}")

class BadgeSystemLoadTest:
    def __init__(self, base_url: str, num_users: int = 1000):
        self.base_url = base_url.rstrip('/')
        self.num_users = num_users
        self.metrics = LoadTestMetrics()
        self.test_emails = []
        self.session = None
        
    def generate_test_email(self) -> str:
        """Generate unique test email"""
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return f"loadtest_{random_str}@test.com"
    
    async def create_session(self):
        """Create aiohttp session with connection limits"""
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection limit
            limit_per_host=50,  # Per-host limit
            ttl_dns_cache=300
        )
        
        timeout = aiohttp.ClientTimeout(
            total=30,
            connect=5,
            sock_read=10
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, data: Dict = None) -> Tuple[int, float]:
        """Make HTTP request and measure response time"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with self.session.request(method, url, json=data) as response:
                await response.text()  # Ensure response is fully read
                response_time = time.time() - start_time
                
                self.metrics.add_response(endpoint, response_time, response.status)
                return response.status, response_time
                
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            self.metrics.add_error(endpoint, "Timeout")
            logging.error(f"Timeout on {endpoint} after {response_time:.2f}s")
            return 0, response_time
            
        except aiohttp.ClientError as e:
            response_time = time.time() - start_time
            self.metrics.add_error(endpoint, f"ClientError: {type(e).__name__}")
            logging.error(f"Client error on {endpoint}: {e}")
            return 0, response_time
            
        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.add_error(endpoint, f"Error: {type(e).__name__}")
            logging.error(f"Unexpected error on {endpoint}: {e}")
            return 0, response_time
    
    async def simulate_user_journey(self, user_id: int):
        """Simulate complete user journey"""
        email = self.generate_test_email()
        
        # Stage 1: Check if user exists
        await self.make_request("GET", f"/api/status/{email}")
        
        # Small delay to simulate user thinking
        await asyncio.sleep(random.uniform(0.5, 2))
        
        # Stage 2: Register with email
        await self.make_request("POST", "/auth/email/register-instant", {
            "email": email,
            "referral_code": "LOADTEST"
        })
        
        await asyncio.sleep(random.uniform(1, 3))
        
        # Stage 3: Send verification code
        await self.make_request("POST", "/auth/email/send-verification", {
            "email": email
        })
        
        await asyncio.sleep(random.uniform(2, 5))
        
        # Stage 4: Verify code
        await self.make_request("POST", "/auth/email/verify-code", {
            "email": email,
            "code": "123456"  # Dummy code
        })
        
        # Stage 5: Check status multiple times (simulating polling)
        for _ in range(3):
            await self.make_request("GET", f"/api/status/{email}")
            await asyncio.sleep(random.uniform(5, 10))
        
        # Stage 6: Access dashboard
        await self.make_request("GET", f"/api/dashboard/{email}")
        
        # Stage 7: Claim badge
        if random.random() > 0.5:  # 50% of users claim badge
            await self.make_request("POST", "/api/claim-badge-with-referral", {
                "email": email,
                "referral_code": "LOADTEST"
            })
        
        logging.info(f"User {user_id} completed journey")
    
    async def ramp_up_test(self, target_users: int, ramp_time: int):
        """Gradually increase load"""
        logging.info(f"Starting ramp-up test: {target_users} users over {ramp_time} seconds")
        
        users_per_second = target_users / ramp_time
        tasks = []
        
        for i in range(target_users):
            # Start user journey
            task = asyncio.create_task(self.simulate_user_journey(i))
            tasks.append(task)
            
            # Record concurrent users
            self.metrics.concurrent_users.append(len([t for t in tasks if not t.done()]))
            self.metrics.timestamps.append(time.time())
            
            # Wait before starting next user
            await asyncio.sleep(1 / users_per_second)
            
            # Log progress
            if i % 100 == 0:
                active = len([t for t in tasks if not t.done()])
                logging.info(f"Progress: {i}/{target_users} users started, {active} active")
        
        # Wait for all users to complete
        logging.info("Waiting for all users to complete...")
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def spike_test(self, spike_users: int):
        """Sudden spike in traffic"""
        logging.info(f"Starting spike test: {spike_users} users at once")
        
        tasks = []
        for i in range(spike_users):
            task = asyncio.create_task(self.simulate_user_journey(i))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def sustained_load_test(self, users: int, duration: int):
        """Maintain constant load for duration"""
        logging.info(f"Starting sustained load test: {users} users for {duration} seconds")
        
        end_time = time.time() + duration
        user_id = 0
        active_tasks = []
        
        while time.time() < end_time:
            # Remove completed tasks
            active_tasks = [t for t in active_tasks if not t.done()]
            
            # Add new users to maintain load
            while len(active_tasks) < users:
                task = asyncio.create_task(self.simulate_user_journey(user_id))
                active_tasks.append(task)
                user_id += 1
            
            # Record metrics
            self.metrics.concurrent_users.append(len(active_tasks))
            self.metrics.timestamps.append(time.time())
            
            await asyncio.sleep(1)
        
        # Wait for remaining tasks
        await asyncio.gather(*active_tasks, return_exceptions=True)
    
    def generate_report(self):
        """Generate detailed report with graphs"""
        # Print summary
        self.metrics.print_summary()
        
        # Save detailed results to CSV
        with open('load_test_detailed_results.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Endpoint', 'Response Time', 'Timestamp'])
            
            for endpoint, times in self.metrics.response_times.items():
                for i, time_val in enumerate(times):
                    writer.writerow([endpoint, time_val, i])
        
        # Generate graphs
        self.plot_response_times()
        self.plot_concurrent_users()
        self.plot_error_rate()
        
        logging.info("Report generated: load_test_results.log, graphs saved as PNG files")
    
    def plot_response_times(self):
        """Plot response time distribution"""
        plt.figure(figsize=(12, 8))
        
        for endpoint, times in self.metrics.response_times.items():
            if times:
                plt.hist(times, bins=50, alpha=0.5, label=endpoint)
        
        plt.xlabel('Response Time (seconds)')
        plt.ylabel('Frequency')
        plt.title('Response Time Distribution by Endpoint')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig('response_time_distribution.png')
        plt.close()
    
    def plot_concurrent_users(self):
        """Plot concurrent users over time"""
        if not self.metrics.timestamps:
            return
            
        plt.figure(figsize=(12, 6))
        
        start_time = self.metrics.timestamps[0]
        relative_times = [(t - start_time) for t in self.metrics.timestamps]
        
        plt.plot(relative_times, self.metrics.concurrent_users)
        plt.xlabel('Time (seconds)')
        plt.ylabel('Concurrent Users')
        plt.title('Concurrent Users Over Time')
        plt.grid(True, alpha=0.3)
        plt.savefig('concurrent_users.png')
        plt.close()
    
    def plot_error_rate(self):
        """Plot error rate over time"""
        plt.figure(figsize=(12, 6))
        
        # Calculate error rate in windows
        window_size = 10  # 10 second windows
        error_rates = []
        timestamps = []
        
        total_requests = self.successful_requests + self.failed_requests
        if total_requests > 0:
            error_rate = (self.failed_requests / total_requests) * 100
            
            plt.bar(['Successful', 'Failed'], 
                   [self.successful_requests, self.failed_requests],
                   color=['green', 'red'])
            plt.ylabel('Number of Requests')
            plt.title(f'Request Success/Failure Rate (Error Rate: {error_rate:.1f}%)')
            plt.savefig('error_rate.png')
        plt.close()

async def main():
    """Run comprehensive load test suite"""
    # Configuration
    BASE_URL = "https://api.badge.iopn.io"  # Change to your API URL
    
    # Test scenarios
    scenarios = [
        {
            "name": "Gradual Ramp-up",
            "type": "ramp",
            "users": 1000,
            "duration": 300  # 5 minutes
        },
        {
            "name": "Spike Test",
            "type": "spike",
            "users": 500
        },
        {
            "name": "Sustained Load",
            "type": "sustained",
            "users": 200,
            "duration": 600  # 10 minutes
        },
        {
            "name": "Stress Test",
            "type": "ramp",
            "users": 5000,
            "duration": 600  # 10 minutes
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{'='*80}")
        print(f"Starting scenario: {scenario['name']}")
        print(f"{'='*80}")
        
        # Create new test instance
        load_test = BadgeSystemLoadTest(BASE_URL, scenario.get('users', 1000))
        
        await load_test.create_session()
        
        try:
            if scenario['type'] == 'ramp':
                await load_test.ramp_up_test(scenario['users'], scenario['duration'])
            elif scenario['type'] == 'spike':
                await load_test.spike_test(scenario['users'])
            elif scenario['type'] == 'sustained':
                await load_test.sustained_load_test(scenario['users'], scenario['duration'])
            
            # Generate report for this scenario
            load_test.generate_report()
            
            # Save scenario-specific results
            with open(f"results_{scenario['name'].replace(' ', '_')}.json", 'w') as f:
                json.dump({
                    "scenario": scenario,
                    "metrics": {
                        "total_requests": load_test.metrics.successful_requests + load_test.metrics.failed_requests,
                        "successful_requests": load_test.metrics.successful_requests,
                        "failed_requests": load_test.metrics.failed_requests,
                        "error_rate": (load_test.metrics.failed_requests / (load_test.metrics.successful_requests + load_test.metrics.failed_requests) * 100) if (load_test.metrics.successful_requests + load_test.metrics.failed_requests) > 0 else 0,
                        "connection_errors": load_test.metrics.connection_errors,
                        "timeouts": load_test.metrics.timeouts,
                        "status_codes": dict(load_test.metrics.status_codes),
                        "endpoint_stats": {
                            endpoint: load_test.metrics.get_stats(endpoint)
                            for endpoint in load_test.metrics.response_times
                        }
                    }
                }, f, indent=2)
            
        finally:
            await load_test.close_session()
        
        # Cool down between scenarios
        print(f"\nScenario '{scenario['name']}' completed. Cooling down...")
        await asyncio.sleep(30)
    
    print("\n" + "="*80)
    print("ALL LOAD TESTS COMPLETED")
    print("="*80)
    print("\nCheck the following files for results:")
    print("- load_test_results.log")
    print("- load_test_detailed_results.csv")
    print("- response_time_distribution.png")
    print("- concurrent_users.png")
    print("- error_rate.png")
    print("- results_*.json (for each scenario)")

if __name__ == "__main__":
    asyncio.run(main())