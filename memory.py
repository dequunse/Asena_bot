from collections import defaultdict

class ConversationMemory:
    def __init__(self, max_messages=20):
        self.history = defaultdict(list)
        self.max_messages = max_messages

    def add_message(self, user_id, role, content):
        self.history[user_id].append({"role": role, "content": content})
        
        # 20 mesaj limitini aşarsa en eski mesajları sil
        if len(self.history[user_id]) > self.max_messages:
            self.history[user_id] = self.history[user_id][-self.max_messages:]

    def get_messages(self, user_id):
        return list(self.history[user_id])
