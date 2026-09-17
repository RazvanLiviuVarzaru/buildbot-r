from buildbot.plugins import reporters


class FoundryPullRequestStatusPush(reporters.GitHubStatusPush):
    # The stock GitHub reporter, narrowed to pull request builds: this
    # buildbot's reporters can only filter by builder name, and the
    # dispatcher also runs force builds, whose sourcestamp has no revision
    # to report on. A pull request's sourcestamp carries the PR head SHA and
    # "MariaDB/foundry" as project, set by the GitHub hook.
    #
    # Its own name, since every master already has a GitHubStatusPush (see
    # master_common.py) and service names must be unique.
    name = "FoundryPullRequestStatusPush"

    def filterBuilds(self, build):
        branch = build["properties"].get("branch", ("", None))[0] or ""
        return super().filterBuilds(build) and branch.startswith("refs/pull/")
