#!/bin/bash
# test_system.sh - Script para probar el sistema completo

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Testing Sistema SQLCoder + NLG"
echo "=================================="
echo ""

# 1. Verificar que los servicios estén corriendo
echo "1️Verificando servicios..."

check_service() {
    local name=$1
    local url=$2
    
    if curl -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name está corriendo"
        return 0
    else
        echo -e "${RED}✗${NC} $name NO está corriendo en $url"
        return 1
    fi
}

check_service "SQLCoder" "http://127.0.0.1:8011/health"
sqlcoder_ok=$?

check_service "NLG" "http://127.0.0.1:8002/health"
nlg_ok=$?

check_service "Conector" "http://127.0.0.1:8000/health"
connector_ok=$?

echo ""

if [ $sqlcoder_ok -ne 0 ] || [ $nlg_ok -ne 0 ] || [ $connector_ok -ne 0 ]; then
    echo -e "${RED}Algunos servicios no están corriendo. Inícialos primero.${NC}"
    echo ""
    echo "Ejecuta en terminales separadas:"
    echo "  Terminal 1: cd /workspace/sqlcoder_7b_2 && uvicorn app_sqlcoder:app --host 0.0.0.0 --port 8001"
    echo "  Terminal 2: cd /workspace/GPT && uvicorn app_gpt:app --host 0.0.0.0 --port 8002"
    echo "  Terminal 3: cd /workspace/conector && uvicorn app_connector:app --host 0.0.0.0 --port 8000"
    exit 1
fi

# 2. Verificar variables de entorno
echo "2️⃣ Verificando configuración..."

if [ -z "$PG_HOST" ]; then
    echo -e "${YELLOW}⚠${NC} PG_HOST no configurado"
else
    echo -e "${GREEN}✓${NC} PG_HOST configurado"
fi

if [ -z "$PG_DB" ]; then
    echo -e "${YELLOW}⚠${NC} PG_DB no configurado"
else
    echo -e "${GREEN}✓${NC} PG_DB configurado"
fi

echo ""

# 3. Hacer pruebas de consultas
echo "3️⃣ Ejecutando pruebas de consultas..."
echo ""

test_query() {
    local num=$1
    local question=$2
    local expected_type=$3
    
    echo -e "${YELLOW}Prueba $num:${NC} $question"
    
    response=$(curl -s -X POST http://127.0.0.1:8000/ask \
        -H "Content-Type: application/json" \
        -d "{\"question\":\"$question\",\"lang\":\"es\"}")
    
    # Verificar si hay error
    if echo "$response" | jq -e '.error' > /dev/null 2>&1; then
        error_msg=$(echo "$response" | jq -r '.error')
        echo -e "${RED}  ✗ ERROR:${NC} $error_msg"
        echo "  SQL generado:" $(echo "$response" | jq -r '.sql // "N/A"')
        return 1
    fi
    
    # Verificar si hay respuesta
    if echo "$response" | jq -e '.answer' > /dev/null 2>&1; then
        answer=$(echo "$response" | jq -r '.answer' | head -c 100)
        rows=$(echo "$response" | jq -r '.rows | length // 0')
        sql=$(echo "$response" | jq -r '.sql' | tr '\n' ' ')
        
        echo -e "${GREEN}  ✓ ÉXITO${NC}"
        echo "  SQL: $sql"
        echo "  Filas: $rows"
        echo "  Respuesta: $answer..."
        return 0
    fi
    
    echo -e "${RED}  ✗ Respuesta inesperada${NC}"
    echo "$response" | jq '.'
    return 1
}

# Contadores
total=0
passed=0

# Test 1: Conteo simple
total=$((total + 1))
test_query 1 "¿Cuántos compradores hay?" "count" && passed=$((passed + 1))
echo ""

# Test 2: Listado
total=$((total + 1))
test_query 2 "Muéstrame los primeros 5 compradores" "list" && passed=$((passed + 1))
echo ""

# Test 3: Conteo con filtro
total=$((total + 1))
test_query 3 "¿Cuántas facturas hay?" "count" && passed=$((passed + 1))
echo ""

# Test 4: Usuarios
total=$((total + 1))
test_query 4 "Lista los últimos 3 usuarios" "list" && passed=$((passed + 1))
echo ""

# Test 5: Agregación (puede fallar si no hay datos)
total=$((total + 1))
test_query 5 "¿Cuánto es el total de facturas?" "aggregate" && passed=$((passed + 1))
echo ""

# 4. Resultados finales
echo "=================================="
echo "📊 Resultados:"
echo "  Pasadas: $passed/$total"
echo "  Fallidas: $((total - passed))/$total"
echo ""

if [ $passed -eq $total ]; then
    echo -e "${GREEN}¡Todas las pruebas pasaron!${NC}"
    echo ""
    echo "El sistema está funcionando correctamente."
    echo "Puedes empezar a hacer consultas con:"
    echo "  curl -X POST http://127.0.0.1:8000/ask -H 'Content-Type: application/json' -d '{\"question\":\"tu pregunta aquí\"}' | jq"
    exit 0
elif [ $passed -gt 0 ]; then
    echo -e "${YELLOW}  Algunas pruebas fallaron${NC}"
    echo ""
    echo "El sistema funciona parcialmente. Revisa:"
    echo "  1. Que la base de datos tenga datos"
    echo "  2. Que el schema_catalog.yaml esté actualizado"
    echo "  3. Los logs de cada servicio"
    exit 1
else
    echo -e "${RED} Todas las pruebas fallaron${NC}"
    echo ""
    echo "Revisa:"
    echo "  1. Variables de entorno (PG_HOST, PG_DB, etc.)"
    echo "  2. Conexión a la base de datos"
    echo "  3. Logs de los servicios para errores"
    echo ""
    echo "Ver logs:"
    echo "  Conector: curl http://127.0.0.1:8000/health | jq"
    echo "  SQLCoder: curl http://127.0.0.1:8001/health | jq"
    echo "  NLG: curl http://127.0.0.1:8002/health | jq"
    exit 1
fi
