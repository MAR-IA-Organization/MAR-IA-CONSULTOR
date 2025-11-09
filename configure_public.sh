#!/bin/bash
# ============================================================================
# 🌐 Configuración para Exponer MAR-IA en RunPod
# ============================================================================

# Detectar si estamos en RunPod
detect_runpod() {
    if [ -n "$RUNPOD_POD_ID" ]; then
        echo "✅ Detectado entorno RunPod"
        echo "Pod ID: $RUNPOD_POD_ID"
        return 0
    else
        echo "ℹ️  No se detectó RunPod (modo local)"
        return 1
    fi
}

# Generar URLs públicas de RunPod
get_runpod_urls() {
    local pod_id="$RUNPOD_POD_ID"
    
    if [ -z "$pod_id" ]; then
        echo "❌ RUNPOD_POD_ID no está definido"
        return 1
    fi
    
    # Extraer el identificador del pod (primeros caracteres antes del guión)
    local pod_short=$(echo "$pod_id" | cut -d'-' -f1)
    
    # Generar URLs públicas (RunPod usa este formato)
    export CONECTOR_PUBLIC_URL="https://${pod_short}-8000.proxy.runpod.net"
    export NLG_PUBLIC_URL="https://${pod_short}-8002.proxy.runpod.net"
    export SQLCODER_PUBLIC_URL="https://${pod_short}-8011.proxy.runpod.net"
    
    echo "🌐 URLs Públicas Generadas:"
    echo "  Conector:  $CONECTOR_PUBLIC_URL"
    echo "  NLG:       $NLG_PUBLIC_URL"
    echo "  SQLCoder:  $SQLCODER_PUBLIC_URL"
    echo ""
    echo "⚠️  IMPORTANTE: Debes haber expuesto los puertos 8000,8002,8011 en RunPod"
}

# Configurar .env para uso público
setup_public_env() {
    local env_file="/workspace/api/conector/.env"
    
    # Backup del .env original
    if [ -f "$env_file" ]; then
        cp "$env_file" "${env_file}.backup"
        echo "💾 Backup creado: ${env_file}.backup"
    fi
    
    # Si estamos en RunPod, usar URLs internas para comunicación entre servicios
    # (más rápido que ir por la proxy pública)
    if detect_runpod; then
        cat >> "$env_file" << EOF

# ============================================================================
# CONFIGURACIÓN RUNPOD - URLs INTERNAS (para comunicación entre servicios)
# ============================================================================
SQLCODER_URL=http://127.0.0.1:8011/generate_sql
NLG_URL=http://127.0.0.1:8002/refine

# URLs PÚBLICAS (para acceso externo - usar estas desde otros servidores)
# Nota: Debes exponer los puertos 8000,8002,8011 en la configuración del pod
PUBLIC_CONECTOR_URL=${CONECTOR_PUBLIC_URL:-https://tu-pod-8000.proxy.runpod.net}
PUBLIC_NLG_URL=${NLG_PUBLIC_URL:-https://tu-pod-8002.proxy.runpod.net}
PUBLIC_SQLCODER_URL=${SQLCODER_PUBLIC_URL:-https://tu-pod-8011.proxy.runpod.net}

EOF
        echo "✅ Configuración de RunPod agregada a .env"
    fi
}

# Verificar que los puertos están expuestos
check_public_access() {
    echo "🔍 Verificando acceso público..."
    
    local urls=(
        "$CONECTOR_PUBLIC_URL/health"
        "$NLG_PUBLIC_URL/health"
        "$SQLCODER_PUBLIC_URL/health"
    )
    
    for url in "${urls[@]}"; do
        echo -n "Probando $url ... "
        if curl -s --max-time 5 "$url" > /dev/null 2>&1; then
            echo "✅ Accesible"
        else
            echo "❌ No accesible"
            echo "   → Verifica que el puerto esté expuesto en RunPod"
        fi
    done
}

# Generar instrucciones para cliente externo
generate_client_instructions() {
    cat > /workspace/CLIENT_INSTRUCTIONS.md << EOF
# 🌐 Instrucciones para Acceder a MAR-IA desde Otro Servidor

## URLs Públicas del Sistema

- **Conector Principal**: $CONECTOR_PUBLIC_URL
- **NLG (MAR-IA)**: $NLG_PUBLIC_URL  
- **SQLCoder**: $SQLCODER_PUBLIC_URL

## Ejemplo de Uso desde Otro Servidor

### Python
\`\`\`python
import requests

# Hacer consulta
response = requests.post(
    "${CONECTOR_PUBLIC_URL}/ask",
    json={
        "question": "¿Cuántos compradores tengo?",
        "lang": "es"
    },
    timeout=30
)

result = response.json()
print(result['answer'])
\`\`\`

### cURL
\`\`\`bash
curl -X POST ${CONECTOR_PUBLIC_URL}/ask \\
  -H "Content-Type: application/json" \\
  -d '{"question":"¿Cuántos compradores tengo?","lang":"es"}'
\`\`\`

### JavaScript/Node.js
\`\`\`javascript
const response = await fetch('${CONECTOR_PUBLIC_URL}/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: '¿Cuántos compradores tengo?',
    lang: 'es'
  })
});

const data = await response.json();
console.log(data.answer);
\`\`\`

## Endpoints Disponibles

- \`POST /ask\` - Consulta principal (recomendado)
- \`GET /health\` - Verificar estado del sistema
- \`GET /debug/tables\` - Listar tablas disponibles
- \`POST /debug/validate_sql\` - Validar SQL sin ejecutar

## Notas Importantes

1. **Timeout**: Las consultas pueden tardar hasta 30 segundos en CPU
2. **HTTPS**: Todas las URLs usan HTTPS (certificado de RunPod)
3. **Rate Limiting**: RunPod puede aplicar límites de tasa
4. **Persistencia**: Si el pod se reinicia, las URLs pueden cambiar

## Verificar Disponibilidad

\`\`\`bash
# Health check rápido
curl ${CONECTOR_PUBLIC_URL}/health
\`\`\`

Debería retornar:
\`\`\`json
{
  "status": "ok",
  "pg_connection": "ok",
  "version": "2.2"
}
\`\`\`

EOF

    echo "✅ Instrucciones generadas en /workspace/CLIENT_INSTRUCTIONS.md"
    cat /workspace/CLIENT_INSTRUCTIONS.md
}

# Función principal
main() {
    echo "============================================"
    echo "🌐 Configuración de Acceso Público - RunPod"
    echo "============================================"
    echo ""
    
    # Detectar entorno
    if detect_runpod; then
        get_runpod_urls
        setup_public_env
        
        echo ""
        echo "⏳ Esperando a que los servicios inicien..."
        sleep 5
        
        echo ""
        check_public_access
        
        echo ""
        generate_client_instructions
        
        echo ""
        echo "============================================"
        echo "✅ Configuración Completada"
        echo "============================================"
        echo ""
        echo "📋 Próximos pasos:"
        echo "  1. Verifica que los puertos estén expuestos en RunPod"
        echo "  2. Comparte las URLs públicas con otros servidores"
        echo "  3. Lee CLIENT_INSTRUCTIONS.md para ejemplos de uso"
        echo ""
        echo "🔗 URL Principal para Compartir:"
        echo "   $CONECTOR_PUBLIC_URL"
        
    else
        echo "❌ Este script debe ejecutarse en un pod de RunPod"
        echo ""
        echo "Si estás en RunPod pero no se detectó:"
        echo "  export RUNPOD_POD_ID='tu-pod-id'"
        echo "  ./configure_public.sh"
    fi
}

# Ejecutar
main
