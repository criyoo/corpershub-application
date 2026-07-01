import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.urls import re_path

from apps.chat.consumers import ConversationConsumer


class CommunityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.topic_id = self.scope["url_route"]["kwargs"]["topic_id"]

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        if self.user.role != "corper":
            await self.close(code=4002)
            return

        self.group_name = f"community_{self.topic_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            payload = json.loads(text_data)
            if payload.get("type") == "typing":
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "community.typing",
                        "payload": {
                            "topic_id": self.topic_id,
                            "sender_id": str(self.user.id),
                        },
                    },
                )

    async def community_message(self, event):
        await self.send(text_data=json.dumps({"type": "message", **event["message"]}))

    async def community_typing(self, event):
        await self.send(text_data=json.dumps({"type": "typing", **event["payload"]}))


websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<conversation_id>[0-9a-f-]+)/$", ConversationConsumer.as_asgi()),
    re_path(r"ws/community/(?P<topic_id>[\w-]+)/$", CommunityConsumer.as_asgi()),
]