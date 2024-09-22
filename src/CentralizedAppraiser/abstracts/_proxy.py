import asyncio
import random
import requests
import aiohttp

# Proxy
class Proxy:
    """
    This is an abstract class that should be inhereted by any other clients used for this library.
    """
    def __init__(self) -> None:
        raise NotImplementedError

    def __str__(self):
        return f"Proxy()"
    
    def getProxyIP(self) -> str:
        raise NotImplementedError



# TheSpeedX/SOCKS-List
class TheSpeedXProxy(Proxy):
    """
    This is a class to manage: https://github.com/TheSpeedX/SOCKS-List
    """
    def __init__(self, testEach=False):
        self.testEach = testEach
        self.proxies = []
        self.session = None

    @classmethod
    async def create(cls, testEach=False):
        self = cls(testEach)
        await self.initialize()
        return self

    async def initialize(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt") as response:
                data = await response.text()
        data = data.split("\n")
        data = ["http://7377b58badb4290a90e33e08d7098a5595d3195c:premium_proxy=true&proxy_country=us@api.zenrows.com:8001", "http://40.76.69.94:8080"]

        if self.testEach:
            async with aiohttp.ClientSession() as session:
                self.session = session
                tasks = []
                for proxy in data:
                    task = asyncio.create_task(self.__testEach(proxy))
                    tasks.append(task)
                results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter proxies that returned True
            self.proxies = [proxy for proxy, result in zip(data, results) if result is True]
        else:
            self.proxies = data

    def __str__(self):
        return f"TheSpeedXProxy()"
    
    def getProxyIP(self) -> str:
        return random.choice(self.proxies)
    
    async def __testEach(self, proxy, testURL="https://reedgraff.com") -> bool:
        try:
            async with self.session.get(testURL, proxy=proxy, ssl=False, timeout=5) as response:
                return response.status == 200
        except (aiohttp.ClientConnectorError, aiohttp.ServerTimeoutError, asyncio.TimeoutError, aiohttp.ClientError):
            return False
        except Exception as e:
            print(f"Unexpected error testing proxy {proxy}: {str(e)}")
            return False

    async def close(self):
        if self.session:
            await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()