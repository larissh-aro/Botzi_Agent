# supervisor_agent.py

class SupervisorAgent:
    def __init__(self, interpreter, executor):
        self.interpreter = interpreter
        self.executor = executor

    def handle(self, text: str):
        tl = text.lower().strip()

        # Friendly greetings handled quickly
        if tl in ("hi", "hello", "hey", "yo", "hii", "hiii"):
            return ["Hello! How can I help you today? 🙂"]

        # Interpret (LLM + fallback)
        actions = self.interpreter.run(text)

        if not actions:
            return [
                "I couldn't understand that. Try:",
                "• add note shopping",
                "• update shopping content to 'buy eggs'",
                "• show notes"
            ]

        # Basic validation: drop invalid actions
        valid = []
        for a in actions:
            act = a.get("action")
            if not act:
                continue
            # update/delete must have identifier
            if act in ("update", "delete", "show_one", "pin", "unpin", "archive", "unarchive",
                       "add_label", "remove_label", "add_check", "check_item") and not a.get("identifier"):
                # skip invalid
                continue
            valid.append(a)

        if not valid:
            return ["Your request seems incomplete or unclear."]

        # Execute actions and return results
        return self.executor.run(valid)
