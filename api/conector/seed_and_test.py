#!/bin/bash
# Pruebas Avanzadas para el Sistema SQLCoder + NLG

echo "=========================================="
echo "PRUEBAS AVANZADAS"
echo "=========================================="

CONNECTOR_URL="http://127.0.0.1:8000"

# ============================================================================
# 1. PRUEBAS DE PATRONES COMPLEJOS
# ============================================================================
echo -e "\n[1] Agregaciones y Cálculos"

# Suma de montos
echo "→ Total de ingresos..."
curl -s -X POST "$CONNECTOR_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuál es el total de ingresos?",
    "lang": "es"
  }' | jq -r '.sql, .answer' | head -2

# Promedio
echo -e "\n→ Promedio de precios..."
curl -s -X POST "$CONNECTOR_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuál es el precio promedio de los productos?",
    "lang": "es"
  }' | jq -r '.sql, .answer' | head -2

# ============================================================================
# 2. PRUEBAS DE LÍMITES DINÁMICOS
# ============================================================================
echo -e "\n[2] Límites Dinámicos en Listados"

# Top 3
curl -s -X POST "$CONNECTOR_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Muéstrame los 3 compradores más recientes",
    "lang": "es"
  }' | jq -r '.sql, .row_count, .shortcut'

# Top 20
echo -e "\n→ Top 20..."
curl -s -X POST "$CONNECTOR_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Dame los primeros 20 cultivos",
    "lang": "es"
  }' | jq -r '.sql, .row_count'

# ============================================================================
# 3. PRUEBAS DE DIFERENTES TABLAS
# ============================================================================
echo -e "\n[3] Consultas a Diferentes Tablas"

declare -a preguntas=(
  "¿Cuántas facturas tengo?"
  "¿Cuántos trabajadores hay?"
  "¿Cuántas fincas están registradas?"
  "¿Cuántos cultivos diferentes tengo?"
  "Muéstrame las deudas"
  "Lista los pagos"
)

for pregunta in "${preguntas[@]}"; do
  echo -e "\n→ $pregunta"
  curl -s -X POST "$CONNECTOR_URL/ask" \
    -H "Content-Type: application/json" \
    -d "{
      \"question\": \"$pregunta\",
      \"lang\": \"es\"
    }" | jq -r '.sql, .tables_used[0]'
done

# ============================================================================
# 4. PRUEBA DE CONSISTENCIA (CACHÉ)
# ============================================================================
echo -e "\n[4] Prueba de Consistencia y Caché"

pregunta="¿Cuántos compradores tengo?"

echo "→ Ejecutando 5 veces la misma pregunta..."
for i in {1..5}; do
  start=$(date +%s%N)
  
  sql=$(curl -s -X POST "$CONNECTOR_URL/ask" \
    -H "Content-Type: application/json" \
    -d "{\"question\":\"$pregunta\",\"lang\":\"es\"}" \
    | jq -r '.sql')
  
  end=$(date +%s%N)
  duration=$(( (end - start) / 1000000 ))
  
  echo "  Intento $i: $duration ms → $sql"
done

# ============================================================================
# 5. PRUEBAS DE PALABRAS CLAVE EN ESPAÑOL
# ============================================================================
echo -e "\n🇪🇸 [5] Variaciones en Español"

declare -a variaciones=(
  "cantidad de compradores"
  "número de compradores"
  "cuántos compradores"
  "total de compradores"
  "dame el total de compradores"
)

for var in "${variaciones[@]}"; do
  echo -e "\n→ '$var'"
  curl -s -X POST "$CONNECTOR_URL/ask" \
    -H "Content-Type: application/json" \
    -d "{
      \"question\": \"$var\",
      \"lang\": \"es\"
    }" | jq -r '.sql'
done

# ============================================================================
# 6. PRUEBA DE TABLAS CON ALIAS
# ============================================================================
echo -e "\n[6] Corrección Automática de Nombres (Aliases)"

declare -a con_alias=(
  "¿Cuántos customers tengo?"
  "Lista los invoices"
  "Muéstrame las facturas"
  "Dame los compradores"
  "¿Cuántos users hay?"
)

for pregunta in "${con_alias[@]}"; do
  echo -e "\n→ '$pregunta'"
  response=$(curl -s -X POST "$CONNECTOR_URL/ask" \
    -H "Content-Type: application/json" \
    -d "{
      \"question\": \"$pregunta\",
      \"lang\": \"es\"
    }")
  
  sql=$(echo "$response" | jq -r '.sql')
  error=$(echo "$response" | jq -r '.error // "none"')
  
  if [ "$error" = "none" ]; then
    echo "  SQL: $sql"
  else
    echo "  Error: $error"
  fi
