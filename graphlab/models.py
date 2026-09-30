"""Bounded inputs for a local, undirected weighted graph laboratory."""
import csv
import io
import math
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_NODES = 1000
MAX_EDGES = 5000
MAX_UPLOAD = 1_000_000

class Edge(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source: str = Field(min_length=1, max_length=64)
    target: str = Field(min_length=1, max_length=64)
    weight: float = Field(default=1, ge=0, le=1e9, allow_inf_nan=False)

    @field_validator('source', 'target')
    @classmethod
    def clean_label(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError('Vertex labels must be nonempty and contain no control characters.')
        return value

class Graph(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nodes: list[str] = Field(default_factory=list, max_length=MAX_NODES)
    edges: list[Edge] = Field(default_factory=list, max_length=MAX_EDGES)

    @model_validator(mode='after')
    def validate_graph(self):
        labels = []
        for node in self.nodes:
            label = Edge(source=node, target=node).source
            if label in labels:
                raise ValueError(f'Duplicate vertex label: {label}')
            labels.append(label)
        seen = set()
        for edge in self.edges:
            if edge.source == edge.target:
                raise ValueError(f'Self-loop at {edge.source}; use a simple undirected graph.')
            key = tuple(sorted((edge.source, edge.target)))
            if key in seen:
                raise ValueError(f'Duplicate undirected edge: {edge.source} — {edge.target}')
            seen.add(key)
            for node in (edge.source, edge.target):
                if node not in labels:
                    labels.append(node)
        if not labels or len(labels) > MAX_NODES:
            raise ValueError(f'A graph needs 1–{MAX_NODES} vertices.')
        self.nodes = labels
        return self

class Parameters(BaseModel):
    model_config = ConfigDict(extra='forbid')
    partitions: int = Field(default=2, ge=2, le=8)
    balance_lambda: float = Field(default=1.1, ge=0, le=20, allow_inf_nan=False)
    capacity: bool = False
    seed: int = Field(default=42, ge=0, le=2**31-1)

class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    graph: Graph
    parameters: Parameters = Field(default_factory=Parameters)

class PathRequest(BaseModel):
    graph: Graph
    source: str
    target: str
    hops: int = Field(default=3, ge=0, le=6)

class BenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    family: str = 'hub'
    sizes: list[int] = Field(default_factory=lambda: [16, 64, 128, 256], min_length=1, max_length=5)
    repeats: int = Field(default=3, ge=1, le=5)
    parameters: Parameters = Field(default_factory=Parameters)

    @field_validator('sizes')
    @classmethod
    def valid_sizes(cls, values):
        if any(n < 8 or n > 512 for n in values) or len(set(values)) != len(values):
            raise ValueError('Choose unique benchmark sizes between 8 and 512.')
        return sorted(values)

    @field_validator('family')
    @classmethod
    def valid_family(cls, value):
        if value not in ('hub', 'random', 'grid', 'disconnected'):
            raise ValueError('Family must be hub, random, grid or disconnected.')
        return value


def parse_csv(data: bytes) -> Graph:
    if len(data) > MAX_UPLOAD:
        raise ValueError('CSV is too large. Maximum upload size: 1 MB.')
    try:
        decoded = data.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('Save the CSV as UTF-8 and try again.') from exc
    reader = csv.DictReader(io.StringIO(decoded), strict=True)
    if reader.fieldnames != ['source', 'target', 'weight']:
        raise ValueError('The CSV header must be exactly: source,target,weight')
    edges = []
    seen = set()
    try:
        for row in reader:
            line = reader.line_num
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'Line {line}: expected three columns.')
            try:
                edge = Edge(**row)
            except ValueError as exc:
                raise ValueError(f'Line {line}: use nonempty vertex labels and a finite weight from 0 to 1,000,000,000.') from exc
            key = tuple(sorted((edge.source, edge.target)))
            if edge.source == edge.target or key in seen:
                raise ValueError(f'Line {line}: self-loops and duplicate undirected edges are not supported.')
            seen.add(key)
            edges.append(edge)
            if len(edges) > MAX_EDGES:
                raise ValueError(f'Maximum {MAX_EDGES} edges per graph.')
    except csv.Error as exc:
        raise ValueError(f'Invalid CSV near line {reader.line_num}: {exc}') from exc
    if not edges:
        raise ValueError('The CSV needs at least one edge below the header.')
    return Graph(edges=edges)
