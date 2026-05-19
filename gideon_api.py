from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ai_api
import uvicorn
import threading
import os

app = FastAPI(title="Gideon API Service")

class ChatRequest(BaseModel):
    prompt: str
    model_id: str = "local_engine"

class VoiceRequest(BaseModel):
    audio_data: str  # Base64 encoded audio or path to file

@app.get("/status")
def get_status():
    return {"status": "online", "system": "Gideon", "engine": "Luna AI"}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        # Use the existing ai_api call
        response = ai_api.call_ai_api(request.prompt, model_id=request.model_id)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe")
async def transcribe(request: VoiceRequest):
    try:
        # In a full implementation, we would use:
        # import whisper
        # model = whisper.load_model("base")
        # result = model.transcribe(audio_path)
        # return {"text": result["text"]}
        
        # For the bridge validation:
        print(f"Gideon received audio data (length: {len(request.audio_data)})")
        return {"text": "Gideon, scan for metahumans."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def start_api():
    uvicorn.run(app, host="127.0.0.1", port=8008)

if __name__ == "__main__":
    print("Starting Gideon API Bridge on port 8008...")
    start_api()
