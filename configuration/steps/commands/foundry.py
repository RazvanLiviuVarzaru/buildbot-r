from pathlib import PurePath

from buildbot.plugins import util
from configuration.steps.commands.base import Command


class BuildPlugin(Command):
    # package_type: "RPM" or "DEB" -- the -D flag run.cmake expects.
    def __init__(self, package_type: str, workdir: PurePath = PurePath(".")):
        self.package_type = package_type
        super().__init__(name=f"Build plugin ({package_type})", workdir=workdir)

    def as_cmd_arg(self) -> list[str]:
        return [
            "bash",
            "-exc",
            util.Interpolate(f"cmake -D{self.package_type}=1 -P run.cmake %(prop:plugin)s"),
        ]


class InstallBuiltPackages(Command):
    # Installs whatever run.cmake just built (copied next to run.cmake, see
    # run.cmake's `file(COPY ${packages} DESTINATION "${b}/..")`).
    def __init__(self, package_type: str, workdir: PurePath = PurePath(".")):
        self.package_type = package_type
        super().__init__(
            name=f"Install built plugin packages ({package_type})",
            workdir=workdir,
            user="root",
        )

    def as_cmd_arg(self) -> list[str]:
        # apt-get/dnf can exit 0 having installed nothing (e.g. a malformed
        # package filename it silently ignores) -- verify each built package
        # actually landed, instead of only trusting the install command's
        # own exit code.
        if self.package_type == "RPM":
            script = """
dnf install -y ./*.rpm
for f in ./*.rpm; do
    pkg=$(rpm -qp --qf '%{NAME}' "$f")
    rpm -q "$pkg" >/dev/null 2>&1 || { echo "Package $pkg from $f was not installed" >&2; exit 1; }
done
"""
        else:
            # apt-get/apt's dependency resolver can silently refuse to add a
            # local .deb to its changeset when the filename contains a ":"
            # (as ours does, from the Debian epoch) -- dpkg -i installs the
            # file directly with no such ambiguity, then apt -f pulls in
            # anything it couldn't resolve on its own.
            script = """
dpkg -i ./*.deb || true
apt-get install -f -y
for f in ./*.deb; do
    pkg=$(dpkg-deb -f "$f" Package)
    dpkg -s "$pkg" >/dev/null 2>&1 || { echo "Package $pkg from $f was not installed" >&2; exit 1; }
done
"""
        return ["bash", "-exc", f"set -euo pipefail\n{script}"]


class RunPluginMTRSuite(Command):
    # MARIADB_ADD_PLUGIN's INSTALL_MYSQL_TEST (cmake/plugin.cmake) always
    # installs a plugin's mysql-test/ contents -- suite/ included -- under
    # <mtr_base_dir>/plugin/<X>/, so the suite ends up at
    # plugin/<X>/suite/<name>, not plugin/<X>/<name>. <X> is the plugin's own
    # CMake project/target name, which isn't always the same as the Foundry
    # "plugin" property (e.g. tidesql's CMake target is actually "tidesdb"),
    # so rather than guess it, discover whatever actually landed under
    # plugin/*/suite/* -- exactly one plugin gets installed per build.
    # mtr_cases.pm's short-name lookup for `--suite=NAME` doesn't account for
    # the extra suite/ level either way, so we pass MTR the full relative
    # path instead, which it accepts directly. A plugin with no suite/ dir
    # at all is skipped rather than failing the build.
    def __init__(self, package_type: str, workdir: PurePath = PurePath(".")):
        self.package_type = package_type
        super().__init__(name="Run plugin MTR suite", workdir=workdir, user="root")

    def as_cmd_arg(self) -> list[str]:
        # Ask the package manager where MariaDB-test/mariadb-test actually
        # put mariadb-test-run.pl, rather than guessing a path -- it's moved
        # across MariaDB package versions/layouts before. Match the current
        # top-level script by name, and exclude lib/v1/ specifically -- it
        # bundles its own legacy-named mysql-test-run.pl that isn't it.
        if self.package_type == "RPM":
            list_files_cmd = "rpm -ql MariaDB-test"
        else:
            list_files_cmd = "dpkg -L mariadb-test"
        return [
            "bash",
            "-exc",
            util.Interpolate(
                f"""
set -euo pipefail

mtr_script=$({list_files_cmd} | grep -v '/lib/v1/' | grep -m1 '/mariadb-test-run\\.pl$' || true)
if [ -z "$mtr_script" ]; then
    echo "Could not locate mariadb-test-run.pl from the installed test package" >&2
    exit 1
fi
mtr_base_dir=$(dirname "$mtr_script")

suites=""
for suite_dir in "$mtr_base_dir"/plugin/*/suite; do
    [ -d "$suite_dir" ] || continue
    plugin_dir=$(basename "$(dirname "$suite_dir")")
    for d in "$suite_dir"/*/; do
        [ -d "$d" ] || continue
        name=$(basename "$d")
        suites="$suites,plugin/$plugin_dir/suite/$name"
    done
done
suites=$(echo "$suites" | sed 's/^,//')

if [ -z "$suites" ]; then
    echo "No MTR suite found for plugin %(prop:plugin)s -- skipping"
    exit 0
fi

cd "$mtr_base_dir" && perl mariadb-test-run.pl --force --max-test-fail=20 --suite="$suites" --vardir=/home/buildbot
"""
            ),
        ]
