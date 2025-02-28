from pydantic import BaseModel, Field, AnyHttpUrl, FilePath, validator, model_validator
from typing import Optional, List
from enum import Enum

class InputSource(BaseModel):
    local_file: Optional[FilePath] = None
    remote_url: Optional[AnyHttpUrl] = None
    sparql_endpoint: Optional[AnyHttpUrl] = None
    raw_data: Optional[str] = None

    @model_validator(mode='after')
    def check_single_source(self):
        provided = [k for k,v in self.model_dump().items() if v is not None]
        if len(provided) != 1:
            raise ValueError(f"Exactly one source required. Got {len(provided)}")
        return self

class ExamplesMode(str, Enum):
    SHAPE = "SHAPE_EXAMPLES"
    CONSTRAINT = "CONSTRAINT_EXAMPLES"
    ALL = "ALL_EXAMPLES"

class ShexerConfig(BaseModel):
    source: InputSource
    target_classes: Optional[List[str]] = None
    all_classes: bool = False
    shape_map_file: Optional[FilePath] = Field(  # Added missing field
        None,
        description="Path to shape map file for custom groupings"
    )
    disable_comments: bool = False
    examples: Optional[ExamplesMode] = None
    remove_empty_shapes: bool = True
    class_property: str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    ignore_namespaces: Optional[List[str]] = None
    depth: int = Field(1, ge=1)

    @model_validator(mode='after')
    def validate_targets(self):
        if (
            not self.all_classes 
            and not self.target_classes 
            and not self.shape_map_file  # Now using correct field name
        ):
            raise ValueError(
                "Must specify either target_classes, all_classes, or shape_map_file"
            )
        return self