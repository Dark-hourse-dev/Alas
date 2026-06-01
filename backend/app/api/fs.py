from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from pathlib import Path

router = APIRouter(prefix="/api/fs", tags=["filesystem"])

# Safely restrict to workspace
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
# Assuming workspace is /home/himanshu-meena/workspace

class WriteRequest(BaseModel):
    content: str

def safe_path(rel_path: str) -> Path:
    target = (WORKSPACE_ROOT / rel_path).resolve()
    if not str(target).startswith(str(WORKSPACE_ROOT)):
        raise HTTPException(status_code=403, detail="Path traversal not allowed")
    return target

@router.get("/list")
async def list_dir(path: str = ""):
    try:
        target = safe_path(path)
        if not target.exists() or not target.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")
            
        items = []
        for item in target.iterdir():
            if item.name.startswith(".git") or item.name == "__pycache__":
                continue
            items.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "path": str(item.relative_to(WORKSPACE_ROOT))
            })
            
        # Sort directories first, then alphabetically
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"items": items, "current_path": path}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/read")
async def read_file(path: str):
    try:
        target = safe_path(path)
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content, "path": path}
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Cannot read binary files")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/raw")
async def raw_file(path: str):
    try:
        target = safe_path(path)
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(target)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/write")
async def write_file(path: str, req: WriteRequest):
    try:
        target = safe_path(path)
        with open(target, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"success": True, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
