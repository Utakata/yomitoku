from importlib.metadata import version

from .document_analyzer import DocumentAnalyzer
from .layout_analyzer import LayoutAnalyzer
from .layout_parser import LayoutParser
from .ocr import OCR
from .table_structure_recognizer import TableStructureRecognizer
from .text_detector import TextDetector
from .text_recognizer import TextRecognizer

# DSD module (Document Structure Deconstructor)
try:
    from . import dsd
    from .dsd.orchestrator import DSDOrchestrator
    DSD_AVAILABLE = True
except ImportError as e:
    DSD_AVAILABLE = False
    dsd = None

__all__ = [
    "OCR",
    "LayoutParser",
    "TableStructureRecognizer",
    "TextDetector",
    "TextRecognizer",
    "LayoutAnalyzer",
    "DocumentAnalyzer",
]

# Add DSD exports if available
if DSD_AVAILABLE:
    __all__.extend([
        "dsd",
        "DSDOrchestrator",
    ])

__version__ = version(__package__)
