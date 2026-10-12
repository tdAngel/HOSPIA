"""Genera db/schema.sql (DDL de PostgreSQL) a partir de los modelos."""
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import Base

out = ["-- HOSPIA · esquema PostgreSQL (generado con backend/export_schema.py)\n"]
for t in Base.metadata.sorted_tables:
    out.append(str(CreateTable(t).compile(dialect=postgresql.dialect())).strip() + ";\n")
    for ix in sorted(t.indexes, key=lambda i: i.name):
        out.append(str(CreateIndex(ix).compile(dialect=postgresql.dialect())).strip() + ";\n")
open("../db/schema.sql", "w", encoding="utf-8").write("\n".join(out))
print("db/schema.sql generado")
