import os
import sys

from buildbot.plugins import reporters, secrets, util
from constants import GITHUB_STATUS_BUILDERS
from schedulers_definition import SCHEDULERS

try:
    from buildbot.reporters.generators.build import BuildStartEndStatusGenerator
    from buildbot.reporters.message import MessageFormatterRenderable
except ImportError:
    BuildStartEndStatusGenerator = None
    MessageFormatterRenderable = None

IS_CHECKCONFIG = any("checkconfig" in arg for arg in sys.argv)


def _github_status_reporter(github_access_token):
    kwargs = {
        "token": github_access_token,
        "context": util.Interpolate("buildbot/%(prop:buildername)s"),
        "verbose": True,
    }

    if BuildStartEndStatusGenerator is None:
        # TODO: Drop this legacy fallback after Buildbot < 2.10 is no longer
        # supported. Newer Buildbot versions should use generators instead of
        # startDescription/endDescription/builders.
        kwargs.update(
            {
                "startDescription": "Build started.",
                "endDescription": "Build done.",
                "builders": GITHUB_STATUS_BUILDERS,
            }
        )
    else:
        kwargs["generators"] = [
            BuildStartEndStatusGenerator(
                builders=GITHUB_STATUS_BUILDERS,
                start_formatter=MessageFormatterRenderable("Build started."),
                end_formatter=MessageFormatterRenderable("Build done."),
            )
        ]

    return reporters.GitHubStatusPush(**kwargs)


def base_master_config(
    config: dict,
    title=os.environ["TITLE"],
    title_url=os.environ["TITLE_URL"],
    buildbot_url=os.environ["BUILDMASTER_URL"],
    secrets_provider_file=os.environ["MASTER_CREDENTIALS_DIR"],
    master_port=os.environ["PORT"],
    mq_router_url=os.environ["MQ_ROUTER_URL"],
):
    # TODO(cvicentiu) either move this to environ or all other params to config
    # file.
    github_access_token = config["private"]["gh_mdbci"]["access_token"]
    db_url = config["private"]["db_url"]

    return {
        #######
        # PROJECT IDENTITY
        #######
        # the 'title' string will appear at the top of this buildbot
        # installation's
        "title": title,
        # home pages (linked to the 'titleURL').
        "titleURL": title_url,
        # the 'buildbotURL' string should point to the location where the
        # buildbot's internal web server is visible. This typically uses the
        # port number set in the 'www' entry below, but with an
        # externally-visible host name which the buildbot cannot figure out
        # without some help.
        "buildbotURL": buildbot_url,
        # 'services' is a list of BuildbotService items like reporter targets.
        # The status of each build will be pushed to these targets.
        # buildbot/reporters/*.py has a variety to choose from, like IRC bots.
        "services": [_github_status_reporter(github_access_token)],
        "secretsProviders": [secrets.SecretInAFile(dirname=secrets_provider_file)],
        # 'protocols' contains information about protocols which master will
        # use for communicating with workers. You must define at least 'port'
        # option that workers could connect to your master with this protocol.
        # 'port' must match the value configured into the workers (with their
        # --master option)
        "protocols": {
            "pb": {"port": int(master_port)},  # master_port must be int
        },
        # This specifies what database buildbot uses to store its state.
        "db": {
            "db_url": db_url,
        },
        # Disable net usage reports from being sent to buildbot.net
        "buildbotNetUsageData": None,
        # Configure the Schedulers, which decide how to react to incoming
        # changes.
        "schedulers": SCHEDULERS,
        "logEncoding": "utf-8",
        "multiMaster": True,
        "mq": {
            # Need to enable multimaster aware mq. Wamp is the only option for
            # now.
            "type": "wamp",
            "router_url": mq_router_url,
            "realm": "realm1",
            # valid are: none, critical, error, warn, info, debug, trace
            "wamp_debug_level": "info",
        },
    }
