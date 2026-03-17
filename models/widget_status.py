from pydantic import BaseModel


class WidgetStatus(BaseModel):
    is_online: bool
