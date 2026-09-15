"""Authenticated github.com access for git operations that run on workers.

GitHub answers anonymous clones from our CI with HTTP 401 -- the problem
eea5c94 / cc453b0 tried to work around by forcing HTTP/1.1. The fix is to
authenticate with a read-only PAT.

When the PAT is sent: by default git sends every request anonymously and asks
for credentials only after a 401, so a green build proves nothing. We set
``http.proactiveAuth=basic`` so git sends the token with the first request.
That needs git >= 2.46; older git ignores the setting and authenticates only
when GitHub challenges it -- which still fixes the 401, but lets unchallenged
requests go out anonymously. Where proactive auth is in effect a missing or
empty token fails the clone rather than falling back to anonymous access; that
is intended, as the secret is mandatory.

The PAT is a buildbot secret and reaches git through an *environment variable*
only; git is told to run a credential helper that reads it. So the token stays
off the command line (invisible to `ps`) and out of `.git/config` on the
worker, and `%(secret:...)s` registers it for log redaction.

Redaction is master-side only, though: it runs in `RemoteCommand.remoteUpdate`
on data the worker already sent, while the worker *also* writes the command
line -- and, if `logEnviron` is on, the whole environment -- to its own
twistd.log, which nothing scrubs. Most of our workers are long-lived, so that
file persists. Hence two rules, both pinned by test_git_auth.py:

* every step carrying the token sets ``logEnviron=False``;
* no secret ever goes on a command line (the worker only obfuscates argv for
  explicit ``Obfuscated`` objects, which a rendered secret is not).

That second rule is also why this is a credential helper rather than
``http.extraheader``, which would have to carry ``base64(user:PAT)`` in argv.
``extraheader`` is unusable here anyway: ``config`` is not renderable on the
``Git``/``GitHub`` source steps, so a ``util.Secret`` placed there is never
resolved. ``env`` is renderable, which is what the helper needs.
"""

from buildbot.plugins import util

# Name of the file holding the PAT inside MASTER_CREDENTIALS_DIR, the
# SecretInAFile directory wired up in master_common.base_master_config().
# Read-only; authenticating at all is the point, no scope beyond public read is
# needed. Classic and fine-grained tokens both work. See the README.
#
# Nothing here authenticates a push. The only factory that pushes (the
# unexercised staging-branch rebase in master-protected-branches) keeps its own
# credential in master-private.cfg -- and moving it here would not be free,
# since buildbot renders a step's renderables *before* evaluating doStepIf, so
# the secret would have to resolve on every build, not just the rebasing ones.
GITHUB_TOKEN_SECRET = "github_token"

# Prefixed so it cannot collide with a GITHUB_TOKEN that build scripts or the
# gh CLI may expect to mean something else.
GITHUB_TOKEN_ENV_VAR = "BB_GITHUB_TOKEN"

# The helper. A leading '!' makes git run it through sh, appending the
# operation (get/store/erase) as an argument, which f() swallows. An empty
# variable yields no output, so git gets no credentials: without proactive auth
# it then proceeds anonymously, with it the clone fails.
#
# Two properties are load-bearing, and test_git_auth.py enforces both: no
# single quote, so it can be wrapped in '...' inside a bash command line; and
# no '%', so it survives util.Interpolate().
_CREDENTIAL_HELPER = (
    "!f(){ "
    f'[ -n "${{{GITHUB_TOKEN_ENV_VAR}:-}}" ] || return 0; '
    "echo username=x-access-token; "
    f'echo "password=${GITHUB_TOKEN_ENV_VAR}"; '
    "}; f"
)

# Scoped to github.com so the PAT is never offered to another host, e.g. a
# submodule pointing elsewhere.
_HELPER_KEY = "credential.https://github.com.helper"

# 'helper' is multi-valued: config-file values accumulate *before* -c ones and
# git stops at the first helper that answers, so a helper already on the worker
# (credential store, osxkeychain, gh) would shadow ours. Setting the key empty
# resets the list.
_HELPER_RESET_KEY = "credential.helper"

# Send the token with the first request rather than after a 401 (see the module
# docstring). Scoped to github.com as well: unscoped, git would demand
# credentials up front from every host and fail wherever the helper has none.
_PROACTIVE_AUTH_KEY = "http.https://github.com.proactiveAuth"

# The whole configuration, in order: the reset must precede the helper.
_GIT_CONFIG = (
    (_HELPER_RESET_KEY, ""),
    (_HELPER_KEY, _CREDENTIAL_HELPER),
    (_PROACTIVE_AUTH_KEY, "basic"),
)


def git_auth_config() -> dict:
    """``config=`` mapping for the ``Git``/``GitHub`` source steps.

    Static text, no secret. Pair it with :func:`git_auth_env`.
    """
    return dict(_GIT_CONFIG)


def git_auth_env() -> dict:
    """``env=`` mapping carrying the PAT, for any step running git.

    ``env`` is renderable on both ``ShellMixin`` and ``Source`` steps, so this
    resolves at build time and registers the value for log redaction.
    """
    return {GITHUB_TOKEN_ENV_VAR: util.Interpolate(f"%(secret:{GITHUB_TOKEN_SECRET})s")}


def git_auth_env_vars() -> list:
    """The same as the ``(name, value)`` list ``ShellStep`` expects.

    ``ShellStep`` applies ``util.Interpolate`` itself, so pass the raw string.
    """
    return [(GITHUB_TOKEN_ENV_VAR, f"%(secret:{GITHUB_TOKEN_SECRET})s")]


def git_auth_argv() -> list:
    """``git -c ...`` flags as argv, for callers that exec git directly."""
    return [arg for key, value in _GIT_CONFIG for arg in ("-c", f"{key}={value}")]


def git_auth_args() -> str:
    """``git -c ...`` flags for git invoked from a shell command string::

        f"git {git_auth_args()} fetch --depth 1 origin {commit}"

    Child git processes inherit the flags via ``GIT_CONFIG_PARAMETERS``, which
    is what makes ``git submodule update`` authenticate too.
    """
    # Quoting the helper unconditionally keeps the rendered command stable;
    # safe because it contains no single quote (see above).
    return " ".join(
        f"'{arg}'" if arg.startswith(_HELPER_KEY) else arg for arg in git_auth_argv()
    )


def git_auth_config_env() -> dict:
    """:func:`git_auth_args` as ``GIT_CONFIG_*`` env vars, to be merged into a
    step's ``env`` alongside :func:`git_auth_env`.

    For call sites where splicing ``-c`` into the command line is impractical:
    the Windows workers wrap git in ``dojob "..."``, where quoting is fragile.

    Needs git >= 2.31 -- fine for Git for Windows, but not for many of our
    Linux images (bb-master ships 2.30, RHEL 7 ships 1.8), hence
    :func:`git_auth_args` everywhere else. Older git ignores these variables,
    so the failure mode is a visible 401, not a silently unauthenticated build.
    """
    env = {"GIT_CONFIG_COUNT": str(len(_GIT_CONFIG))}
    for i, (key, value) in enumerate(_GIT_CONFIG):
        env[f"GIT_CONFIG_KEY_{i}"] = key
        env[f"GIT_CONFIG_VALUE_{i}"] = value
    return env
