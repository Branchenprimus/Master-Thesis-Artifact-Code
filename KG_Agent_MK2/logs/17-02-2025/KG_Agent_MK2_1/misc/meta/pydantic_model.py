from pydantic import BaseModel, Field, AnyHttpUrl, FilePath
from typing import Optional, List, Union
from enum import Enum

class InputSource(BaseModel):
    local_file: Optional[FilePath] = Field(None, description="Path to local RDF file")
    remote_url: Optional[AnyHttpUrl] = Field(None, description="URL of RDF resource")
    sparql_endpoint: Optional[AnyHttpUrl] = Field(None, description="SPARQL endpoint")
    raw_data: Optional[str] = Field(None, description="Raw RDF data")

    def model_post_init(self, __context):
        provided = [k for k,v in self.dict().items() if v is not None]
        if len(provided) > 1:
            raise ValueError(f"Multiple sources provided: {provided}")

class ExamplesMode(str, Enum):
    SHAPE = "SHAPE_EXAMPLES"
    CONSTRAINT = "CONSTRAINT_EXAMPLES"
    ALL = "ALL_EXAMPLES"

class ShexerConfig(BaseModel):
    source: InputSource
    target_classes: Optional[List[str]] = None
    all_classes: bool = False
    shape_map_file: Optional[FilePath] = None
    disable_comments: bool = False
    examples: Optional[ExamplesMode] = None
    remove_empty_shapes: bool = True
    class_property: str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    ignore_namespaces: Optional[List[str]] = None
    depth: int = Field(1, ge=1)

    @validator('target_classes', always=True)
    def validate_targets(cls, v, values):
        if not values.get('all_classes') and not v and not values.get('shape_map_file'):
            raise ValueError("Must specify target_classes, all_classes, or shape_map_file")
        return v