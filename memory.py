from collections import defaultdict

class ConversationMemory:
    def __init__(self):
        self.history = defaultdict(list)

    def add_message(self, user_id, role, content):
        self.history[user_id].append({"role": role, "content": content})

    def get_messages(self, user_id):
        return list(self.history[user_id])
