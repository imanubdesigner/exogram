from unittest.mock import patch

from django.test import SimpleTestCase

from books.goodreads_reading_scraper import GoodreadsReadingScraper


class _FakeResponse:
    def __init__(self, status_code: int, text: str, url: str):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.is_redirect = False


class GoodreadsReadingScraperTest(SimpleTestCase):
    @patch.object(GoodreadsReadingScraper, "_resolve_user_id", return_value="12345")
    def test_fetch_data_falls_back_to_profile_widget_when_shelf_requires_login(self, _mock_user_id):
        scraper = GoodreadsReadingScraper(username="matzalazar")

        shelf_sign_in = _FakeResponse(
            status_code=200,
            text="<html><head><title>Sign in</title></head><body>Sign in</body></html>",
            url="https://www.goodreads.com/user/sign_in?returnurl=%2Freview%2Flist%2F12345"
        )
        profile_widget = _FakeResponse(
            status_code=200,
            url="https://www.goodreads.com/user/show/12345-reader",
            text="""
                <html>
                  <body>
                    <div id="currentlyReadingReviews">
                      <div class="Updates">
                        <a class="bookTitle" href="/book/show/42-example-book">Example Book</a>
                        <a class="authorName" href="/author/show/7-example-author">Example Author</a>
                        <div>progress: (8%)</div>
                      </div>
                    </div>
                  </body>
                </html>
            """,
        )

        with patch.object(scraper.session, "get", side_effect=[shelf_sign_in, profile_widget]):
            results = scraper.fetch_data()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Example Book")
        self.assertEqual(results[0].author, "Example Author")
        self.assertEqual(results[0].percent, 8)
        self.assertEqual(results[0].book_url, "https://www.goodreads.com/book/show/42-example-book")
