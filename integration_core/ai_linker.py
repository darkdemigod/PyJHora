
from ai.interpretation_engine import AIInterpretationEngine

class AILinker:
    def __init__(self):
        self.engine = AIInterpretationEngine()

    def interpret(self, chart):
        return self.engine.interpret(chart)
