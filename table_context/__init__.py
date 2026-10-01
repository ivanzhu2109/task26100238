"""HTML table context for voice navigation."""

from .api import compile_table, describe
from .model import Description, HeaderRef, Table
from .parser import TableNotFoundError, TableStructureError

__all__ = [
    "compile_table",
    "describe",
    "Description",
    "HeaderRef",
    "Table",
    "TableNotFoundError",
    "TableStructureError",
]
