import asyncio
import httpx
from uuid import uuid4
from typing import Any
import rich

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
)


async def main():
    PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json' # NOQA F841
    EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard' # NOQA F841
    
    base_url = 'http://127.0.0.1:8000'

    async with httpx.AsyncClient() as httpx_client:
        httpx_client.timeout = 20000
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )
        
        _public_card = (
            await resolver.get_agent_card()
        )
        
        client = A2AClient(
            httpx_client=httpx_client, agent_card=_public_card
        )

        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'Whats a color like red?'}
                ],
                'messageId': uuid4().hex,
            },
        }
        
        request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )
        response = await client.send_message(request)
        
        rich.print(response.root.result.status.message.parts[0].root.text)
        

if __name__ == "__main__":
    asyncio.run(main())