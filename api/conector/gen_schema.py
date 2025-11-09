#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Genera un schema_catalog.yaml a partir de una BD PostgreSQL.

Uso típico:
python gen_schema.py \
  --host 148.230.92.252 --port 5432 \
  --db agrodb --user agro --password "TU_PASS" --sslmode require \
  --schema public \
  --out /workspace/api/conector/schema_catalog.yaml
"""

import os
import argparse
import psycopg2
import psycopg2.extras
import yaml


def fetch(conn, q, args=()):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(q, args)
        return cur.fetchall()


def main():
    ap = argparse.ArgumentParser(description="Exporta el esquema de PostgreSQL a schema_catalog.yaml")
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=5432)
    ap.add_argument("--db", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--sslmode", default="require", help="disable|allow|prefer|require|verify-ca|verify-full")
    ap.add_argument("--schema", default=None, help="Filtrar por esquema (ej. public). Si se omite, exporta todos.")
    ap.add_argument("--out", default="schema_catalog.yaml")
    ap.add_argument("--limit_tables", type=int, default=0, help="0 = sin límite de tablas")
    ap.add_argument("--include_views", action="store_true", help="Incluir vistas además de tablas")
    args = ap.parse_args()

    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.db,
        user=args.user,
        password=args.password,
        sslmode=args.sslmode,
    )

    # 1) Esquemas
    schema_filter_ns = "AND n.nspname = %s" if args.schema else ""
    schemas = fetch(
        conn,
        f"""
        SELECT n.nspname AS schema
        FROM pg_namespace n
        WHERE n.nspname NOT IN ('pg_catalog','information_schema')
          AND n.nspname NOT LIKE 'pg_toast%%'
          {schema_filter_ns}
        ORDER BY 1;
        """,
        (args.schema,) if args.schema else (),
    )

    # 2) Tablas (y opcionalmente vistas)
    relkinds = ("'r'") if not args.include_views else ("'r','v'")
    schema_filter_cls = "AND n.nspname = %s" if args.schema else ""
    tables = fetch(
        conn,
        f"""
        SELECT n.nspname AS schema,
               c.relname  AS table,
               obj_description(c.oid, 'pg_class') AS description,
               c.relkind
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog','information_schema')
          AND n.nspname NOT LIKE 'pg_toast%%'
          AND c.relkind IN ({relkinds})
          {schema_filter_cls}
        ORDER BY n.nspname, c.relname;
        """,
        (args.schema,) if args.schema else (),
    )

    # 3) Columnas (¡sin %s dentro de format()! usamos quote_ident)
    schema_filter_cols = "AND c.table_schema = %s" if args.schema else ""
    cols = fetch(
        conn,
        f"""
        SELECT
            c.table_schema AS schema,
            c.table_name   AS table,
            c.column_name  AS name,
            c.data_type    AS type,
            col_description(
                (quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass::oid,
                c.ordinal_position
            ) AS description
        FROM information_schema.columns c
        WHERE c.table_schema NOT IN ('pg_catalog','information_schema')
          {schema_filter_cols}
        ORDER BY c.table_schema, c.table_name, c.ordinal_position;
        """,
        (args.schema,) if args.schema else (),
    )

    # 4) Armar mapa de columnas
    colmap = {}
    for r in cols:
        key = (r["schema"], r["table"])
        colmap.setdefault(key, []).append({
            "name": r["name"],
            "type": r["type"],
            **({"description": r["description"]} if r.get("description") else {}),
        })

    # 5) Construir estructura YAML final
    schema_nodes = []
    total_tables = 0
    limit = args.limit_tables if args.limit_tables and args.limit_tables > 0 else None

    for s in schemas:
        sname = s["schema"]
        tables_in_schema = []
        for t in tables:
            if t["schema"] != sname:
                continue
            if limit is not None and total_tables >= limit:
                break
            key = (t["schema"], t["table"])
            tables_in_schema.append({
                "name": t["table"],
                **({"description": t["description"]} if t.get("description") else {}),
                "columns": colmap.get(key, []),
            })
            total_tables += 1

        if tables_in_schema:
            schema_nodes.append({
                "name": sname,
                "tables": tables_in_schema,
            })

    out_obj = {
        "databases": [
            {
                "name": args.db,
                "schemas": schema_nodes,
            }
        ]
    }

    # 6) Guardar YAML
    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(out_obj, f, sort_keys=False, allow_unicode=True)

    print(f"[ok] Esquema guardado en {out_path} (schemas={len(schema_nodes)}, tablas={total_tables})")


if __name__ == "__main__":
    main()
