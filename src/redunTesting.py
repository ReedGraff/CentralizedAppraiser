import asyncio
import json
import timeit
import aiohttp
import aiohttp.client

async def fetch(url, tries=3):
    url = (
        'https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN24/MapServer/16/query'
        '?f=json'
        '&geometry={"xmin":913371.185151686,"ymin":638379.2604835231,"xmax":915429.5184850192,"ymax":640104.2604835231}'
        '&outFields=*'
        '&spatialRel=esriSpatialRelIntersects'
        '&where=1=1'
        '&geometryType=esriGeometryEnvelope'
        '&resultRecordCount=1000'
        '&resultOffset=0'
    )
    proxy = "http://7377b58badb4290a90e33e08d7098a5595d3195c@api.zenrows.com:8001"
    async with aiohttp.ClientSession() as s:
        s:aiohttp.client.ClientSession = s
        async with s.get(url, proxy=proxy, ssl=False, timeout=60) as r:
            if r.status != 200:
                print(f"Failed to fetch {url}, status code {r.status}, tries left {tries}")
                if tries > 0:
                    return await fetch(url, tries-1)
                else:
                    r.raise_for_status()
            else:
                # response_text = await r.text()
                # print(f"Response text: {response_text}")
                return json.loads(await r.text())

async def fetch_all(urls):
    tasks = []
    for url in urls:
        task = asyncio.create_task(fetch(url))
        tasks.append(task)
    res = await asyncio.gather(*tasks)
    print(f"res: {res}")
    return res

async def main():
    urls = range(1, 21)
    htmls = await fetch_all(urls)
    # print(htmls)
    return htmls

if __name__ == '__main__':
    val = asyncio.run(main())
    print(len(val))
    # print(timeit.timeit(lambda: asyncio.run(main()), number=1))