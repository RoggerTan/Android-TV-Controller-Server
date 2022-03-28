import json
from os import path

class ConfigHelper:
    def __init__(self, dirPath):
        self.dirPath = dirPath
        self.initServerConf()

    def initServerConf(self):
        self.configs = {}
        with open(self.dirPath + "/server.json", "r") as f:
            self.configs["server"] = json.load(f)

    def read(self, configName = "server"):
        with open(path.join(self.dirPath, f"{configName}.json"), "r") as f:
                self.configs[configName] = json.load(f)
        return self.configs[configName]

configHelper = ConfigHelper("configs")
