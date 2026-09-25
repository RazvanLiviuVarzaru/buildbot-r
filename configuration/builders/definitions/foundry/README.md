# Foundry build pipeline

[MariaDB/foundry](https://github.com/MariaDB/foundry) holds a set of MariaDB server plugins, one per top-level directory, all built through a single `cmake -P run.cmake` entry point.

This pipeline takes that repository and, for every supported MariaDB version, builds each plugin as a native package on every supported OS and architecture, installs it, and runs the plugin's own MTR suites against a matching MariaDB server.

Two things vary per run and are decided at run time rather than baked into the builders: **which plugins** get built, and **where the MariaDB server packages come from**. The MariaDB version is carried into the build as a property, so the same builders serve every version instead of the matrix gaining a dimension.

## Pipeline

```text
  trigger                dispatcher                per version           per OS/arch
  ------------------     --------------------      -----------------     ------------------
  Force button       \   foundry-trigger-builders   foundry_11_4_...      foundry-amd64-...
                      >  clone Foundry,          >  fan out with       >  build, install,
  GitHub pull req.   /   discover plugins           plugins + source       MTR, save
```

1. **Trigger** — someone presses Force, or GitHub sends a pull request event for the Foundry repository.
1. **Discover** — the dispatcher clones Foundry, reads the plugin list out of it (all plugins, or just the ones a pull request touches), and publishes a `git archive` of the commit it got.
1. **Fan out** — one `Triggerable` per supported MariaDB version, carrying that archive, the plugin list and the chosen package source.
1. **Build and test** — per OS and architecture, starting from the downloaded archive: rpm and deb packages are built in the target's worker image, then installed and tested in its plain upstream base image (see below).
1. **Report** — the dispatcher waits for every package build and fails if any of them does. On a pull request, its result is posted to GitHub as the `buildbot/foundry-trigger-builders` status.

### Installing into a base image

A worker image already carries most of what MariaDB and its plugins need, so a package that forgets to declare a dependency would still install and pass there. rpm and deb packages are therefore installed and tested in the target's `base_image` from `foundry.yaml`, the upstream image its worker image is built from (e.g. `debian:12`, `quay.io/centos/centos:stream9`, `ubi9/ubi`, `bci-base:16.0`), so they have to pull in every dependency themselves.

The build workspace, with the built packages in it, carries over; nothing installed in the worker image does. The base image gets only what the pipeline itself needs: the `buildbot` user (uid 1000, owner of the workspace), `ca-certificates` and `curl` on apt bases, `findutils` on zypper bases. RHEL targets use UBI with the host's RHEL entitlement mounted (`base_mounts`), so they must run on RHEL hosts. x86 uses Docker Hub's `i386/` images, so it never shares a local tag with amd64.

Bintar targets (centos7, almalinux8) have no `-devel` packages to install against, so they link the plugin against an unpacked MariaDB server tarball and run that tarball's bundled MTR instead of installing system packages.

## Starting a run

### Force build

The force scheduler takes an optional **Foundry commit** (a full SHA). Left empty, the run builds the tip of `repository.branch` in `foundry.yaml` (`main`) as it is when the dispatcher starts.

Either way, the dispatcher is the only one to clone Foundry. It publishes a `git archive` of the commit it checked out, and every package build downloads that, checked against its SHA-256, instead of cloning it again. That is one fetch from GitHub per run rather than one per package build. Package builds start whenever a worker is free, and the branch or pull request may have moved on by then, but all of a run's builds build the commit its plugins were discovered in. The dispatch plan log shows the commit.

The archive holds Foundry alone. Each plugin's own code is fetched by the plugin's `CMakeLists.txt` when it builds, as before.

For each supported MariaDB version the force scheduler also asks where the server packages should come from:

- **Use MariaDB Server mirrors** — the default; released packages from `mirror.mariadb.org`.
- **Use a ci.mariadb.org tarball** — build against a specific `tarbuildnum`, for testing against an unreleased server.
- **Skip this version** — no builders triggered for it.

There is no plugin picker: the dispatcher discovers what to build.

Only the GitHub users listed under `access.force_users` in `foundry.yaml` can press Force, since that is where a run's inputs are chosen. Other MariaDB members still see the button but get a 403. They can still Rebuild an existing run, which reuses its inputs.

### Pull request

Fully automatic, and deliberately narrower than a force build:

- Only the plugins the pull request changes. A pull request touching the top-level `CMakeLists.txt` or `run.cmake` rebuilds everything, since those affect every plugin.
- Mirrors only; there is no CI tarball to choose.
- Packages are not saved.
- A pull request touching no plugin passes without building anything.

Changed files are read with `git` from the checkout, diffing against the merge base with the pull request's target branch. Buildbot's own Changed Files are not populated for pull request events on this deployment.

## Several plugins in one run

A run builds every discovered plugin in one `run.cmake` invocation, which keeps going after a plugin fails (`message(SEND_ERROR)`, not `FATAL_ERROR`). One broken plugin must not hide the others' results, so the build and install steps report a three-state outcome:

| Outcome | Step shows | Run result | What happens next |
| --- | --- | --- | --- |
| Every plugin succeeded | `SUCCESS` | pass | Continues |
| Some succeeded, some did not | `WARNINGS` | **fail** | Continues with the survivors; the step names the plugins that failed |
| None succeeded | `FAILURE` | **fail** | Stops — there is nothing left to install or test |

The partial case is a warning on the step so you can open it and see which plugin failed, but `flunkOnWarnings` still fails the run: a partly working build is never reported green.

The build step takes each plugin's outcome from the summary `run.cmake` prints once it has tried them all, not from cmake's exit code, which only says whether anything failed:

```text
-- FOUNDRY-RESULT: PASS <plugin> <package file>...
-- FOUNDRY-RESULT: FAIL <plugin> <configure|build|package> <reason>
-- FOUNDRY-SUMMARY: <failed> of <total> plugins failed
```

A requested plugin that the summary leaves out counts as failed, and a run that never gets as far as the summary fails outright. The step's own summary names each failed plugin and the stage it failed at. The outcome is also kept in build properties: `built_plugins` and `failed_plugins`, space-separated, and `plugin_packages`, the package files each built plugin produced.

`run.cmake` runs as many make jobs as the builder's `jobs` in `master-migration/master.cfg` (through `CMAKE_BUILD_PARALLEL_LEVEL`), which is 1 for every Foundry builder. Left to itself it would use every core, on a worker that runs several of these builds at once.

Each stage narrows the list it hands to the next — requested, then built, then installed. MTR only runs suites belonging to plugins that installed, because a suite MariaDB cannot find aborts the entire test run. With a single plugin in scope, the common case for a pull request, any failure is simply a failure.

## Configured vs. discovered

`foundry.yaml` is the one place to adjust Foundry. It holds:

- the Foundry repository and its default branch;
- where server packages come from (the CI and mirror URLs);
- the dispatcher's builder name and image;
- per package family (rpm, deb, bintar): the repo file, mirror path, and the packages installed to build and to test;
- the OS × architecture matrix, named after the server builders, with each target's quay worker image and upstream base image;
- the supported MariaDB versions, and which targets each one builds;
- who may press Force.

Discovered at run time:

- the plugins — every top-level directory in Foundry with a `CMakeLists.txt`;
- which plugins a pull request changed;
- which plugins built, and which of those installed;
- each plugin's MTR suite names, read off the built packages;
- the newest release on the mirrors for a MariaDB version.

Adding a plugin to Foundry therefore needs no change here. Adding an OS target or a MariaDB version does.

A MariaDB version's `targets` must only name platforms the mirrors actually publish for that version, since those differ per branch — 11.4 has no sles-15.7/16.0 or opensuse-16.0 repository, while 11.8 does.

A new platform gets its server builders, and so CI tarballs, well before a release puts it on the mirrors. Until then, list it under the version's `ci_only`. Those targets run only when Force picks a CI tarbuildnum for that version; mirror runs and pull requests skip them, and the dispatch plan says so. Once a release has put the platform on the mirrors, move it to `targets`.

## Saved packages

```text
/packages/foundry/<mariadb_version>-<tarbuildnum|mirror>/<plugin>/<foundry_revision>/<buildername>/
```

One directory per plugin, taken from that plugin's own `<plugin>.build/` rather than the workspace root, where `run.cmake` pools every plugin's packages together. Each directory also holds a `sha256sums.txt` for the packages saved in it, so a download can be checked with `sha256sum -c sha256sums.txt`.

MTR logs from a failed run are saved per run rather than per plugin, since one MTR invocation covers every plugin's suites:

```text
/packages/foundry/<mariadb_version>-<tarbuildnum|mirror>/<foundry_revision>/logs/<buildername>/
```

Pull request builds save no packages.

The dispatcher publishes the Foundry archive its package builds download, with a `sha256sums.txt`, one directory per dispatcher build. Pull requests publish it too, since their package builds need it; it is source only, as `tarball-docker` publishes for server pull requests.

```text
/packages/foundry/sources/<dispatcher build number>/foundry-<commit>.tar.gz
```

## Design decisions

- **Plugins are discovered, not listed.** Foundry already defines what a plugin is; duplicating that list here would make every new plugin a two-repository change, and the lists would drift.
- **The public mirrors are the default source.** A run should be possible without a fresh server CI build to point at. Choosing a `tarbuildnum` stays available for testing against an unreleased server.
- **MariaDB version is a property, not a builder.** Keeps the matrix one dimension smaller, and adding a version costs no new builders.
- **Best effort on build and install, strict on the result.** Engineers need every plugin's outcome from one run, not just the first failure — but a partly working run must never be reported green.
- **Pull requests are read-only.** A contributor's branch validates a change; it should not publish installable packages or pin CI builds.
- **Every step runs in the target's own distribution.** A plugin package is only meaningful on the distribution it was built for, which is what makes the install test real.
- **Packages are tested where nothing is preinstalled.** Installing into the plain base image, not the worker image, is what shows whether a package declares all of its dependencies.

## Where the code lives

| Path | What it holds |
| --- | --- |
| `foundry.yaml` | All Foundry settings: repository, sources, OS matrix, MariaDB versions, access |
| `builders.py` | Turns that config into builders and schedulers |
| `sources.py` | The three package-source choices and their property names |
| `../../sequences/foundry/` | Step sequences: `autobake.py` (deb/rpm/bintar), `dispatcher.py` |
| `../../../steps/commands/foundry.py` | The commands each step runs, and the build step that reads `run.cmake`'s summary |
| `../../../schedulers/foundry.py` | Force scheduler, pull request scheduler, Triggerables |

The force and pull request schedulers are loaded by `master-web`, which serves the UI and receives the GitHub webhook. The dispatcher and package builders run on `master-migration`, which owns their workers.
