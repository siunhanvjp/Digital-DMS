from typing import Optional

from ninja.schema import Schema


class NewSynsetRequest(Schema):
    ontologyId: str

class UpdateNodeNameRequest(Schema):
    name: str
    
class NewEdgeRequest(Schema):
    from_id: str
    to_id: str

class OntologyGraphRequest(Schema):
    nodes: list[dict]
    edges: list[dict]
    ontologyId: str

class NewOntologyRequest(Schema):
    name: str
    ontologyId: str
    
class RenameOntologyRequest(Schema):
    ontologyName: str
    
class UpdateDefinitionRequest(Schema):
    definition: str
    ontologyId: str
    

class AddSenseRequest(Schema):
    label: str
    synsetId: str
    ontologyId: str
    
class AddEdgeRequest(Schema):
    from_id: str
    to_id: str
    ontologyId: str
    

class UpdateSenseLabel(Schema):
    ontologyId: str
    label: str