# executor_agent.py

class ExecutorAgent:
    def __init__(self, tools_layer):
        self.tools = tools_layer

    def run(self, actions):
        # re-use your existing execute_actions function in main.py
        from main import execute_actions
        return execute_actions(actions)
