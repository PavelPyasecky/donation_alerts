import datetime
import grpc

from google.protobuf.json_format import MessageToDict

from alerts.models import AlertSetting, AlertSettingsGroup, Campaign
from configs import config
from protobuf.campaigns_pb2 import GetByAuthorIDRequest, GetByIDAuthorIDRequest
from protobuf.campaigns_pb2_grpc import CampaignServiceStub
from protobuf.groups_pb2 import AlertSettingsGroupRetrieveRequest
from protobuf.groups_pb2_grpc import AlertSettingsGroupControllerStub
from utils.grpc import handle_grpc_errors


class GRPCClient:
    def __init__(self):
        self.channel = grpc.aio.insecure_channel(config.GRPC_SERVER_URL)


class CampaignGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = CampaignServiceStub(self.channel)

    @handle_grpc_errors
    async def get_campaign_by_id_author_id(
        self, author_id: int, campaign_id: int
    ) -> Campaign:
        stub = await self.stub.GetByIDAuthorID(
            GetByIDAuthorIDRequest(author_id=author_id, campaign_id=campaign_id)
        )
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


class AlertSettingsGroupGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = AlertSettingsGroupControllerStub(self.channel)

    @handle_grpc_errors
    async def get_alert_settings_group_filter_updated_at(
        self, author_id: int, group_id: int, updated_at: datetime.datetime
    ) -> AlertSettingsGroup:
        stub = await self.stub.Retrieve(
            AlertSettingsGroupRetrieveRequest(
                author_id=author_id, group_id=group_id, updated_at=str(updated_at)
            )
        )
        data = MessageToDict(stub, preserving_proto_field_name=True)
        if not data:
            return None
        return AlertSettingsGroup(**data)


campaign_grpc_client = CampaignGRPCClient()
alert_settings_group_grpc_client = AlertSettingsGroupGRPCClient()
