class ScraperError(Exception):
    """모든 scraper 오류의 공통 부모 예외다."""


class UnsupportedUrlError(ScraperError):
    """scraper가 담당하지 않는 도메인의 URL을 받았을 때 발생한다."""


class FetchError(ScraperError):
    """페이지 요청이 timeout이나 HTTP 오류로 실패했을 때 발생한다."""


class ParseError(ScraperError):
    """HTML에서 필요한 상품명이나 가격을 찾지 못했을 때 발생한다."""
