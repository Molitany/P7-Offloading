from datetime import datetime


class Colors:
    def __init__(self) -> None:
        self.RED = "\33[31m"
        self.GREEN = "\33[32m"
        self.BLUE = "\33[34m"
        self.GREENHIGH = "\33[92m"
        self.BLUEHIGH = "\33[94m"
        self.WHITE = "\33[97m"


class Logger:
    def __init__(self, file="log.txt") -> None:
        self.colors = Colors()
        self.file = file

    def truncate(self):
        with open(self.file, "w") as f:
            f.write("")

    def log_error(self, error):
        with open(self.file, "a") as f:
            f.write(
                f'{self.colors.RED}[{datetime.utcnow().isoformat(sep=" ", timespec="milliseconds")}] {error}{self.colors.WHITE}\n'
            )

    def log_message(self, message):
        with open(self.file, "a") as f:
            f.write(
                f'{self.colors.WHITE}[{datetime.utcnow().isoformat(sep=" ", timespec="milliseconds")}] {message}\n'
            )

    def log_colored_message(self, color, message):
        with open(self.file, "a") as f:
            f.write(
                f'{color}[{datetime.utcnow().isoformat(sep=" ", timespec="milliseconds")}] {message}{self.colors.WHITE}\n'
            )
