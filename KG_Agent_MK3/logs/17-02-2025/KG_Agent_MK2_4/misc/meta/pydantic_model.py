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
    source: InputSource  # Mandatory field
    target_classes: Optional[List[str]] = None
    all_classes: bool = False
    examples: Optional[ExamplesMode] = None  # Correct enum type
    # ... other fields ...

    @model_validator(mode='after')
    def validate_targets(self):
        if not self.all_classes and not self.target_classes and not self.shape_map_file:
            raise ValueError("Must specify targets")
        return self