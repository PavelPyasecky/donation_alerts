import grpc

from google.protobuf.json_format import MessageToDict, MessageToJson

from alerts.models import Campaign
from configs import config
from protobuf.campaigns_pb2 import GetByAuthorIDRequest, GetByIDAuthorIDRequest
from protobuf.campaigns_pb2_grpc import CampaignServiceStub
from utils.grpc import handle_grpc_errors


class CampaignGRPCClient:
    def __init__(self):
        self.channel = grpc.aio.insecure_channel(config.GRPC_SERVER_URL)
        self.stub = CampaignServiceStub(self.channel)

    @handle_grpc_errors
    async def get_campaign_by_id_author_id(self, author_id: int, campaign_id: int) -> Campaign:
        stub = await self.stub.GetByIDAuthorID(GetByIDAuthorIDRequest(author_id=author_id, campaign_id=campaign_id))
        data = MessageToDict(
            stub,
            preserving_proto_field_name=True,
        )
        return Campaign(**data, author_id=author_id)

    @handle_grpc_errors
    async def get_campaigns_list_by_author_id(self, author_id: int) -> list[Campaign]:
        stub = await self.stub.ListByAuthorID(GetByAuthorIDRequest(author_id=author_id))
        data = MessageToDict(stub, preserving_proto_field_name=True)
        return [Campaign(**obj, author_id=author_id) for obj in data]


campaign_grpc_client = CampaignGRPCClient()
