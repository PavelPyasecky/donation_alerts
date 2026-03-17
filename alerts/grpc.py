import datetime

from google.protobuf.json_format import MessageToDict

from configs import config
from models.alert import AlertSettingsGroup
from protobuf.groups_pb2 import AlertSettingsGroupRetrieveRequest
from protobuf.groups_pb2_grpc import AlertSettingsGroupControllerStub
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


alert_settings_group_grpc_client = AlertSettingsGroupGRPCClient(config.GRPC_SERVER_URL)
