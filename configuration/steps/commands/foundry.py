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
        if self.package_type == "RPM":
            install_cmd = "dnf install -y ./*.rpm"
        else:
            install_cmd = "apt-get install -y ./*.deb"
        return ["bash", "-exc", f"set -euo pipefail\n{install_cmd}"]


class RunPluginMTRSuite(Command):
    # Discovers the plugin's own MTR suite(s) the way mtr-suites.sh does --
    # any directory under a mysql-test/ (or mysql-test/suite/) directory in
    # the plugin's fetched source (<plugin>.build/) that has a suite.opt --
    # copies them into the installed suite tree, and runs them. A plugin
    # with no MTR suite is skipped rather than failing the build.
    def __init__(self, package_type: str, workdir: PurePath = PurePath(".")):
        self.package_type = package_type
        super().__init__(name="Run plugin MTR suite", workdir=workdir, user="root")

    def as_cmd_arg(self) -> list[str]:
        # Ask the package manager where MariaDB-test/mariadb-test actually
        # put mysql-test-run.pl, rather than guessing a path -- it's moved
        # across MariaDB package versions/layouts before.
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

mtr_script=$({list_files_cmd} | grep -m1 '/mysql-test-run\\.pl$')
if [ -z "$mtr_script" ]; then
    echo "Could not locate mysql-test-run.pl from the installed test package" >&2
    exit 1
fi
mtr_base_dir=$(dirname "$mtr_script")

plugin_build="%(prop:plugin)s.build"
suites=""
for mt in $(find "$plugin_build" -type d -name mysql-test 2>/dev/null); do
    for d in "$mt"/*/ "$mt"/suite/*/; do
        [ -f "${{d}}suite.opt" ] || continue
        name=$(basename "$d")
        cp -r "$d" "$mtr_base_dir/suite/$name"
        suites="$suites,$name"
    done
done
suites=$(echo "$suites" | sed 's/^,//')

if [ -z "$suites" ]; then
    echo "No MTR suite found for plugin %(prop:plugin)s -- skipping"
    exit 0
fi

cd "$mtr_base_dir" && perl mysql-test-run.pl --suite="$suites" --user=root
"""
            ),
        ]
