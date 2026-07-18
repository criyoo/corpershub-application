import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.chat.models import Conversation


class ConversationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        if not await self._is_allowed():
            await self.close(code=4003)
            return
        self.group_name = f"conversation_{self.conversation_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        payload = json.loads(text_data)
        if payload.get("type") == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat.typing",
                    "payload": {
                        "conversation_id": self.conversation_id,
                        "sender_id": str(self.user.id),
                    },
                },
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "message", **event["message"]}))

    async def chat_typing(self, event):
        await self.send(text_data=json.dumps({"type": "typing", **event["payload"]}))

    @database_sync_to_async
    def _is_allowed(self):
        conversation = Conversation.objects.filter(pk=self.conversation_id).first()
        if not conversation:
            return False
        if self.user.role == "admin":
            return True
        return self.user_id_in(conversation)

    def user_id_in(self, conversation):
        return self.user.id in {conversation.company_id, conversation.corper_id}
