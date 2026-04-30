from fastapi import FastAPI, Request
import uvicorn
from typing import Dict, Any

app = FastAPI(title="TrafficFlow API Server")

# In-memory storage for the latest simulation data
latest_data: Dict[str, Any] = {}

@app.get("/data")
async def get_data():
    """Returns the latest traffic simulation data."""
    return latest_data

@app.post("/update")
async def update_data(request: Request):
    """Updates the in-memory simulation data."""
    global latest_data
    try:
        data = await request.json()
        latest_data = data
        return {"status": "success", "message": "Data updated successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("Starting API server on http://127.0.0.1:9000")
    uvicorn.run(app, host="127.0.0.1", port=9000)
