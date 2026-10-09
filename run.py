
import uvicorn

from app.config import settings

if __name__ == "__main__":
    print(f"EstateDB starting on http://{settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run("app.main:app", host=settings.APP_HOST,
                port=settings.APP_PORT, reload=True)
