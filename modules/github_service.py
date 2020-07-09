from github import Github


def create_issue(detection_name, config):
    title = detection_name + " needs testing"

    g = Github(config["github_token"])
    repo = g.get_repo(config["github_repo"])


    create_issue = True
    open_issues = repo.get_issues(state='open')
    for issue in open_issues:
        if issue.title == title:
            create_issue = False

    if create_issue:
        repo.create_issue(title=title, body="This detection failed automated testing. Please review.")
