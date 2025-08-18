import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Optional
import structlog
import hashlib
from urllib.parse import urljoin
from asyncio_throttle import Throttler

from ..domain.entities import WoWArticle
from ..domain.repositories import WebScrapingRepository

logger = structlog.get_logger()


class BlizzSpiritScrapingRepository(WebScrapingRepository):
    def __init__(
        self,
        base_url: str = "https://www.blizzspirit.com",
        requests_per_second: float = 1.0,
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.throttler = Throttler(rate_limit=requests_per_second, period=1.0)
        
        # Headers to appear more like a regular browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

    async def fetch_article_urls(self, base_url: str, max_articles: int) -> List[str]:
        logger.info("Fetching article URLs from Blizzspirit homepage", max_articles=max_articles)
        
        try:
            async with self.throttler:
                async with aiohttp.ClientSession(
                    timeout=self.timeout,
                    headers=self.headers
                ) as session:
                    async with session.get(self.base_url) as response:
                        if response.status != 200:
                            logger.error("Failed to fetch homepage", status=response.status)
                            return []
                        
                        html_content = await response.text()
            
            # Parse HTML content
            soup = BeautifulSoup(html_content, 'html.parser')
            article_urls = []
            
            # Look for article links in the slider/carousel based on observed structure
            selectors = [
                '.n2-ss-2 a',  # Smart Slider links
                'a[href*="/warcraft/"]',  # WoW-specific articles
                'a[href*="/news/"]',  # News articles
                'a[href*="/guide/"]',  # Guide articles
                'article a',  # General article links
                '.post-title a',  # Post titles
                'h1 a, h2 a, h3 a'  # Headlines
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                logger.debug(f"Found {len(links)} links with selector: {selector}")
                
                for link in links:
                    href = link.get('href')
                    if href and href.startswith('http'):
                        # Full URL
                        full_url = href
                    elif href:
                        # Relative URL
                        full_url = urljoin(self.base_url, href)
                    else:
                        continue
                    
                    # Filter for likely article URLs and avoid duplicates
                    if self._is_article_url(full_url) and full_url not in article_urls:
                        article_urls.append(full_url)
                        logger.debug(f"Added article URL: {full_url}")
                        
                        if len(article_urls) >= max_articles:
                            break
                
                if len(article_urls) >= max_articles:
                    break
            
            logger.info("Found article URLs", count=len(article_urls))
            return article_urls[:max_articles]
            
        except Exception as e:
            logger.error("Failed to fetch article URLs", error=str(e), exc_info=True)
            return []

    async def extract_article_content(self, url: str) -> Optional[WoWArticle]:
        logger.debug("Extracting article content", url=url)
        
        try:
            async with self.throttler:
                async with aiohttp.ClientSession(
                    timeout=self.timeout,
                    headers=self.headers
                ) as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.warning("Failed to fetch article", url=url, status=response.status)
                            return None
                        
                        html_content = await response.text()
            
            # Parse article content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup)
            if not title:
                logger.warning("Could not extract title", url=url)
                return None
            
            # Extract content
            content = self._extract_content(soup)
            if not content or len(content.strip()) < 50:  # Minimum content length
                logger.warning("Could not extract sufficient content", url=url, content_length=len(content))
                return None
            
            # Extract metadata
            published_date = self._extract_published_date(soup) or datetime.now()
            author = self._extract_author(soup)
            category = "World of Warcraft"  # Default category for Blizzspirit
            
            # Generate article ID from URL
            article_id = hashlib.md5(url.encode()).hexdigest()
            
            # Create summary (first 200 characters)
            summary = content[:200] + "..." if len(content) > 200 else content
            
            article = WoWArticle(
                id=article_id,
                title=title,
                content=content,
                summary=summary,
                url=url,
                published_date=published_date,
                author=author,
                category=category,
                tags=["World of Warcraft", "Blizzspirit"]
            )
            
            logger.debug(
                "Successfully extracted article",
                url=url,
                title=title[:50] + "..." if len(title) > 50 else title,
                content_length=len(content)
            )
            
            return article
            
        except Exception as e:
            logger.error("Failed to extract article content", url=url, error=str(e), exc_info=True)
            return None

    def _is_article_url(self, url: str) -> bool:
        """Check if URL is likely an article URL for Blizzspirit"""
        if not url.startswith('https://www.blizzspirit.com'):
            return False
        
        # Skip common non-article paths
        skip_patterns = [
            '/wp-admin/', '/wp-content/', '/wp-json/',
            '.jpg', '.png', '.gif', '.pdf', '.css', '.js',
            '/tag/', '/category/', '/author/', '/search/',
            '#', 'javascript:', 'mailto:'
        ]
        
        url_lower = url.lower()
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
        
        # Accept article patterns
        article_patterns = [
            '/warcraft/',
            '/diablo/',
            '/hearthstone/',
            '/overwatch/',
            '/news/',
            '/guide/'
        ]
        
        for pattern in article_patterns:
            if pattern in url_lower:
                return True
        
        # If it has a reasonable path (not just homepage)
        path = url.replace('https://www.blizzspirit.com', '').strip('/')
        return len(path) > 0 and '/' in path

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article title"""
        title_selectors = [
            'h1.entry-title',
            'h1.post-title', 
            'h1.wp-block-post-title',
            '.article-title h1',
            'article h1',
            'h1',
            'title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                # Clean up common title suffixes
                title = title.replace(' - Blizzspirit', '').replace(' | Blizzspirit', '')
                if title and len(title) > 5:
                    return title
        
        return None

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content"""
        content_selectors = [
            '.entry-content',
            '.post-content',
            '.wp-block-post-content',
            'article .content',
            '.single-content',
            'main article'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                # Remove unwanted elements
                for unwanted in element(['script', 'style', 'nav', 'aside', 'footer', 'header', '.advertisement', '.ads']):
                    unwanted.decompose()
                
                # Get text with proper spacing
                text = element.get_text(separator=' ', strip=True)
                if text and len(text) > 100:
                    return text
        
        return ""

    def _extract_published_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract article published date"""
        date_selectors = [
            'time[datetime]',
            '.entry-date',
            '.post-date',
            '.published',
            'meta[property="article:published_time"]'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                # Try datetime attribute first
                datetime_attr = element.get('datetime') or element.get('content')
                if datetime_attr:
                    try:
                        return datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                    except:
                        pass
                
                # Try parsing text content
                date_text = element.get_text(strip=True)
                if date_text:
                    try:
                        # Simple French date parsing
                        import re
                        # Look for patterns like "12 janvier 2024"
                        date_match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_text)
                        if date_match:
                            day, month_fr, year = date_match.groups()
                            month_map = {
                                'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
                                'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
                                'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
                            }
                            if month_fr in month_map:
                                return datetime(int(year), month_map[month_fr], int(day))
                    except:
                        pass
        
        return None

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article author"""
        author_selectors = [
            '.author-name',
            '.entry-author',
            '.post-author',
            '.byline',
            'meta[name="author"]'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get('content') or element.get_text(strip=True)
                if author and len(author) > 1 and len(author) < 50:
                    return author
        
        return "Blizzspirit"  # Default author