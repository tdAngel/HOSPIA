from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import engine
from .models import Base
from .routers import auth, catalogo, citas, disponibilidad, pacientes


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="HOSPIA API", version="0.2.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """Convierte los errores de validación a mensajes en español, por campo."""
    errores = {}
    for e in exc.errors():
        campo = str(e["loc"][-1]) if len(e["loc"]) > 1 else "body"
        msg = e["msg"]
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        elif e["type"] == "missing":
            msg = "Este campo es obligatorio."
        elif "email" in msg.lower():
            msg = "Correo electrónico inválido."
        elif "date" in e["type"]:
            msg = "Fecha inválida (formato AAAA-MM-DD)."
        elif e["type"] == "bool_parsing":
            msg = "Valor inválido."
        errores.setdefault(campo, msg)
    return JSONResponse(status_code=422, content={"detail": "Revisa los datos capturados.", "errores": errores})


for r in (auth, catalogo, disponibilidad, pacientes, citas):
    app.include_router(r.router)


@app.get("/api/health", tags=["Sistema"])
def health():
    return {"estado": "ok"}
