import logging
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import URL_AUTH, URL_GRAPHQL, CLIENT_ID, URL_MAIL

_LOGGER = logging.getLogger(__name__)

class CanadaPostAPI:
    def __init__(self, hass, username, password):
        self.hass = hass
        self.username = username
        self.password = password

    async def get_tokens(self):
        payload = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "scope": "openid profile"
        }
        session = async_get_clientsession(self.hass)
        async with session.post(URL_AUTH, data=payload) as resp:
            resp.raise_for_status()
            tokens = await resp.json()            
            return tokens

    async def discover_topic_id(self, id_token):
        headers = {
            "Authorization": id_token, 
            "Content-Type": "application/json",
            "host": "b3n4knmt6famlj575e5pfn74lm.appsync-api.ca-central-1.amazonaws.com"
        }
        
        session = async_get_clientsession(self.hass)

        create_q = {
            "query": "mutation CreateTrackSyncItem($input: CreateTrackSyncItemInput!) { createTrackSyncItem(input: $input) { id owner createdAt ttl } }",
            "variables": {
                "input": {
                    "trackId": "1234567890123456",
                    "type": "DEFAULT",
                    "source": "USER"
                }
            }
        }
        
        try:
            async with session.post(URL_GRAPHQL, json=create_q, headers=headers) as resp:
                res_json = await resp.json()                
                data = res_json.get("data", {}).get("createTrackSyncItem")
                if not data:
                    _LOGGER.error("GraphQL error: %s", res_json.get("errors"))
                    return None

                topic_id = data["owner"]
                item_id = data["id"]

                update_q = {
                    "query": "mutation UpdateTrackSyncItem($input: UpdateTrackSyncItemInput!) { updateTrackSyncItem(input: $input) { id } }",
                    "variables": {
                        "input": {
                            "id": item_id,
                            "trackId": "1234567890123456",
                            "source": "USER",
                            "type": "DEFAULT",
                            "deleted": True,
                            "owner": topic_id,
                            "createdAt": data["createdAt"],
                            "ttl": data["ttl"]
                        }
                    }
                }
                await session.post(URL_GRAPHQL, json=update_q, headers=headers)
                
                return topic_id

        except Exception as e:
            _LOGGER.error("Error while fetching item id: %s", e)
            return None

    async def get_mail(self, full_token, topic_id, start_date=None):
        if start_date is None:
            from datetime import datetime
            start_date = datetime.now().strftime('%Y%m%d')

        url = URL_MAIL.format(topic_id=topic_id)
        params = {"startDate": start_date, "daySpan": "-7"}
        
        auth_header = f"Bearer {full_token}"
        
        headers = {
            "Authorization": auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/5.0.0-alpha.11",
            "Host": "1i5z3519d0.execute-api.ca-central-1.amazonaws.com"
        }
        
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    _LOGGER.error("API Error (%s): %s", resp.status, text)
                
                resp.raise_for_status()
                return await resp.json()
        except Exception as err:
            _LOGGER.error("Exception: %s", err)
            return None