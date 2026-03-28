from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import brands, cigars, prices, admin, auth, billing

app = FastAPI(title="Cigar Price API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,    prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(brands.router, prefix="/api/v1")
app.include_router(cigars.router, prefix="/api/v1")
app.include_router(prices.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
