"""Run the OneMoreRep web API; start both web processes with start_onemorerep.ps1."""
import uvicorn


if __name__ == "__main__":
    uvicorn.run("onemorerep.webapp:app", host="127.0.0.1", port=8000)
