import datetime

from google.protobuf.json_format import MessageToDict

from configs import config
from models.donations import Donater
from models.settings import TopDonatersSettings
from protobuf.donations_pb2 import UnionByDonorNamesDonation, UnionByDonorNamesListRequest
from protobuf.donations_pb2_grpc import DonationServiceStub
from protobuf.top_donaters_pb2 import RetrieveTopDonatersSettingRequest
from utils.grpc import GRPCClient, handle_grpc_errors
from protobuf.top_donaters_pb2_grpc import TopDonatersSettingsServiceStub


class TopDonatersGRPCClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = TopDonatersSettingsServiceStub(self.channel)

    @handle_grpc_errors
    async def get_top_donaters_settings(self, author_id: int, setting_id: int) -> TopDonatersSettings:
        stub = await self.stub.RetrieveTopDonatersSetting(
            RetrieveTopDonatersSettingRequest(author_id=author_id, setting_id=setting_id)
        )
        data = MessageToDict(stub, preserving_proto_field_name=True)
        if not data:
            return None
        return TopDonatersSettings(**data)


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


top_donaters_grpc_client = TopDonatersGRPCClient(config.GRPC_SERVER_URL)
donations_grpc_client = DonationsGRPCClient(config.GRPC_SERVER_URL)
