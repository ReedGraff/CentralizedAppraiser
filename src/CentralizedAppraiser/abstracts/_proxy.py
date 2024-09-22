import asyncio
import json
import logging
import random
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
class TheSpeedX(Proxy):
    """
    This is a class to manage: https://github.com/TheSpeedX/SOCKS-List
    """
    def __init__(self, testEach=True) -> None:
        self.timeout = 15
        self.testEach = testEach

    def create(**kwargs):
        classObj = TheSpeedX(**kwargs)
        asyncio.run(classObj.setup())
        return classObj

    async def setup(self):
        import bs4
        import requests

        textOfProxies = requests.get("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt")
        proxies_list = textOfProxies.text.split("\n")[0:-1]
        self.totalProxies = len(proxies_list)

        if self.testEach:
            tasks = []
            for index, proxy in enumerate(proxies_list):
                tasks.append(asyncio.create_task(self.testOne(proxy)))

            results = await asyncio.gather(*tasks)
            self.proxies = [proxy for proxy in results if proxy]

    def getProxyIP(self) -> str:
        return random.choice(self.proxies)
    
    async def testOne(self, proxy, url="https://reedgraff.com"):
        try:
            session_timeout = aiohttp.ClientTimeout(
                total=None,
                sock_connect=self.timeout,
                sock_read=self.timeout
            )

            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                async with session.get(
                    url,
                    proxy=f"http://{proxy}",
                    timeout=self.timeout,
                    ssl=False
                ) as response:
                    # await response.text()
                    return proxy
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            logging.error(f"Proxy {proxy} responded with an error: {e}")
            return None



# FreeProxyList
class FreeProxyList(Proxy):
    def __init__(self, testEach=True) -> None:
        self.timeout = 15
        self.testEach = testEach

    def create(**kwargs):
        classObj = FreeProxyList(**kwargs)
        asyncio.run(classObj.setup())
        return classObj

    async def setup(self):
        import bs4
        import requests

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

        # Filter proxies
        proxies_list = list(filter(lambda x: x['Https'] == "yes", proxies_list))
        self.totalProxies = len(proxies_list)
        # proxies_list = list(filter(lambda x: x['Code'] in ["US", "CA", "GB", "AU", "NZ"], proxies_list))

        if self.testEach:
            tasks = []
            for index, proxy in enumerate(proxies_list):
                proxy = f"{proxy['IP Address']}:{proxy['Port']}"
                tasks.append(asyncio.create_task(self.testOne(proxy)))

            results = await asyncio.gather(*tasks)
            self.proxies = [proxy for proxy in results if proxy]

    def getProxyIP(self) -> str:
        return random.choice(self.proxies)
    
    async def testOne(self, proxy, url="https://reedgraff.com"):
        try:
            session_timeout = aiohttp.ClientTimeout(
                total=None,
                sock_connect=self.timeout,
                sock_read=self.timeout
            )

            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'no-cache',
                # 'cookie': '_ga=GA1.1.1469782983.1725583612; ASP.NET_SessionId=csisdsftraxkbomnb2nr21s5; BIGipServer~AUTO-VISION~visionlive~www.delraybeachfl.gov_443=!npEjW8az9AV4LZtedm1Xf9THDYxJhFCC29mRd0waO7uZ4fLjXvKYI4rmpwuXleDS/53mLg1AZRlZscQ=; __RequestVerificationToken=v_1Rcu_zDZMM84IpYRwcMTdcCC80DUgiaK4_uKGrjBnw916u9B9OyYK5Zxo3XZqvpo-7S81ogMUIZ4bxmYw9_qetRGKSUC1XhppmVpIUKpQ1; TS01af151e=0106cf681bfd15a527dd34d0b5117d4823d5706dfc5a132d71c4e4313465d55e01bd0fc695bf46cd2465992c6321ab8343134cfcbbe03e8c7cbd719720016e6c3c22dc8264655f961350031b9144a219130ca7f19c3fec29d46cc613956fdacb0afda4b7c9; _ga_ZJVMFY126H=GS1.1.1726452726.4.0.1726452726.60.0.0; TS3b44c919027=08b9428c85ab2000939699dff48ee16c2a82ba70b7a0533cdb0f575ac82d26c2a0e4ceac504b1b06084efa3c3c113000410c662a484c9088632feed2facb3fa2d52773dd1abe2025fb516a861e3bfd5053f4ae848d7ecedc2ddcf22255c02aa2',
                'pragma': 'no-cache',
                'priority': 'u=0, i',
                'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            }

            connector = aiohttp.TCPConnector(ssl=False, force_close=True)
            async with aiohttp.ClientSession(connector=connector, trust_env=True, timeout=session_timeout) as session:
                async with session.get(
                    url,
                    proxy=proxy,
                    timeout=self.timeout,
                    headers=headers,
                    ssl=False
                ) as response:
                    # await response.text()
                    # print(await response.text())
                    # print(f"Proxy {proxy} responded with a status code of {response.status}")
                    return proxy
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            logging.error(f"Proxy {proxy} responded with an error: {e}")
            return None



if __name__ == "__main__":
    pl = FreeProxyList.create(testEach=True)
    print(len(pl.proxies), "/", pl.totalProxies)

    pl = TheSpeedX.create(testEach=True)
    print(len(pl.proxies), "/", pl.totalProxies)