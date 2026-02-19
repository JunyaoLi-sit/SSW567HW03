\# HW03a – GitHub API Commit Counter



\## Description



This program takes a GitHub user ID as input and retrieves:

\- All repositories owned by the user

\- The number of commits in each repository



It uses the public GitHub REST API.



\## Installation



pip install -r requirements.txt



\## Run the Program



python main.py



\## Run Unit Tests



python -m unittest -v



\## Testing Strategy



The GitHubClient class was designed for testability.



\- The HTTP session is injected so it can be mocked.

\- All API calls are tested using unittest.mock.

\- Tests do not rely on real GitHub API calls.

\- Error handling (404, 403 rate limit) is verified.

\- Pagination is handled and tested.



