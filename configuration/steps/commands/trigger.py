from buildbot.plugins import steps
from buildbot.process.buildstep import BuildStepFailed
from buildbot.process.properties import Interpolate, Property
from buildbot.steps.trigger import Trigger as BuildbotTrigger
from twisted.internet import defer

from configuration.builders.definitions.foundry import sources
from constants import SAVED_PACKAGE_BRANCHES
from utils import (
    hasDockerLibrary,
    hasInstall,
    hasPackagesGenerated,
    hasUpgrade,
    savePackageIfBranchMatch,
)


class Trigger:
    def __init__(self, name, schedulername, doStepIf, properties=None):
        self.name = name
        self.schedulername = schedulername
        self.doStepIf = doStepIf
        self.properties = properties or {}

    def generate(self):
        return steps.Trigger(
            name=self.name,
            schedulerNames=[self.schedulername],
            waitForFinish=False,  # standard value across buildbot
            updateSourceStamp=False,  # standard value across buildbot
            set_properties=self.properties,
            doStepIf=self.doStepIf,
        )


class Server(Trigger):
    def __init__(self, name, schedulername, doStepIf, additional_properties=None):
        properties = {
            "tarbuildnum": Property("tarbuildnum"),  # set by tarball-docker
            "mariadb_version": Property("mariadb_version"),  # set by tarball-docker
            "master_branch": Property("master_branch"),  # set by tarball-docker
            "parentbuildername": Property("buildername"),  # set by tarball-docker
        }
        if additional_properties:
            properties.update(additional_properties)
        super().__init__(name, schedulername, doStepIf, properties)


class ConODBC(Trigger):
    def __init__(self):
        self.name = "Trigger Conc-ODBC Builders"
        self.schedulername = "conc_odbc_all_scheduler"
        self.doStepIf = lambda step: True
        properties = {
            "tarbuildnum": Property(
                "buildnumber"
            ),  # Used by get_tarball.sh to identify the tarball dir on CI
            "mariadb_version": "ci",  # Used by get_tarball.sh to download ci.tar.gz
            "odbc_to_mariadb_repo": Property("odbc_to_mariadb_repo"),
            "odbc_version": Property("odbc_version"),
        }

        super().__init__(self.name, self.schedulername, self.doStepIf, properties)


class ConCPP(Trigger):
    def __init__(self):
        self.name = "Trigger Conc-CPP Builders"
        self.schedulername = "conc_cpp_all_scheduler"
        self.doStepIf = lambda step: True
        properties = {
            "tarbuildnum": Property(
                "buildnumber"
            ),  # Used by get_tarball.sh to identify the tarball dir on CI
            "mariadb_version": "ci",  # Used by get_tarball.sh to download ci.tar.gz
            "cpp_to_mariadb_repo": Property("cpp_to_mariadb_repo"),
            "cpp_version": Property("cpp_version"),
        }

        super().__init__(self.name, self.schedulername, self.doStepIf, properties)


class ConC(Trigger):
    def __init__(self):
        self.name = "Trigger Conc-C Builders"
        self.schedulername = "conc_c_all_scheduler"
        self.doStepIf = lambda step: True
        properties = {
            "tarbuildnum": Property(
                "buildnumber"
            ),  # Used by get_tarball.sh to identify the tarball dir on CI
            "mariadb_version": "ci",  # Used by get_tarball.sh to download ci.tar.gz
        }

        super().__init__(self.name, self.schedulername, self.doStepIf, properties)


