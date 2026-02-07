import sys
import traceback

try:
    print("Starting MDO app...", flush=True)
    import uvicorn
    from main import app
    print("App imported successfully", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)
except Exception as e:
    print(f"STARTUP ERROR: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
