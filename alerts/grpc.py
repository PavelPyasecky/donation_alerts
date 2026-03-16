import datetime
import grpc

from google.protobuf.json_format import MessageToDict

from alerts.models import AlertSetting, Campaign
from configs import config
from protobuf.campaigns_pb2 import GetByAuthorIDRequest, GetByIDAuthorIDRequest
from protobuf.campaigns_pb2_grpc import CampaignServiceStub
from protobuf.settings_pb2 import AlertSettingListRequest, AlertSettingRetrieveRequest
from protobuf.settings_pb2_grpc import AlertSettingControllerStub
from utils.grpc import handle_grpc_errors


class GRPCClient:
    def __init__(self):
        self.channel = grpc.aio.insecure_channel(config.GRPC_SERVER_URL)


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


class AlertSettingsGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = AlertSettingControllerStub(self.channel)

    @handle_grpc_errors
    async def get_alert_settings_list_by_author_id_filter_by_updated_at(
        self, author_id: int, group_id: int, updated_at: datetime.datetime
    ) -> list[AlertSetting]:
        stub = await self.stub.ListByGroupID(AlertSettingListRequest(author_id=author_id, group_id=group_id, updated_at=str(updated_at)))
        data = MessageToDict(stub, preserving_proto_field_name=True)
        return [AlertSetting(**obj) for obj in data.get("alert_settings", [])]


campaign_grpc_client = CampaignGRPCClient()
alert_settings_grpc_client = AlertSettingsGRPCClient()
