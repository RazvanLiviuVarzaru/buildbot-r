class WorkerBase:
    def __init__(self, name: str, properties: dict[str, str | int | bool]):
        self.name = name
        self.properties = properties

    def __str__(self):
        return self.name