done

# ============================================================================
# 7. PRUEBA DE RENDIMIENTO
# ============================================================================
echo -e "\n [7] Prueba de Rendimiento"

echo "→ Ejecutando 10 consultas diferentes secuencialmente..."

start_total=$(date +%s%N)

declare -a test_queries=(
  "¿Cuántos compradores tengo?"
  "Muéstrame 5 facturas"
  "¿Cuántos trabajadores hay?"
  "Lista los cultivos"
  "¿Cuál es el total de ingresos?"
  "Dame las fincas"
  "¿Cuántas deudas hay?"
  "Muéstrame los pagos"
  "¿Cuántas ofertas tengo?"
  "Lista los precios de mercado"
)

success=0
failed=0

for query in "${test_queries[@]}"; do
  start=$(date +%s%N)
  
  response=$(curl -s -X POST "$CONNECTOR_URL/ask" \
    -H "Content-Type: application/json" \
    -d "{\"question\":\"$query\",\"lang\":\"es\"}")
  
  end=$(date +%s%N)
  duration=$(( (end - start) / 1000000 ))
  
  if echo "$response" | jq -e '.execution_success' > /dev/null 2>&1; then
    if [ "$(echo "$response" | jq -r '.execution_success')" = "true" ]; then
      ((success++))
      echo "  ${duration}ms: $query"
    else
      ((failed++))
      echo "  ${duration}ms: $query"
    fi
  else
    ((failed++))
    echo "  ${duration}ms: $query (sin estado)"
  fi
done

end_total=$(date +%s%N)
duration_total=$(( (end_total - start_total) / 1000000 ))

echo ""
echo "Resultados:"
echo "  Total: 10 consultas"
echo "  Exitosas: $success"
echo "  Fallidas: $failed"
echo "  Tiempo total: ${duration_total}ms"
echo "  Promedio por consulta: $(( duration_total / 10 ))ms"

# ============================================================================
# 8. VERIFICAR SISTEMA DE MEMORIA DESPUÉS DE PRUEBAS
# ============================================================================
echo -e "\n[8] Estado de la Memoria después de las pruebas"

curl -s "$CONNECTOR_URL/../sqlcoder/health" 2>/dev/null | jq '.memory' || \
curl -s "http://127.0.0.1:8011/health" | jq '.memory'

echo ""
echo "→ Si total_queries > 0, el sistema está aprendiendo "
echo "→ Si total_queries = 0, verifica permisos del archivo memory.json "

# ============================================================================
# 9. PRUEBA DE FEEDBACK MANUAL
# ============================================================================
echo -e "\n[9] Registrar Feedback Manual"

curl -s -X POST "http://127.0.0.1:8011/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuántos compradores tengo?",
    "sql": "SELECT COUNT(*) AS total FROM public.commerce_buyer",
    "success": true,
    "tables_used": ["public.commerce_buyer"]
  }' | jq

echo ""
echo "→ Verificar nueva entrada en memoria:"
curl -s "http://127.0.0.1:8011/health" | jq '.memory'

# ============================================================================
# 10. PRUEBAS DE ERRORES ESPERADOS
# ============================================================================
echo -e "\n[10] Pruebas de Manejo de Errores"

# Pregunta ambigua
echo "→ Pregunta ambigua..."
curl -s -X POST "$CONNECTOR_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "dame algo",
    "lang": "es"
  }' | jq -r 'if .error then "Error esperado: " + .error else "Respuesta: " + .sql end'

# Tabla inexistente (debería auto-corregir)
echo -e "\n→ Tabla con nombre incorrecto (debe auto-corregir)..."
curl -s -X POST "$CONNECTOR_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Cuántos customers tengo?",
    "lang": "es"
  }' | jq -r 'if .error then "No corrigió: " + .error else "Corrigió: " + .sql end'

# ============================================================================
# RESUMEN FINAL
# ============================================================================
echo -e "\n=========================================="
echo "PRUEBAS AVANZADAS COMPLETADAS"
echo "=========================================="
echo ""
echo "Puntos a verificar:"
echo "  1. ¿Todas las consultas generaron SQL válido?"
echo "  2. ¿El sistema aprende (memory.json se actualiza)?"
echo "  3. ¿Los atajos funcionan (list_intent)?"
echo "  4. ¿NLG genera respuestas coherentes?"
echo "  5. ¿Los aliases se corrigen automáticamente?"
echo ""
echo "Para ver el archivo de memoria:"
echo "  cat /workspace/sqlcoder_7b_2/memory.json | jq"