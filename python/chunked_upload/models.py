from typing import List

import pydantic
import pydantic.alias_generators


class ApplicationModel(pydantic.BaseModel):
    """Base model for application-specific models with camel case alias generation."""

    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )


class Object(ApplicationModel):
    """An object in storage."""

    path: str
    n_bytes: int
    completed: bool = True
    finalizing: bool = False
    uploaded_chunks: int | None = None
    total_chunks: int | None = None


class ObjectList(ApplicationModel):
    """A list of objects in storage."""

    items: List[Object]
