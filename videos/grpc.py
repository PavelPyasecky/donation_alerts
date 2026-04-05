import datetime

from google.protobuf.json_format import MessageToDict

from configs import config
from models.videos import Video, WidgetVideoSetting
from protobuf.widget_videos_pb2_grpc import VideosServiceStub
from protobuf.widget_videos_pb2 import ListWidgetVideosRequest, ListWidgetVideosResponse
from protobuf.donators_videos_pb2_grpc import DonatorsVideosServiceStub
from protobuf.donators_videos_pb2 import ListDonatorsVideosRequest, ListDonatorsVideosResponse
from widget_video_settings_pb2_grpc import WidgetVideoSettingsServiceStub
from widget_video_settings_pb2 import RetrieveWidgetVideoSettingsRequest, SetWidgetVideoVolumeRequest, WidgetVideoSettings
from utils.grpc import GRPCClient, handle_grpc_errors


class WidgetVideosGrpcClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = VideosServiceStub(self.channel)

    @handle_grpc_errors
    async def get_videos(self, author_id: int, updated_at: datetime.datetime) -> list[Video]:
        response = await self.stub.ListWidgetVideos(
            ListWidgetVideosRequest(author_id=author_id, updated_at=updated_at.isoformat())
        )
        data = MessageToDict(response, preserving_proto_field_name=True)
        return [Video(**video) for video in data.get("videos", [])]


class DonatorsVideosGrpcClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = DonatorsVideosServiceStub(self.channel)

    @handle_grpc_errors
    async def get_videos(self, author_id: int, updated_at: datetime.datetime) -> list[Video]:
        response = await self.stub.ListDonatorsVideos(
            ListDonatorsVideosRequest(author_id=author_id, updated_at=updated_at.isoformat())
        )
        data = MessageToDict(response, preserving_proto_field_name=True)
        return [Video(**video) for video in data.get("videos", [])]


class WidgetVideoSettingsGrpcClient(GRPCClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = WidgetVideoSettingsServiceStub(self.channel)

    @handle_grpc_errors
    async def get_video_settings(self, author_id: int, updated_at: datetime.datetime) -> WidgetVideoSetting:
        response = await self.stub.RetrieveWidgetVideoSettings(
            RetrieveWidgetVideoSettingsRequest(author_id=author_id, updated_at=updated_at.isoformat())
        )
        data = MessageToDict(response, preserving_proto_field_name=True)
        if not data:
            return None
        return WidgetVideoSetting(**data)

    @handle_grpc_errors
    async def set_volume(self, author_id: int, volume: int) -> WidgetVideoSetting:
        response = await self.stub.SetVolume(
            SetWidgetVideoVolumeRequest(author_id=author_id, volume=volume)
        )
        data = MessageToDict(response, preserving_proto_field_name=True)
        if not data:
            return None
        return WidgetVideoSetting(**data)


widget_videos_grpc_client = WidgetVideosGrpcClient(config.GRPC_SERVER_URL)
donators_videos_grpc_client = DonatorsVideosGrpcClient(config.GRPC_SERVER_URL)
widget_video_settings_grpc_client = WidgetVideoSettingsGrpcClient(config.GRPC_SERVER_URL)
