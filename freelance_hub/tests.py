from django.test import SimpleTestCase


class EmbeddingPolicyTests(SimpleTestCase):
    def test_portfolio_can_embed_public_workio_pages(self):
        response = self.client.get("/")

        self.assertNotIn("X-Frame-Options", response.headers)
        self.assertEqual(
            response.headers["Content-Security-Policy"],
            "frame-ancestors 'self' https://kittykio.com https://www.kittykio.com",
        )
