import unittest
from unittest.mock import Mock
from github_api import GitHubClient, UserNotFoundError, RateLimitError


def make_response(status_code=200, json_data=None, headers=None, ok=True):
    r = Mock()
    r.status_code = status_code
    r.ok = ok
    r.json = Mock(return_value=json_data if json_data is not None else [])
    r.headers = headers or {}
    return r


class TestGitHubClient(unittest.TestCase):
    def test_get_user_repos_single_page(self):
        session = Mock()
        session.get.return_value = make_response(
            200,
            json_data=[{"name": "A"}, {"name": "B"}],
            headers={},  # no Link => single page
            ok=True
        )
        client = GitHubClient(session=session)

        repos = client.get_user_repos("someone")
        self.assertEqual(repos, ["A", "B"])
        session.get.assert_called_once()

    def test_count_repo_commits_multiple_pages(self):
        session = Mock()
        # page 1 returns 2 commits and provides Link next
        session.get.side_effect = [
            make_response(
                200,
                json_data=[{"sha": "1"}, {"sha": "2"}],
                headers={"Link": '<https://api.github.com/repositories/1/commits?page=2>; rel="next"'},
                ok=True,
            ),
            make_response(
                200,
                json_data=[{"sha": "3"}],
                headers={},  # no next
                ok=True,
            ),
        ]
        client = GitHubClient(session=session)

        count = client.count_repo_commits("u", "r")
        self.assertEqual(count, 3)
        self.assertEqual(session.get.call_count, 2)

    def test_user_not_found(self):
        session = Mock()
        session.get.return_value = make_response(404, json_data={"message": "Not Found"}, ok=False)
        client = GitHubClient(session=session)

        with self.assertRaises(UserNotFoundError):
            client.get_user_repos("nope")

    def test_rate_limit(self):
        session = Mock()
        session.get.return_value = make_response(
            403,
            json_data={"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Remaining": "0"},
            ok=False,
        )
        client = GitHubClient(session=session)

        with self.assertRaises(RateLimitError):
            client.get_user_repos("someone")

    def test_repo_commit_counts_integration_with_mocks(self):
        session = Mock()
        # 1) /users/<id>/repos
        # 2) /repos/<id>/A/commits
        # 3) /repos/<id>/B/commits
        session.get.side_effect = [
            make_response(200, json_data=[{"name": "A"}, {"name": "B"}], headers={}, ok=True),
            make_response(200, json_data=[{"sha": "1"}], headers={}, ok=True),
            make_response(200, json_data=[{"sha": "1"}, {"sha": "2"}], headers={}, ok=True),
        ]
        client = GitHubClient(session=session)

        results = client.repo_commit_counts("someone")
        self.assertEqual([(r.repo_name, r.commit_count) for r in results], [("A", 1), ("B", 2)])


if __name__ == "__main__":
    unittest.main()
