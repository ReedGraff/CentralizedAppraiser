import asyncio
import aiohttp
import random
import time
import matplotlib.pyplot as plt

# Try to use uvloop if available
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

class AppraiserInfoFetcher:
    def __init__(self, max_concurrency=50):
        self.semaphore = asyncio.Semaphore(max_concurrency)

    def create_connector(self):
        raise NotImplementedError
        # replace with u p proxy for your proxy server...
        proxy_auth = "{}:{}@{}".format(username, password, proxy)
        return "http://{}".format(proxy_auth)

    async def fetch_appraiser_info(self, folio: str, max_tries=3, backoff_factor=0.5):
        # url = "https://api.ipify.org"
        url = "https://www.miamidade.gov/Apps/PA/PApublicServiceProxy/PaServicesProxy.ashx"
        querystring = {
            "Operation": "GetPropertySearchByFolio",
            "clientAppName": "PropertySearch",
            "folioNumber": folio.replace("-", "")
        }

        async with self.semaphore:
            for attempt in range(max_tries):
                proxy = self.create_connector()
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                        async with session.get(url, params=querystring, proxy=proxy) as response:
                            if response.status == 200:
                                return {"data": await response.text()}, attempt + 1
                            if attempt == max_tries - 1:
                                response.raise_for_status()
                except Exception as e:
                    print(f"Exception on attempt {attempt + 1}: {e}")
                    if attempt < max_tries - 1:
                        print(f"Retrying in {backoff_factor * (2 ** attempt):.4f} seconds")
                        await asyncio.sleep(backoff_factor * (2 ** attempt))
                    else:
                        print(f"Failed to fetch appraiser info after {max_tries} attempts")
                        return None, max_tries

    async def run_multiple(self, folio, num_runs):
        start_time = time.time()
        tasks = [self.fetch_appraiser_info(folio) for _ in range(num_runs)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        total_time = total_time
        total_attempts = sum(result[1] for result in results)
        successful_runs = sum(1 for result in results if result[0])
        
        avg_time = total_time / successful_runs if successful_runs else 0
        avg_attempts = total_attempts / num_runs
        
        print(f"Average time per successful run: {avg_time:.4f} seconds")
        print(f"Average number of attempts per run: {avg_attempts:.2f}")
        print(f"Successful runs: {successful_runs}/{num_runs}")
        print(f"IPs = {[result[0]['data'] for result in results if result[0]]}")
        
        return avg_attempts

async def main(simulated_requests, grid_size, concurrent_requests):
    folio = "01-3112-014-0300"
    fetcher = AppraiserInfoFetcher(max_concurrency=concurrent_requests)
    
    tasks = [fetcher.run_multiple(folio, simulated_requests) for _ in range(grid_size)]
    avg_attempts_list = await asyncio.gather(*tasks)
    return sum(avg_attempts_list) / len(avg_attempts_list)

if __name__ == "__main__":
    simulated_requests = 800
    grid_size = 3
    concurrent_requests_list = [200, 500, 1000] # 500 renders the best results
    execution_times = []
    avg_attempts_list = []

    for concurrent_requests in concurrent_requests_list:
        start_time = time.time()
        avg_attempts = asyncio.run(main(simulated_requests, grid_size, concurrent_requests=concurrent_requests))
        end_time = time.time()
        total_time = end_time - start_time
        execution_times.append(total_time)
        avg_attempts_list.append(avg_attempts)
        print(f"Concurrent requests: {concurrent_requests}, Total time: {total_time:.4f} seconds, Avg attempts: {avg_attempts:.2f}")
    
    # Plotting the graph
    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax1.set_xlabel('Concurrent Requests')
    ax1.set_ylabel('Total Time (seconds)', color='tab:blue')
    ax1.plot(concurrent_requests_list, execution_times, marker='o', color='tab:blue', label='Total Time')
    ax1.tick_params(axis='y', labelcolor='tab:blue')

    ax2 = ax1.twinx()
    ax2.set_ylabel('Average Attempts', color='tab:orange')
    ax2.plot(concurrent_requests_list, avg_attempts_list, marker='s', color='tab:orange', label='Average Attempts')
    ax2.tick_params(axis='y', labelcolor='tab:orange')

    plt.title('Performance and Attempts vs Concurrent Requests')
    fig.tight_layout()
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.grid(True)
    plt.show()
    fig.savefig(f'grid_size{grid_size}___simulated_requests{simulated_requests}.png', dpi=fig.dpi)