class _FoundryDispatchStep(BuildbotTrigger):
    # Rendered before getSchedulersAndProperties runs; merged with Trigger's
    # own renderables, in both buildbot 2.x and 3.0+.
    renderables = ["source_url"]

    def __init__(self, trigger_specs, source_url, **kwargs):
        self.trigger_specs = trigger_specs
        self.source_url = source_url
        super().__init__(**kwargs)

    # Buildbot's dynamic-trigger extension point: lets one step fan out to a
    # different set of schedulers/properties per MariaDB version, instead of
    # needing one static Trigger step per version. Everything that varies is
    # read from this build's own properties (set by foundry_force_scheduler)
    # -- self.trigger_specs isn't a renderable, it's plain config-time data
    # naming the fields to look at and the Triggerable each answer maps to.
    @defer.inlineCallbacks
    def getSchedulersAndProperties(self):
        # Discovered by the preceding step from the Foundry checkout, not
        # chosen by whoever started the build -- see DiscoverFoundryPlugins.
        plugins = str(self.getProperty("foundry_plugins", "") or "").strip()
        # A pull request build validates a proposed change: it doesn't get to
        # pick a server source (the mirrors are the only sane one for an
        # arbitrary contributor's branch) and it doesn't publish packages.
        branch = str(self.getProperty("branch", "") or "")
        is_pull_request = branch.startswith("refs/pull/")
        # The commit the preceding steps checked out and discovered the
        # plugins in, and the archive of it every package build unpacks
        # instead of cloning Foundry -- see trigger_foundry() in
        # sequences/foundry/dispatcher.py. Triggered builds don't inherit
        # this build's properties, so all of it is passed on explicitly.
        commit = str(self.getProperty("foundry_head", "") or "").strip()
        foundry_source = {
            "foundry_commit": commit,
            # Short form, for the paths saved packages and logs go under.
            "foundry_revision": str(
                self.getProperty("foundry_revision", "") or ""
            ).strip(),
            "foundry_source_url": self.source_url,
            "foundry_source_sha256": str(
                self.getProperty("foundry_source_sha256", "") or ""
            ).strip(),
        }
        schedulers_and_properties = []
        # Which versions ran against what is the whole point of this build,
        # and a skipped version leaves no other trace -- so spell the
        # outcome out rather than leaving it to be inferred from which
        # child builds appeared.
        plan = []
        errors = []

        event = "pull request" if is_pull_request else "force build"
        header = [f"event:   {event}", f"commit:  {commit or '(unknown)'} ({branch})"]

        if not plugins:
            # Legitimate for a pull request that touches no plugin (docs, CI
            # config, a plugin directory without a CMakeLists.txt): there is
            # simply nothing to build, which is a pass, not a failure.
            yield self.addCompleteLog(
                "dispatch plan",
                "\n".join(header + ["No plugins to build -- nothing triggered"]) + "\n",
            )
            return []

        missing = [name for name, value in foundry_source.items() if not value]
        if missing:
            # The package builders have no other way to get Foundry.
            errors.append(
                f"no Foundry source to hand on, missing: {', '.join(missing)}"
            )

        for spec in self.trigger_specs:
            version = spec["mariadb_version"]
            if is_pull_request:
                source = sources.MIRROR
                tarbuildnum = ""
            else:
                source = self.getProperty(spec["source_property"], sources.DEFAULT)
                tarbuildnum = str(
                    self.getProperty(spec["tarbuildnum_property"], "") or ""
                ).strip()

            if source not in sources.CHOICES:
                # Not reachable from the force dialog (the choice field is
                # strict), but a rebuild can carry a hand-edited property.
                errors.append(
                    f"{version}: unknown package source {source!r} -- expected "
                    f"one of {', '.join(repr(c) for c in sources.CHOICES)}"
                )
                continue

            if source == sources.SKIP:
                plan.append(f"{version}: skipped, no builders triggered")
                continue

            if source == sources.CI_TARBALL and not tarbuildnum:
                errors.append(
                    f"{version}: set to '{sources.CI_TARBALL}' but no tarbuildnum "
                    f"was given -- supply one, or pick '{sources.MIRROR}' or "
                    f"'{sources.SKIP}' instead"
                )
                continue

            properties = {
                "mariadb_version": version,
                "foundry_plugins": plugins,
                "is_pull_request": is_pull_request,
                **foundry_source,
            }
            if source == sources.CI_TARBALL:
                # The package builders branch on tarbuildnum alone: set means
                # ci.mariadb.org, unset means the MariaDB Server mirrors (see
                # autobake.py). Leave it out entirely for the mirror case
                # rather than setting it empty, so an inherited property from
                # a rebuild can't quietly resurrect the CI path.
                properties["tarbuildnum"] = tarbuildnum
                plan.append(f"{version}: https://ci.mariadb.org/{tarbuildnum}/")
            else:
                plan.append(f"{version}: MariaDB Server mirrors")

            schedulers_and_properties.append((spec["scheduler"], properties))
            if spec["ci_only_targets"]:
                # Platforms not on the mirrors yet: only a CI tarball has
                # server packages for them.
                ci_only = ", ".join(spec["ci_only_targets"])
                if source == sources.CI_TARBALL:
                    schedulers_and_properties.append(
                        (spec["ci_only_scheduler"], properties)
                    )
                    plan.append(f"{version}: also CI-only targets: {ci_only}")
                else:
                    plan.append(f"{version}: skipped CI-only targets: {ci_only}")

        lines = [*header, f"plugins: {plugins}", *plan]
        if errors:
            lines += ["", "Nothing was triggered:", *errors]
        yield self.addCompleteLog("dispatch plan", "\n".join(lines) + "\n")
        if errors:
            # BuildStepFailed carries no message into the build result, hence
            # the log above -- raise only once it's been written, and before
            # anything is triggered, so a bad field can't leave half the
            # versions dispatched.
            raise BuildStepFailed()
        return schedulers_and_properties


