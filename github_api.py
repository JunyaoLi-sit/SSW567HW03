from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import requests


class GitHubApiError(Exception):
    """Base exception for GitHub API errors."""


class UserNotFoundError(GitHubApiError):
    """Raised when the GitHub user does not exist."""


class RateLimitError(GitHubApiError):
    """Raised when GitHub rate limit is exceeded."""


@dataclass(frozen=True)
class RepoCommits:
    repo_name: str
    commit_count: int


class GitHubClient:
    """
    Small wrapper around GitHub REST API (public endpoints).

    Key design-for-test choices:
    - Dependency injection of `session` so unit tests can mock network calls
    - Single pagination helper to test once
    """

    def __init__(self, session: Optional[requests.Session] = None, base_url: str = "https://api.github.com"):
        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/")

    def get_user_repos(self, user_id: str) -> List[str]:
        url = f"{self.base_url}/users/{user_id}/repos"
        repos_json = self._get_paginated_json(url, params={"per_page": 100})
        # Each item has "name" (per assignment)
        return [repo["name"] for repo in repos_json if "name" in repo]

    def count_repo_commits(self, user_id: str, repo_name: str) -> int:
        url = f"{self.base_url}/repos/{user_id}/{repo_name}/commits"
        commits_json = self._get_paginated_json(url, params={"per_page": 100})
        # Assignment says: "count how many elements are in this list"
        return len(commits_json)

    def repo_commit_counts(self, user_id: str) -> List[RepoCommits]:
        repo_names = self.get_user_repos(user_id)
        results: List[RepoCommits] = []
        for repo in repo_names:
            results.append(RepoCommits(repo_name=repo, commit_count=self.count_repo_commits(user_id, repo)))
        return results

    # ---------- internal helpers ----------

    def _get_paginated_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Fetch all pages for endpoints that return a JSON list.
        Uses GitHub 'Link' header pagination.
        """
        all_items: List[Dict[str, Any]] = []
        next_url = url
        next_params = dict(params or {})

        while next_url:
            resp = self.session.get(
                next_url,
                params=next_params,
                headers={"Accept": "application/vnd.github+json"},
                timeout=15,
            )

            # After first request, pagination URLs already include query;
            # safer to stop re-sending params.
            next_params = {}

            if resp.status_code == 404:
                raise UserNotFoundError(f"Not found: {url}")
            if resp.status_code == 403:
                # Could be rate limit or forbidden
                remaining = resp.headers.get("X-RateLimit-Remaining")
                if remaining == "0":
                    raise RateLimitError("GitHub API rate limit exceeded.")
                raise GitHubApiError(f"Forbidden (403) calling {url}")
            if not resp.ok:
                raise GitHubApiError(f"HTTP {resp.status_code} calling {url}")

            data = resp.json()
            if not isinstance(data, list):
                raise GitHubApiError(f"Expected list JSON from {url}, got {type(data).__name__}")

            all_items.extend(data)
            next_url = self._parse_next_link(resp.headers.get("Link"))

        return all_items

    @staticmethod
    def _parse_next_link(link_header: Optional[str]) -> Optional[str]:
        """
        Parse GitHub Link header and return URL for rel="next" if present.
        """
        if not link_header:
            return None

        # Example:
        # <https://api.github.com/...&page=2>; rel="next", <...page=3>; rel="last"
        parts = [p.strip() for p in link_header.split(",")]
        for p in parts:
            if 'rel="next"' in p:
                left = p.find("<")
                right = p.find(">")
                if left != -1 and right != -1 and right > left:
                    return p[left + 1 : right]
        return None
