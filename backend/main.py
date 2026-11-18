from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title='KBL GO', version='0.1.0', description='DAY 1 API validation scaffold')


class HealthResponse(BaseModel):
    status: str


@app.get('/api/health', response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status='ok')
