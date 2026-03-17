from google.protobuf.json_format import MessageToDict

from configs import config
from models.campaign import Campaign
from protobuf.campaigns_pb2 import GetByAuthorIDRequest, GetByIDAuthorIDRequest
from protobuf.campaigns_pb2_grpc import CampaignServiceStub
from utils.grpc import GRPCClient, handle_grpc_errors


class CampaignGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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


campaign_grpc_client = CampaignGRPCClient(config.GRPC_SERVER_URL)
