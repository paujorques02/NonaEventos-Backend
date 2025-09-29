from google.cloud import firestore

class ConversationStore:
    def __init__(self, project_id):
        self.db = firestore.Client(project=project_id)

    def save_conversation(self, user_id, messages):
        conversation_ref = self.db.collection('conversations').document(user_id)
        conversation_ref.set({
            'messages': messages
        })

    def get_conversation(self, user_id):
        conversation_ref = self.db.collection('conversations').document(user_id)
        conversation = conversation_ref.get()
        if conversation.exists:
            return conversation.to_dict().get('messages', [])
        return []