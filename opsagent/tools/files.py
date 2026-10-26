"""File tools for OpsAgent - list files and read PDFs."""
import os
from pathlib import Path
import pdfplumber
from opsagent.tools.registry import tool
from opsagent.config import PROJECT_ROOT


@tool(
    name="file_list",
    description="List files in a directory. Returns file names, sizes and types. Use to discover invoice PDFs and other documents.",
    risk="read",
    parameters={
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Directory path to list (relative to project root or absolute)"},
            "pattern": {"type": "string", "description": "Optional glob pattern to filter files (e.g. '*.pdf')"}
        },
        "required": ["directory"]
    }
)
async def file_list(directory: str, pattern: str = "*") -> dict:
    try:
        dir_path = Path(directory)
        if not dir_path.is_absolute():
            dir_path = PROJECT_ROOT / directory

        if not dir_path.exists():
            return {"success": False, "error": f"Directory not found: {directory}"}
        if not dir_path.is_dir():
            return {"success": False, "error": f"Not a directory: {directory}"}

        files = []
        for f in sorted(dir_path.glob(pattern)):
            files.append({
                "name": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size if f.is_file() else 0,
                "is_directory": f.is_dir(),
            })

        return {"success": True, "directory": str(dir_path), "files": files[:50],
                "total": len(files)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="file_read_pdf",
    description="Read and extract text content from a PDF file. Use to extract invoice details like vendor name, amount, date, and invoice number.",
    risk="read",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to the PDF file to read"}
        },
        "required": ["file_path"]
    }
)
async def file_read_pdf(file_path: str) -> dict:
    try:
        path = Path(file_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / file_path

        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        if not path.suffix.lower() == '.pdf':
            return {"success": False, "error": f"Not a PDF file: {file_path}"}

        text_pages = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                text_pages.append({
                    "page_number": i + 1,
                    "text": page_text,
                })

        full_text = "\n\n".join(p['text'] for p in text_pages)

        # Truncate if too long
        if len(full_text) > 6000:
            full_text = full_text[:6000] + "\n... [content truncated]"

        return {
            "success": True,
            "file_path": str(path),
            "num_pages": len(text_pages),
            "text": full_text,
            "pages": text_pages,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
