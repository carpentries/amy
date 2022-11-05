import requests

API_BASE_URL = "https://api.github.com/repos/carpentries/amy"


def get_milestone_by_title(*, title: str, page: int = 1, per_page: int = 100) -> dict:
    milestone_response = requests.get(
        f"{API_BASE_URL}/milestones?per_page={per_page}&page={page}"
    )
    try:
        milestone_response.raise_for_status()
    except requests.HTTPError:
        return milestone_response.json()
    return milestone_response.json()


def get_milestone(*, number: int) -> dict:
    milestone_response = requests.get(f"{API_BASE_URL}/milestones/{number}")
    milestone_response.raise_for_status()
    return milestone_response.json()


def get_pull_requests_recursive(page: int = 1, per_page: int = 100) -> list[dict]:
    if page > 15:
        raise RuntimeError("Too many pull request pages calls")

    pr_response = requests.get(
        f"{API_BASE_URL}/pulls?state=closed&per_page={per_page}&page={page}"
    )
    try:
        pr_response.raise_for_status()
    except requests.HTTPError:
        return pr_response.json()

    pr_response_json = pr_response.json()
    if len(pr_response_json) == per_page:
        return pr_response_json + get_pull_requests_recursive(page + 1, per_page)
    else:
        return pr_response_json


def filter_pull_requests_by_milestone(prs: list[dict], milestone_id: int) -> list[dict]:
    return [pr for pr in prs if (pr.get("milestone") or {}).get("id") == milestone_id]


def pretty_pull_request(pr: dict) -> str:
    return (
        f"* {pr['title']} - [#{pr['number']}]({pr['html_url']}) @{pr['user']['login']}"
    )


def main() -> None:
    milestone = get_milestone(number=91)
    milestone_id = milestone["id"]

    all_prs = get_pull_requests_recursive()

    prs_for_milestone = filter_pull_requests_by_milestone(all_prs, milestone_id)
    for pr in prs_for_milestone:
        print(pretty_pull_request(pr))


if __name__ == "__main__":
    main()
