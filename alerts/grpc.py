import datetime

from google.protobuf.json_format import MessageToDict

from configs import config
from models.alert import Alert, AlertSettingsGroup, AlertSetting, BanWord
from models.settings import ModerationSettings
from protobuf.ban_words_pb2 import RetrieveBanWordsRequest
from protobuf.ban_words_pb2_grpc import BanWordsServiceStub
from protobuf.moderation_settings_pb2 import RetrieveModerationSettingRequest
from protobuf.moderation_settings_pb2_grpc import ModerationSettingsServiceStub
from protobuf.settings_pb2 import GetSettingRequest
from protobuf.settings_pb2_grpc import SettingsServiceStub
from protobuf.groups_pb2 import AlertSettingsGroupRetrieveRequest, AlertSettingsGroupsListByAuthorIdRequest
from protobuf.groups_pb2_grpc import AlertSettingsGroupControllerStub
from protobuf.pending_donations_pb2 import GetPendingDonationsRequest
from protobuf.pending_donations_pb2_grpc import PendingDonationsServiceStub
from utils.grpc import GRPCClient, handle_grpc_errors


class AlertSettingsGroupGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = AlertSettingsGroupControllerStub(self.channel)

    @handle_grpc_errors
    async def get_alert_settings_group_filter_updated_at(
        self, author_id: int, group_id: int, updated_at: datetime.datetime
    ) -> AlertSettingsGroup:
        stub = await self.stub.Retrieve(
            AlertSettingsGroupRetrieveRequest(author_id=author_id, group_id=group_id, updated_at=str(updated_at))
        )
        data = MessageToDict(stub, preserving_proto_field_name=True)
        if not data:
            return None
        return AlertSettingsGroup(**data)

    @handle_grpc_errors
    async def get_alert_settings_groups(
        self, author_id: int, group_ids: list[int], updated_at: datetime.datetime
    ) -> list[AlertSettingsGroup]:
        if not group_ids:
            return []
        stub = await self.stub.ListByIds(
            AlertSettingsGroupsListByAuthorIdRequest(
                author_id=author_id, group_ids=group_ids, updated_at=str(updated_at)
            )
        )
        data = MessageToDict(stub, preserving_proto_field_name=True)
        if not data:
            return []
        return [AlertSettingsGroup(**obj) for obj in data.get("groups", [])]


class AlertSettingsGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = SettingsServiceStub(self.channel)

    @handle_grpc_errors
    async def get_alert_settings(self, author_id: int, setting_id: int) -> AlertSetting:
        stub = await self.stub.GetSettingByAuthorIdAndSettingId(
            GetSettingRequest(author_id=author_id, setting_id=setting_id)
        )
        data = MessageToDict(stub, preserving_proto_field_name=True)
        if not data:
            return None
        return AlertSetting(**data)


class AlertSGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = PendingDonationsServiceStub(self.channel)

    @handle_grpc_errors
    async def get_pending_donations(self, author_id: int, limit: int = 0) -> list[Alert]:
        stub = await self.stub.GetPendingDonations(GetPendingDonationsRequest(author_id=author_id))
        data = MessageToDict(stub, preserving_proto_field_name=True)
        return [Alert(**obj) for obj in data.get("pending_donations", [])]


class BanWordsGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = BanWordsServiceStub(self.channel)

    @handle_grpc_errors
    async def get_ban_words(self, author_id: int, updated_at: datetime.datetime) -> BanWord | None:
        stub = await self.stub.RetrieveBanWords(
            RetrieveBanWordsRequest(author_id=author_id, updated_at=str(updated_at))
        )
        data = MessageToDict(stub, preserving_proto_field_name=True)
        if not data:
            return None
        return BanWord(**data)


class ModerationSettingsGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = ModerationSettingsServiceStub(self.channel)

    @handle_grpc_errors
    async def get_moderation_settings(self, author_id: int, updated_at: datetime.datetime) -> ModerationSettings:
        stub = await self.stub.RetrieveModerationSetting(
            RetrieveModerationSettingRequest(author_id=author_id, updated_at=str(updated_at))
        )
        data = MessageToDict(stub, preserving_proto_field_name=True)
        if not data:
            return None
        return ModerationSettings(**data)


alert_settings_group_grpc_client = AlertSettingsGroupGRPCClient(config.GRPC_SERVER_URL)
alert_settings_grpc_client = AlertSettingsGRPCClient(config.GRPC_SERVER_URL)
alerts_grpc_client = AlertSGRPCClient(config.GRPC_SERVER_URL)
ban_words_grpc_client = BanWordsGRPCClient(config.GRPC_SERVER_URL)
moderation_settings_grpc_client = ModerationSettingsGRPCClient(config.GRPC_SERVER_URL)
