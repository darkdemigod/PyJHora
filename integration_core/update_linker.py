
from updater.update_checker import UpdateChecker
from updater.auto_updater import AutoUpdater

class UpdateLinker:
    def __init__(self):
        self.checker = UpdateChecker()
        self.updater = AutoUpdater()

    def run(self):
        status = self.checker.check()
        if status["update_available"]:
            self.updater.run()
        return status
