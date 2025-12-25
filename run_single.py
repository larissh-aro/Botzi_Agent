import sys
import json
from supervisor_agent import SupervisorAgent
from interpreter_agent import InterpreterAgent
from executor_agent import ExecutorAgent
from tools_layer import ToolsLayer
from main import local_parse_multiple

def process(message: str):
    try:
        # provide the local deterministic parser used in main.py
        interpreter = InterpreterAgent(local_parse_multiple, enable_llm=True)
        executor = ExecutorAgent(ToolsLayer())

        # 1) interpret to see actions
        actions = interpreter.run(message)

        # if no actions, fall back to supervisor (which will return friendly guidance)
        if not actions:
            supervisor = SupervisorAgent(interpreter, executor)
            responses = supervisor.handle(message)
            return {"actions": None, "responses": responses}

        # 2) execute actions and collect logs
        logs = executor.run(actions)
        return {"actions": actions, "responses": logs}
    except Exception as e:
        return {"actions": None, "responses": [f"Error: {str(e)}"]}

if __name__ == '__main__':
    if len(sys.argv) < 2:
        # try read from stdin
        msg = sys.stdin.read().strip()
    else:
        msg = sys.argv[1]

    out = process(msg)
    print(json.dumps(out))
