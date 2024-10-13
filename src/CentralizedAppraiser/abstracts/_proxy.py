import asyncio
import json
import logging
import random
import aiohttp
import bs4
import requests

# Proxy
class Proxy:
    """
    This is a class that should be used when there is no proxy to use.
    """
    def __init__(self, url=None) -> None:
        self.url = url
        pass

    def __str__(self):
        return f"Proxy()"
    
    def get(self) -> str:
        return self.url



# Custom Rotating Proxy
class CustomRotating(Proxy):
    """Custom Rotating Proxy"""
    def __init__(self, **kwargs) -> None:
        self.allProxyList = kwargs.get("allProxyList", [])
        self.testEach = kwargs.get("testEach", True)
        self.lenTotalProxies = len(self.allProxyList)
        self.timeout = kwargs.get("timeout", 15)

    def __str__(self):
        return f"{self.__class__.__name__}()"
    
    @classmethod
    def create(cls, **kwargs):
        classObj = cls(**kwargs)
        asyncio.run(classObj.setup())
        return classObj
        
    async def setup(self):
        if self.testEach:
            tasks = []
            for proxy in self.allProxyList:
                tasks.append(asyncio.create_task(self._testOne(proxy)))

            results = await asyncio.gather(*tasks)
            self.proxies = [proxy for proxy in results if proxy]
        else:
            self.proxies = self.allProxyList

    def get(self) -> str:
        return random.choice(self.proxies)
    
    async def _testOne(self, proxy, url="https://reedgraff.com"):
        try:
            session_timeout = aiohttp.ClientTimeout(
                total=None,
                sock_connect=self.timeout,
                sock_read=self.timeout
            )

            connector = aiohttp.TCPConnector(ssl=False, force_close=True)
            async with aiohttp.ClientSession(connector=connector, trust_env=True, timeout=session_timeout) as session:
                async with session.get(
                    url,
                    proxy=f"http://{proxy}" if not proxy.startswith('http') else proxy,
                    timeout=self.timeout,
                    ssl=False
                ) as response:
                    return proxy
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            logging.error(f"Proxy {proxy} responded with an error: {e}")
            return None



# The SpeedX Proxy
class TheSpeedX(CustomRotating):
    """
    This is a wrapper class for this repo: https://github.com/TheSpeedX/PROXY-List
    """
    def __init__(self, testEach=True) -> None:
        super().__init__(testEach=testEach)

    async def setup(self):
        textOfProxies = requests.get("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt")
        self.allProxyList = [f"http://{x}" for x in textOfProxies.text.split("\n")[0:-1] if x]
        self.lenTotalProxies = len(self.allProxyList)
        await super().setup()



# Free Proxy List
class FreeProxyList(CustomRotating):
    """
    Wrapper for this db: https://free-proxy-list.net/
    """
    def __init__(self, testEach=True) -> None:
        super().__init__(testEach=testEach)

    async def setup(self):
        html = requests.get("https://free-proxy-list.net/")
        souped = bs4.BeautifulSoup(html.text, "html.parser")
        table = souped.find_all("table")[0]
        headers = [header.text for header in table.find_all("th")]

        proxies_list = []
        for row in table.find_all("tr")[1:]:
            columns = row.find_all("td")
            if columns:
                proxy_info = {headers[i]: columns[i].text for i in range(len(headers))}
                proxies_list.append(proxy_info)

        proxies_list = list(filter(lambda x: x['Https'] == "yes", proxies_list))
        self.lenTotalProxies = len(proxies_list)
        self.allProxyList = [f"http://{proxy['IP Address']}:{proxy['Port']}" for proxy in proxies_list]
        await super().setup()



if __name__ == "__main__":
    pl = TheSpeedX.create(testEach=True)
    print(len(pl.proxies), "/", pl.lenTotalProxies)
    
    pl = FreeProxyList.create(testEach=True)
    print(len(pl.proxies), "/", pl.lenTotalProxies)
    