class FoundryDispatch:
    def __init__(self, trigger_specs, source_url: str):
        # trigger_specs: one dict per supported MariaDB version -- see
        # _dispatch_specs() in
        # configuration/builders/definitions/foundry/builders.py.
        # source_url: where the package builders download the Foundry
        # archive from, an Interpolate string.
        self.trigger_specs = trigger_specs
        self.source_url = source_url

    def generate(self):
        # Trigger resolves scheduler names against this list, so it has to
        # cover every Triggerable getSchedulersAndProperties may pick -- a
        # given build only fires the ones whose version wasn't skipped.
        return _FoundryDispatchStep(
            trigger_specs=self.trigger_specs,
            source_url=Interpolate(self.source_url),
            name="Trigger Foundry Builders",
            schedulerNames=sorted(
                {spec["scheduler"] for spec in self.trigger_specs}
                | {
                    spec["ci_only_scheduler"]
                    for spec in self.trigger_specs
                    if spec["ci_only_scheduler"]
                }
            ),
            # Wait for the package builds and take the worst of their
            # results, so the dispatcher build -- and the GitHub status it
            # reports on pull requests -- fails if any of them does. The
            # waiting build holds one job on its worker, and since a worker
            # runs one build per builder, the next Foundry run queues until
            # this one's package builds are done.
            waitForFinish=True,
            updateSourceStamp=False,
        )


class Install(Server):
    def __init__(self):
        self.name = "Trigger Install Builders"
        self.schedulername = "s_install"
        self.doStepIf = (
            lambda step: hasInstall(step)
            and savePackageIfBranchMatch(step, SAVED_PACKAGE_BRANCHES)
            and hasPackagesGenerated(step)
        )

        super().__init__(self.name, self.schedulername, self.doStepIf)


class Upgrade(Server):
    def __init__(self):
        self.name = "Trigger Upgrade Builders"
        self.schedulername = "s_upgrade"
        self.doStepIf = (
            lambda step: hasUpgrade(step)
            and savePackageIfBranchMatch(step, SAVED_PACKAGE_BRANCHES)
            and hasPackagesGenerated(step)
        )

        super().__init__(self.name, self.schedulername, self.doStepIf)


class DockerLibrary(Server):
    def __init__(self, RHEL):
        self.name = "Trigger DockerLibrary Builder"
        self.schedulername = "s_dockerlibrary"
        self.doStepIf = lambda step: hasDockerLibrary(step)
        self.additional_properties = {}
        if RHEL:
            self.additional_properties = {
                "ubi": "-ubi",
                "GH_WORKFLOW": "test-image-ubi.yml",
            }

        super().__init__(
            self.name, self.schedulername, self.doStepIf, self.additional_properties
        )
