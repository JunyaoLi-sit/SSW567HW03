import unittest
from unittest.mock import Mock, patch
from github_api import GitHubClient, UserNotFoundError, RateLimitError


def make_response(status_code=200, json_data=None, headers=None, ok=True):
    r = Mock()
    r.status_code = status_code
    r.ok = ok
    r.json = Mock(return_value=json_data if json_data is not None else [])
    r.headers = headers or {}
    return r


class TestGitHubClientMocking(unittest.TestCase):

    @patch("requests.Session.get")
    def test_get_user_repos_single_page(self, mock_get):
        mock_get.return_value = make_response(
            200,
            json_data=[{"name": "A"}, {"name": "B"}],
            headers={},
            ok=True
        )

        client = GitHubClient()  # real client, but network is mocked
        repos = client.get_user_repos("someone")

        self.assertEqual(repos, ["A", "B"])
        self.assertEqual(mock_get.call_count, 1)

    @patch("requests.Session.get")
    def test_count_repo_commits_multiple_pages(self, mock_get):
        mock_get.side_effect = [
            make_response(
                200,
                json_data=[{"sha": "1"}, {"sha": "2"}],
                headers={"Link": '<https://api.github.com/repositories/1/commits?page=2>; rel="next"'},
                ok=True,
            ),
            make_response(
                200,
                json_data=[{"sha": "3"}],
                headers={},
                ok=True,
            ),
        ]

        client = GitHubClient()
        count = client.count_repo_commits("u", "r")

        self.assertEqual(count, 3)
        self.assertEqual(mock_get.call_count, 2)

    @patch("requests.Session.get")
    def test_user_not_found(self, mock_get):
        mock_get.return_value = make_response(404, json_data={"message": "Not Found"}, ok=False)

        client = GitHubClient()
        with self.assertRaises(UserNotFoundError):
            client.get_user_repos("nope")

    @patch("requests.Session.get")
    def test_rate_limit(self, mock_get):
        mock_get.return_value = make_response(
            403,
            json_data={"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Remaining": "0"},
            ok=False,
        )

        client = GitHubClient()
        with self.assertRaises(RateLimitError):
            client.get_user_repos("someone")

    @patch("requests.Session.get")
    def test_repo_commit_counts_integration(self, mock_get):
        mock_get.side_effect = [
            make_response(200, json_data=[{"name": "A"}, {"name": "B"}], headers={}, ok=True),
            make_response(200, json_data=[{"sha": "1"}], headers={}, ok=True),
            make_response(200, json_data=[{"sha": "1"}, {"sha": "2"}], headers={}, ok=True),
        ]

        client = GitHubClient()
        results = client.repo_commit_counts("someone")

        self.assertEqual([(r.repo_name, r.commit_count) for r in results], [("A", 1), ("B", 2)])


if __name__ == "__main__":
    unittest.main()
