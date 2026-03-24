"""
Scraper de Goodreads "currently-reading" con parseo HTML.

Basado en el enfoque de selectores proporcionado por el usuario:
- Resuelve user_id de perfil publico
- Parsea layout de tabla / tarjetas / print
- Extrae porcentaje y paginas cuando estan disponibles
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests

try:
    from bs4 import BeautifulSoup, Tag  # type: ignore
    HAS_BS4 = True
except ImportError:  # pragma: no cover - fallback en entornos sin bs4 instalado
    BeautifulSoup = None  # type: ignore
    Tag = object  # type: ignore
    HAS_BS4 = False


logger = logging.getLogger(__name__)


@dataclass
class BookProgress:
    """Representa un libro en progreso de lectura."""
    title: str
    author: Optional[str]
    percent: Optional[int]
    pages_read: Optional[int]
    pages_total: Optional[int]
    book_url: Optional[str]
    shelf: str = "currently-reading"


class GoodreadsReadingScraper:
    """Scraper HTML para estanteria currently-reading de Goodreads."""

    BASE_URL = "https://www.goodreads.com"
    # Dominios permitidos para requests HTTP — protección SSRF.
    ALLOWED_HOSTS = {"www.goodreads.com", "goodreads.com"}

    def __init__(self, profile_url: Optional[str] = None, username: Optional[str] = None, timeout: int = 25):
        if not profile_url and not username:
            raise ValueError("Debes proveer profile_url o username de Goodreads")

        self.timeout = timeout
        self.username = (username or "").strip()
        self.profile_url = profile_url or self._build_profile_url_from_username(self.username)

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    def _validate_url(self, url: str) -> None:
        """Valida que la URL apunte exclusivamente a Goodreads (protección SSRF)."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host not in self.ALLOWED_HOSTS:
            raise ValueError(
                f"URL bloqueada por política SSRF: host '{host}' no está permitido. "
                f"Solo se permiten requests a {self.ALLOWED_HOSTS}"
            )
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Esquema '{parsed.scheme}' no permitido; solo http/https.")

    def _safe_get(self, url: str, allow_redirects: bool = True, **kwargs) -> requests.Response:
        """
        GET con validación SSRF en cada hop de redirect.

        La implementación anterior validaba la URL final DESPUÉS de que el
        request ya había viajado. Si Goodreads redirigía a un host interno,
        el request llegaba igual aunque se descartara la respuesta (SSRF).

        Ahora cada redirect se valida ANTES de seguirlo: si el destino no
        es goodreads.com, se lanza ValueError sin ejecutar el request.
        """
        self._validate_url(url)

        # Deshabilitar redirects automáticos para controlar cada hop.
        response = self.session.get(url, allow_redirects=False, **kwargs)

        hops = 0
        max_hops = 5  # Goodreads nunca necesita más de 2-3 redirects
        while response.is_redirect and allow_redirects and hops < max_hops:
            next_url = response.headers.get('Location', '')
            # Resolver URLs relativas contra la URL actual
            if next_url.startswith('/'):
                from urllib.parse import urljoin
                next_url = urljoin(url, next_url)
            self._validate_url(next_url)  # Valida ANTES de seguir el redirect
            url = next_url
            response = self.session.get(url, allow_redirects=False, **kwargs)
            hops += 1

        return response

    def _build_profile_url_from_username(self, username: str) -> str:
        candidate = username.strip()
        if candidate.startswith("http://") or candidate.startswith("https://"):
            return candidate

        compact = re.match(r'^(\d+)(?:[-_].*)?$', candidate)
        if compact:
            return f"{self.BASE_URL}/user/show/{compact.group(1)}"

        return f"{self.BASE_URL}/{candidate.lstrip('/')}"

    def _extract_int(self, value: str) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _extract_percent_any(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r'(\d{1,3})\s?%', text)
        if not match:
            return None
        value = int(match.group(1))
        return max(0, min(100, value))

    def _extract_pages_progress(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        if not text:
            return None, None

        match = re.search(r'(\d{1,5})\s+of\s+(\d{1,5})\s+pages', text, re.I)
        if match:
            return self._extract_int(match.group(1)), self._extract_int(match.group(2))

        match = re.search(r'(\d{1,5})\s+de\s+(\d{1,5})\s+p(?:a|á)ginas', text, re.I)
        if match:
            return self._extract_int(match.group(1)), self._extract_int(match.group(2))

        match = re.search(r'(?:\bp\.?\s*)?(\d{1,5})\s*/\s*(\d{1,5})\b', text, re.I)
        if match:
            return self._extract_int(match.group(1)), self._extract_int(match.group(2))

        return None, None

    def _canonical_book_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        if url.startswith('/'):
            url = f"{self.BASE_URL}{url}"
        return re.split(r"[?#]", url)[0]

    def _extract_style_percent(self, node: Tag) -> Optional[int]:
        elems = node.select(
            '.graphBar, .progressGraph, .progress, .meter, '
            '[class*="graph"], [class*="progress"], [class*="meter"]'
        )
        if not elems:
            elems = node.select('[style*="width"]')

        best: Optional[int] = None
        for el in elems:
            style = el.get("style") or ""
            match = re.search(r'width\s*:\s*(\d{1,3})\s*%', style, re.I)
            if not match:
                continue
            value = max(0, min(100, int(match.group(1))))
            if best is None or value > best:
                best = value
        return best

    def _norm_title(self, title: Optional[str]) -> Optional[str]:
        if not title:
            return None
        return re.sub(r'\s+', ' ', title).strip().lower()

    def _resolve_user_id(self) -> str:
        response = self._safe_get(self.profile_url, timeout=self.timeout, allow_redirects=True)
        final_url = response.url

        match = re.search(r'/user/show/(\d+)', final_url)
        if match:
            return match.group(1)

        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            match = re.search(r'/user/show/(\d+)', href)
            if match:
                return match.group(1)

        og = soup.find("meta", property="og:url")
        if og and og.get("content"):
            match = re.search(r'/user/show/(\d+)', og["content"])
            if match:
                return match.group(1)

        raise RuntimeError("No se pudo resolver el user_id de Goodreads")

    def _parse_table_layout(self, soup: BeautifulSoup) -> List[BookProgress]:
        results: List[BookProgress] = []
        table = soup.find("table", id="books") or soup.find("table", class_=re.compile(r"\btableList\b"))
        if not table:
            return results

        for tr in table.find_all("tr"):
            try:
                title = None
                book_url = None
                title_cell = (
                    tr.find("td", class_=re.compile(r"\bfield\s*title\b"))
                    or tr.find("td", class_=re.compile(r"\btitle\b"))
                )
                if title_cell:
                    anchor = title_cell.find("a", href=True)
                    if anchor:
                        title = anchor.get_text(strip=True)
                        book_url = self._canonical_book_url(anchor["href"])

                author = None
                author_cell = (
                    tr.find("td", class_=re.compile(r"\bfield\s*author\b"))
                    or tr.find("td", class_=re.compile(r"\bauthor\b"))
                )
                if author_cell:
                    anchor = author_cell.find("a")
                    author = (anchor.get_text(strip=True) if anchor else author_cell.get_text(strip=True)) or None

                percent = self._extract_style_percent(tr)
                row_text = tr.get_text(" ", strip=True)
                percent = percent or self._extract_percent_any(row_text)
                pages_read, pages_total = self._extract_pages_progress(row_text)

                if percent is None and pages_read is not None and pages_total and pages_total > 0:
                    percent = int(round((pages_read / pages_total) * 100))

                if not title and not book_url:
                    continue

                results.append(BookProgress(
                    title=title or "(sin titulo)",
                    author=author,
                    percent=percent,
                    pages_read=pages_read,
                    pages_total=pages_total,
                    book_url=book_url,
                ))
            except Exception:  # pragma: no cover - filas rotas en HTML externo
                continue
        return results

    def _parse_cards_layout(self, soup: BeautifulSoup) -> List[BookProgress]:
        results: List[BookProgress] = []
        cards = soup.select('div.bookalike.review, div.elementList, li.bookListItem, div.listWithDividers__item')
        for card in cards:
            try:
                anchor = card.find("a", href=True)
                title = anchor.get_text(strip=True) if anchor else None
                book_url = self._canonical_book_url(anchor["href"]) if anchor else None

                author_node = (
                    card.find("a", class_=re.compile("author", re.I))
                    or card.find("span", class_=re.compile("author", re.I))
                )
                author = author_node.get_text(strip=True) if author_node else None

                text = card.get_text(" ", strip=True)
                percent = self._extract_style_percent(card) or self._extract_percent_any(text)
                pages_read, pages_total = self._extract_pages_progress(text)

                if percent is None and pages_read is not None and pages_total and pages_total > 0:
                    percent = int(round((pages_read / pages_total) * 100))

                if not title and not book_url:
                    continue

                results.append(BookProgress(
                    title=title or "(sin titulo)",
                    author=author,
                    percent=percent,
                    pages_read=pages_read,
                    pages_total=pages_total,
                    book_url=book_url,
                ))
            except Exception:  # pragma: no cover - filas rotas en HTML externo
                continue
        return results

    def _parse_print_layout(self, html_text: str) -> List[BookProgress]:
        results: List[BookProgress] = []
        soup = BeautifulSoup(html_text, "html.parser")
        for tr in soup.select("tr"):
            try:
                anchor = tr.find("a", href=True)
                title = anchor.get_text(strip=True) if anchor else None
                book_url = self._canonical_book_url(anchor["href"]) if anchor else None

                row_text = tr.get_text(" ", strip=True)
                by_match = re.search(r'\bby\s+(.+)$', row_text, re.I)
                author = re.split(r'\s{2,}|\s\(|\s-\s', by_match.group(1))[0].strip() if by_match else None

                percent = self._extract_style_percent(tr) or self._extract_percent_any(row_text)
                pages_read, pages_total = self._extract_pages_progress(row_text)
                if percent is None and pages_read is not None and pages_total and pages_total > 0:
                    percent = int(round((pages_read / pages_total) * 100))

                if title or book_url:
                    results.append(BookProgress(
                        title=title or "(sin titulo)",
                        author=author,
                        percent=percent,
                        pages_read=pages_read,
                        pages_total=pages_total,
                        book_url=book_url,
                    ))
            except Exception:  # pragma: no cover
                continue
        return results

    def _augment_from_profile_widget(self) -> Dict[str, int]:
        mapping: Dict[str, int] = {}
        single_pct: List[int] = []

        try:
            response = self._safe_get(self.profile_url, timeout=self.timeout)
            if response.status_code != 200:
                return mapping
            soup = BeautifulSoup(response.text, "html.parser")
            root = soup.find(id="currentlyReadingReviews") or soup

            bars = root.select("div.graphBar, .progressGraph .graphBar, [style*='width']")
            for bar in bars:
                style = bar.get("style") or ""
                match = re.search(r'width\s*:\s*(\d{1,3})\s*%', style, re.I)
                if not match:
                    continue
                pct = max(0, min(100, int(match.group(1))))

                block: Optional[Tag] = bar
                for _ in range(4):
                    if block and block.parent:
                        block = block.parent
                    else:
                        break

                anchor = block.find("a", href=re.compile(r"/book/|/work/")) if block else None
                if not anchor:
                    anchor = root.find("a", href=re.compile(r"/book/|/work/"))

                title = anchor.get_text(strip=True) if anchor else None
                url = self._canonical_book_url(anchor["href"]) if anchor and anchor.has_attr("href") else None

                if url:
                    mapping[url] = pct
                if title:
                    mapping[self._norm_title(title)] = pct
                if not url and not title:
                    single_pct.append(pct)

            if not mapping and single_pct:
                mapping["__single_percent__"] = max(single_pct)

        except Exception as exc:  # pragma: no cover
            logger.warning("No se pudo aumentar data desde widget de perfil: %s", exc)

        return mapping

    def _parse_profile_currently_reading_widget(self) -> List[BookProgress]:
        """
        Fallback robusto: parsea currently-reading desde el perfil publico.

        Goodreads suele bloquear /review/list/* para usuarios no logueados
        (redirecciona a sign-in), pero mantiene visible este widget en perfil.
        """
        results: List[BookProgress] = []
        dedupe_keys = set()

        response = self._safe_get(self.profile_url, timeout=self.timeout, allow_redirects=True)
        if response.status_code != 200:
            return results

        soup = BeautifulSoup(response.text, "html.parser")
        root = soup.find(id="currentlyReadingReviews")
        if not root:
            return results

        entries = root.select("div.Updates")
        if not entries:
            entries = [root]

        for entry in entries:
            try:
                book_anchor = (
                    entry.select_one("a.bookTitle[href]") or
                    entry.find("a", href=re.compile(r"/book/|/work/"))
                )
                if not book_anchor:
                    continue

                title = book_anchor.get_text(" ", strip=True) or "(sin titulo)"
                book_url = self._canonical_book_url(book_anchor.get("href"))

                author_anchor = (
                    entry.select_one("a.authorName[href]") or
                    entry.find("a", href=re.compile(r"/author/show/"))
                )
                author = author_anchor.get_text(" ", strip=True) if author_anchor else None

                entry_text = entry.get_text(" ", strip=True)
                percent = self._extract_percent_any(entry_text) or self._extract_style_percent(entry)
                pages_read, pages_total = self._extract_pages_progress(entry_text)
                if percent is None and pages_read is not None and pages_total and pages_total > 0:
                    percent = int(round((pages_read / pages_total) * 100))

                dedupe_key = book_url or self._norm_title(title)
                if dedupe_key in dedupe_keys:
                    continue
                dedupe_keys.add(dedupe_key)

                results.append(BookProgress(
                    title=title,
                    author=author,
                    percent=percent,
                    pages_read=pages_read,
                    pages_total=pages_total,
                    book_url=book_url,
                ))
            except Exception:  # pragma: no cover - HTML externo impredecible
                continue

        return results

    def fetch_data(self) -> List[BookProgress]:
        if not HAS_BS4:
            logger.warning("beautifulsoup4 no instalado. Goodreads HTML scraping desactivado.")
            return []

        user_id = self._resolve_user_id()
        shelf_url = f"{self.BASE_URL}/review/list/{user_id}?shelf=currently-reading&per_page=100"
        response = self._safe_get(shelf_url, timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError(f"Goodreads devolvio {response.status_code} para {shelf_url}")

        results: List[BookProgress] = []

        # Goodreads suele redirigir review/list a sign-in para sesiones anonimas.
        redirected_to_sign_in = "/user/sign_in" in (response.url or "")
        if not redirected_to_sign_in:
            soup = BeautifulSoup(response.text, "html.parser")
            results = self._parse_table_layout(soup)
            if not results:
                results = self._parse_cards_layout(soup)

        if not results and not redirected_to_sign_in:
            print_url = f"{self.BASE_URL}/review/list/{user_id}?shelf=currently-reading&per_page=100&print=true"
            print_response = self._safe_get(print_url, timeout=self.timeout)
            if print_response.status_code == 200 and "/user/sign_in" not in (print_response.url or ""):
                results = self._parse_print_layout(print_response.text)

        # Fallback final: widget currently-reading en perfil publico.
        if not results:
            results = self._parse_profile_currently_reading_widget()

        if results and any(item.percent is None for item in results):
            pct_map = self._augment_from_profile_widget()
            single = pct_map.get("__single_percent__")
            for item in results:
                if item.percent is not None:
                    continue
                if item.book_url and item.book_url in pct_map:
                    item.percent = pct_map[item.book_url]
                    continue
                normalized_title = self._norm_title(item.title)
                if normalized_title and normalized_title in pct_map:
                    item.percent = pct_map[normalized_title]
                    continue
                if single is not None and len(results) == 1:
                    item.percent = single

        return results
