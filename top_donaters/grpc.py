import datetime

from google.protobuf.json_format import MessageToDict

from configs import config
from models.donations import Donater, Donation
from models.settings import StatisticWidgetSettings
from protobuf.donations_pb2 import LastDonationsListRequest, UnionByDonorNamesDonation, UnionByDonorNamesListRequest
from protobuf.donations_pb2_grpc import DonationServiceStub
from protobuf.top_donaters_pb2 import RetrieveStatisticWidgetSettingsRequest
from utils.grpc import GRPCClient, handle_grpc_errors
from protobuf.top_donaters_pb2_grpc import StatisticWidgetSettingsServiceStub


class TopDonatersGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = StatisticWidgetSettingsServiceStub(self.channel)

    @handle_grpc_errors
    async def get_statistic_widget_settings(self, author_id: int, setting_id: int) -> StatisticWidgetSettings:
        response = await self.stub.RetrieveStatisticWidgetSettings(
            RetrieveStatisticWidgetSettingsRequest(author_id=author_id, setting_id=setting_id)
        )
        data = MessageToDict(response, preserving_proto_field_name=True)
        if not data:
            return None
        return StatisticWidgetSettings(**data)


class DonationsGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = DonationServiceStub(self.channel)

    @handle_grpc_errors
    async def get_union_by_donor_names_list(
        self, author_id: int, start_time: datetime.datetime, end_time: datetime.datetime, limit: int
    ) -> list[Donater]:
        stub = await self.stub.UnionByDonorNamesList(
            UnionByDonorNamesListRequest(author_id=author_id, start_time=str(start_time), end_time=str(end_time), limit=limit)
        )
        data = MessageToDict(stub, preserving_proto_field_name=True)
        if not data:
            return []
        return [Donater(**obj) for obj in data.get("union_by_donor_names_donations", [])]

    @handle_grpc_errors
    async def get_last_donations_list(self, author_id: int, limit: int) -> list[Donation]:
        stub = await self.stub.LastDonationsList(
            LastDonationsListRequest(author_id=author_id, limit=limit)
        )
        data = MessageToDict(stub, preserving_proto_field_name=True)
        if not data:
            return []
        return [Donation(**obj) for obj in data.get("last_donations", [])]


top_donaters_grpc_client = TopDonatersGRPCClient(config.GRPC_SERVER_URL)
donations_grpc_client = DonationsGRPCClient(config.GRPC_SERVER_URL)
