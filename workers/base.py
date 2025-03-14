from abc import abstractmethod


class WorkerBase: # <1>
    def __init__(self, name, properties):
        self.name = name
        self.properties = properties

    def __str__(self):
        return self.name
