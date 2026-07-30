"""Pydantic schemas for the user_preferences API."""


from pydantic import BaseModel, Field


class UserPreferenceItem(BaseModel):
    scope: str = Field(min_length=1, max_length=64)
    key: str = Field(min_length=1, max_length=64)
    # value is a free-form JSON string; the client serializes.
    # Field length is generous — column_visibility JSON is short,
    # saved_views array may be larger.
    value: str = Field(default="null", max_length=65536)


class UserPreferenceList(BaseModel):
    items: list[UserPreferenceItem]
