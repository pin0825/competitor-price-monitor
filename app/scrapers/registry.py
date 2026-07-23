from app.scrapers.apple import AppleScraper
from app.scrapers.base import BaseScraper
from app.scrapers.exceptions import UnsupportedUrlError
from app.scrapers.john_lewis import JohnLewisScraper
from app.scrapers.laptops_direct import LaptopsDirectScraper

# 새로운 사이트를 지원할 때 scraper 객체를 이 목록에 추가한다.
SCRAPERS: tuple[BaseScraper, ...] = (
    AppleScraper(),
    JohnLewisScraper(),
    LaptopsDirectScraper(),
)


def get_scraper_for_url(url: str) -> BaseScraper:
    """URL을 담당하는 scraper를 찾아 반환한다."""
    for scraper in SCRAPERS:
        if scraper.supports(url):
            return scraper

    raise UnsupportedUrlError(f"No scraper is registered for URL: {url}")
