import logging

import grpc

from google.protobuf.json_format import MessageToDict

from alerts.models import Campaign
from configs import config
from protobuf.campaigns_pb2 import GetByAuthorIDRequest
from protobuf.campaigns_pb2_grpc import CampaignServiceStub


class CampaignClient:
    def __init__(self):
        self.channel = grpc.aio.insecure_channel(config.GRPC_SERVER_URL)
        self.stub = CampaignServiceStub(self.channel)
    
    async def get_campaign_by_author_id(self, author_id: int) -> Campaign:
        try:
            stub = await self.stub.GetByAuthorID(GetByAuthorIDRequest(author_id=author_id))
            data = MessageToDict(
                stub,
                preserving_proto_field_name=True,
                including_default_value_fields=True
            )
            return Campaign(**data)
        except Exception as e:
            logging.error(f"GRPC error: {e}", exc_info=True)
