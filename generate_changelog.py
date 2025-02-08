from datetime import datetime
import sys

import requests

API_BASE_URL = "https://api.github.com/repos/carpentries/amy"
API_SEARCH_URL = "https://api.github.com/search"


def read_milestone_version() -> str:
    """Read milestone from argv, if provided. Otherwise ask user."""
    if len(sys.argv) >= 2:
        return sys.argv[1]

    milestone_version = input("Provide milestone title: ")
    return milestone_version


def get_milestone(*, number: int) -> dict:
    milestone_response = requests.get(f"{API_BASE_URL}/milestones/{number}")
    milestone_response.raise_for_status()
    return milestone_response.json()


def search_closed_prs_in_milestone(
    milestone: str,
    repository: str = "carpentries/amy",
    *,
    page: int = 1,
    per_page: int = 100,
) -> list[dict]:
    if page >= 10:
        raise RuntimeError("Too many pull request pages calls")

    Q = f"repo:{repository} type:pr is:merged milestone:{milestone}"
    URL = (
        f"{API_SEARCH_URL}/issues?q={Q}&sort=created&order=desc"
        f"&per_page={per_page}&page={page}"
    )
    response = requests.get(URL)
    response.raise_for_status()

    json = response.json()
    results = json["items"]

    if len(results) >= per_page:
        return results + search_closed_prs_in_milestone(
            milestone, repository, page=page + 1, per_page=per_page
        )
    return results


def parse_iso8601z(date_string: str) -> datetime:
    if sys.version_info >= (3, 11):
        return datetime.fromisoformat(date_string)
    return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")


def pretty_milestone(milestone: dict) -> str:
    is_closed = milestone["state"] == "closed"

    if is_closed:
        closed_at = parse_iso8601z(milestone["closed_at"])
        return f"## {milestone['title']} - {closed_at:%Y-%m-%d}\n"

    return f"## {milestone['title']} - unreleased\n"


def pretty_pull_request(pr: dict) -> str:
    return (
        f"* {pr['title']} - [#{pr['number']}]({pr['html_url']})"
        f" by @{pr['user']['login']}"
    )


def find_milestone_number_in_pr(pr: dict) -> int:
    return pr["milestone"]["number"]


def labels_contain(label_name: str, labels: list[dict]) -> bool:
    return label_name in {label["name"] for label in labels}


def find_bugs_features_in_prs(prs: list[dict]) -> tuple[list[dict], list[dict]]:
    bugfixes = [pr for pr in prs if labels_contain("type: bug", pr["labels"])]
    features = [pr for pr in prs if not labels_contain("type: bug", pr["labels"])]
    return bugfixes, features


def pretty_bugfixes(bugfixes: list[dict]) -> str:
    return (
        "### Bugfixes\n"
        + "\n".join(pretty_pull_request(bugfix) for bugfix in bugfixes)
        + "\n"
    )


def pretty_features(features: list[dict]) -> str:
    return (
        "### Features\n"
        + "\n".join(pretty_pull_request(feature) for feature in features)
        + "\n"
    )


def main() -> None:
    milestone_version = read_milestone_version()
    results = search_closed_prs_in_milestone(milestone_version)

    if results:
        milestone_number = find_milestone_number_in_pr(results[0])
        milestone = get_milestone(number=milestone_number)
        print(pretty_milestone(milestone))

    bugfixes, features = find_bugs_features_in_prs(results)

    if bugfixes:
        print(pretty_bugfixes(bugfixes))

    if features:
        print(pretty_features(features))


if __name__ == "__main__":
    main()
