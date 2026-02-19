from github_api import GitHubClient, GitHubApiError

def main():
    user_id = input("Enter a GitHub user ID: ").strip()
    client = GitHubClient()

    try:
        results = client.repo_commit_counts(user_id)
        if not results:
            print("No repositories found.")
            return

        for item in results:
            print(f"Repo: {item.repo_name} Number of commits: {item.commit_count}")

    except GitHubApiError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
