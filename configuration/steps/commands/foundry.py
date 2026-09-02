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
            script = """
apt-get install -y ./*.deb
for f in ./*.deb; do
    pkg=$(dpkg-deb -f "$f" Package)
    dpkg -s "$pkg" >/dev/null 2>&1 || { echo "Package $pkg from $f was not installed" >&2; exit 1; }
done
"""
        return ["bash", "-exc", f"set -euo pipefail\n{script}"]


class RunPluginMTRSuite(Command):
    # MARIADB_ADD_PLUGIN's INSTALL_MYSQL_TEST (cmake/plugin.cmake) installs
    # a plugin's mysql-test suite(s) under <mtr_base_dir>/plugin/<X>/<name>/,
    # e.g. plugin/rocksdb/rocksdb/suite.pm or
    # plugin/columnstore/columnstore/suite.pm. <X> is the plugin's own CMake
    # project/target name, which isn't always the same as the Foundry
    # "plugin" property (e.g. tidesql's CMake target is actually "tidesdb"),
    # so rather than guess it, discover whatever actually landed under
    # plugin/*/*/suite.pm -- exactly one plugin gets installed per build.
    # mtr_cases.pm resolves a bare suite name (e.g. "rocksdb") by searching
    # under plugin/*/ itself, so passing just the suite's short name is
    # enough -- no need to spell out the plugin/<X>/ prefix. A plugin with no
    # suite.pm anywhere under it is skipped rather than failing the build.
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
for suite_pm in "$mtr_base_dir"/plugin/*/*/suite.pm; do
    [ -f "$suite_pm" ] || continue
    name=$(basename "$(dirname "$suite_pm")")
    suites="$suites,$name"
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
