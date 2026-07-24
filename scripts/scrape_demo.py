import asyncio

import httpx

from app.scrapers.registry import get_scraper_for_url

URLS = (
    "https://www.apple.com/uk/shop/buy-iphone/iphone-17/"
    "6.3-inch-display-256gb-black",
    "https://www.johnlewis.com/apple-iphone-17-ios-6-3-inch-5g-sim-free-256gb/"
    "black/p114322975",
    "https://www.laptopsdirect.co.uk/apple-iphone-17-black-6.3-256gb-5g-unlocked-"
    "sim-free-smartphone-mg6j4qn-a/version.asp",
)


async def main() -> None:
    """세 판매처를 동시에 수집하고 공통 결과 형태를 출력한다."""
    headers = {
        "User-Agent": (
            "CompetitorPriceMonitor/0.1 "
            "(portfolio project; low-frequency requests)"
        )
    }

    async with httpx.AsyncClient(
        headers=headers,
        timeout=20,
        follow_redirects=True,
    ) as client:
        tasks = [
            get_scraper_for_url(url).scrape(url, client)
            for url in URLS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            print(f"FAILED: {type(result).__name__}: {result}")
            continue

        print(
            f"{result.retailer}: "
            f"{result.title} -> {result.currency} {result.price}"
        )


if __name__ == "__main__":
    asyncio.run(main())
