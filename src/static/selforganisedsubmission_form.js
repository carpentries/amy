const isGithubIoRepo = function(url) {
    const url_regex = /(?:https?:\/\/)?(?<username>[^.]+)\.github\.io\/(?<repo>[^\/]+)/i;
    const results = url.match(url_regex);
    if (!results) {
        return false;
    } else {
        return {username: results[1], repo: results[2]};
    }
}

const isGithubComRepo = function(url) {
    const url_regex = /(?:https?:\/\/)?github\.com\/(?<username>[^/]+)\/(?<repo>[^\/]+)/i;
    const results = url.match(url_regex);
    if (!results) {
        return false;
    } else {
        return {username: results[1], repo: results[2]};
    }
}

const isRepoNameValid = function(repo_name) {
    const repo_regex = /(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})-(?<name>.+)/i;
    const results = repo_name.match(repo_regex);
    if (!results) {
        return false;
    } else {
        return {year: results[1], month: results[2], day: results[3], name: results[4]};
    }
}

const validateWorkshopUrl = function(input, warning1, warning2) {
    const github_io = isGithubIoRepo(input.value);
    const github_com = isGithubComRepo(input.value);

    if (github_io) {
        // github.io link, let's check the repo name
        const repo_valid = isRepoNameValid(github_io.repo);
        if (!repo_valid) {
            // invalid repository name format
            input.classList.add("border");
            input.classList.add("border-warning");
            warning1.classList.remove("d-none");
        } else {
            // repo URL okay
            input.classList.remove("border");
            input.classList.remove("border-warning");
            warning1.classList.add("d-none");
            warning2.classList.add("d-none");
        }
    } else if (github_com) {
        // github.com link, show the warning
        input.classList.add("border");
        input.classList.add("border-warning");
        warning2.classList.remove("d-none");
    } else {
        // unable to match with anything, but it's okay - they may use
        // their own website
        input.classList.remove("border");
        input.classList.remove("border-warning");
        warning1.classList.add("d-none");
        warning2.classList.add("d-none");
    }
}

window.addEventListener("load", (e) => {
    const workshop_url = document.querySelector("#id_workshop_url");
    const repo_warning_div = document.querySelector("#workshop_url_repo_warning");
    const url_warning_div = document.querySelector("#workshop_url_warning");

    if (!!workshop_url) {
        validateWorkshopUrl(workshop_url, repo_warning_div, url_warning_div);

        workshop_url.addEventListener("change", ({target}) => {
            validateWorkshopUrl(target, repo_warning_div, url_warning_div);
        });
    }
});
