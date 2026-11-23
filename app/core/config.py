"""Application constraints on top of the installed fastbase configuration."""
from fastbase.settings import BaseAppSettings
from pydantic import model_validator


class AppSettings(BaseAppSettings):
    @model_validator(mode="after")
    def validate_stack(self):
        if set(self.integrations_list) != {"core", "event-infra"}:
            raise ValueError("This application requires core,event-infra integrations")
        if self.workers != 1:
            raise ValueError("Schedule locking requires FAT_WORKERS=1")
        return self
