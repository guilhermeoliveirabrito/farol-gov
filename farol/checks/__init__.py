from dataclasses import dataclass

PASS = "pass"
WARN = "warn"
FAIL = "fail"
ERROR = "error"


@dataclass
class Resultado:
    check: str
    status: str
    detalhe: str = ""

    def to_dict(self):
        return {"check": self.check, "status": self.status, "detalhe": self.detalhe}
