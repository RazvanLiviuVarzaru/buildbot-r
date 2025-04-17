from collections import defaultdict

from buildbot.plugins import worker
from configuration.workers.base import WorkerBase


class WorkerPool:
    def __init__(self):
        self.workers = defaultdict(list)
        self.instances = []

    def add(self, arch, worker):
        self.workers[arch].append(worker.name)
        self.instances.append(worker.instance)

    def get_workers_for_arch(self, arch, filter_fn=None):
        result = list(filter(filter_fn, self.workers[arch]))
        if not result:
            raise ValueError(f"No workers found for architecture: {arch}")
        return result


class NonLatent(WorkerBase):
    def __init__(self, name, config, total_jobs, max_builds=999):
        self.instance = None
        self.config = config
        self.max_builds = max_builds
        self.total_jobs = total_jobs
        super().__init__(name, properties={"total_jobs": total_jobs})
        self.__define()

    def __define(self):
        self.instance = worker.Worker(
            self.name,
            password=self._get_password(),
            max_builds=self.max_builds,
            properties=self.properties,
        )

    def _get_password(self):
        return self.config["private"]["worker_pass"][self.name]
