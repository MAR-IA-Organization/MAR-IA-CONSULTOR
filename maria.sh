#!/bin/bash
# ============================================================================
# SISTEMA DE GESTIÓN COMPLETO - MAR-IA (RunPod Ready)
# ============================================================================

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuración de puertos
CONECTOR_PORT=8000
NLG_PORT=8002
SQLCODER_PORT=8011

# Rutas de proyecto
CONECTOR_DIR="/workspace/api/conector"
NLG_DIR="/workspace/GPT"
SQLCODER_DIR="/workspace/sqlcoder_7b_2"

# Detectar RunPod
IS_RUNPOD=false
if [ -n "$RUNPOD_POD_ID" ]; then
    IS_RUNPOD=true
    POD_SHORT=$(echo "$RUNPOD_POD_ID" | cut -d'-' -f1)
    PUBLIC_BASE_URL="https://${POD_SHORT}"
fi

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

print_header() {
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -tln 2>/dev/null | grep -q ":$port "; then
        return 0
    else
        return 1
    fi
}

wait_for_service() {
    local url=$1
    local name=$2
    local max_wait=30
    local count=0
    
    echo -n "Esperando a que $name esté listo"
    
    while [ $count -lt $max_wait ]; do
        if curl -s "$url/health" > /dev/null 2>&1; then
            echo ""
            print_success "$name está listo"
            return 0
        fi
        echo -n "."
        sleep 1
        ((count++))
    done
    
    echo ""
    print_error "$name no respondió después de ${max_wait}s"
    return 1
}

kill_service() {
    local port=$1
    local name=$2
    
    if check_port $port; then
        print_info "Deteniendo $name en puerto $port..."
        pkill -f "uvicorn.*:$port" 2>/dev/null || true
        fuser -k ${port}/tcp 2>/dev/null || true
        sleep 2
        
        if check_port $port; then
            print_error "No se pudo liberar el puerto $port"
            return 1
        else
            print_success "$name detenido"
            return 0
        fi
    else
        print_info "$name no está corriendo"
        return 0
    fi
}

# ============================================================================
# FUNCIONES DE INICIO DE SERVICIOS
# ============================================================================

start_sqlcoder() {
    print_header "🤖 Iniciando SQLCoder Ligero"
    
    if [ ! -d "$SQLCODER_DIR" ]; then
        print_error "Directorio no encontrado: $SQLCODER_DIR"
        return 1
    fi
    
    cd "$SQLCODER_DIR"
    
    if [ ! -d ".venv" ]; then
        print_warning "Creando entorno virtual..."
        python3 -m venv .venv
    fi
    
    source .venv/bin/activate
    
    if ! pip show fastapi > /dev/null 2>&1; then
        print_warning "Instalando dependencias..."
        pip install -q fastapi uvicorn[standard]
    fi
    
    mkdir -p /workspace/sqlcoder_7b_2/
    if [ ! -f "/workspace/sqlcoder_7b_2/memory.json" ]; then
        echo '{"successful_queries":[],"failed_patterns":[]}' > /workspace/sqlcoder_7b_2/memory.json
        chmod 666 /workspace/sqlcoder_7b_2/memory.json
    fi
    
    kill_service $SQLCODER_PORT "SQLCoder"
    
    print_info "Iniciando SQLCoder en puerto $SQLCODER_PORT..."
    nohup uvicorn app_sqlcoder:app \
        --host 0.0.0.0 \
        --port $SQLCODER_PORT \
        --log-level info \
        > /tmp/sqlcoder.log 2>&1 &
    
    SQLCODER_PID=$!
    echo $SQLCODER_PID > /tmp/sqlcoder.pid
    
    wait_for_service "http://127.0.0.1:$SQLCODER_PORT" "SQLCoder"
    
    print_success "SQLCoder iniciado (PID: $SQLCODER_PID)"
    print_info "Logs: tail -f /tmp/sqlcoder.log"
}

start_nlg() {
    print_header "💬 Iniciando NLG (MAR-IA)"
    
    if [ ! -d "$NLG_DIR" ]; then
        print_error "Directorio no encontrado: $NLG_DIR"
        return 1
    fi
    
    cd "$NLG_DIR"
    
    if [ ! -d ".venv" ]; then
        print_warning "Creando entorno virtual..."
        python3 -m venv .venv
    fi
    
    source .venv/bin/activate
    
    cat > requirements.txt << 'EOF'
fastapi
uvicorn[standard]
pydantic
EOF
    
    print_info "Verificando dependencias..."
    pip install -q -r requirements.txt
    
    kill_service $NLG_PORT "NLG"
    
    print_info "Iniciando NLG en puerto $NLG_PORT..."
    nohup uvicorn app_gpt:app \
        --host 0.0.0.0 \
        --port $NLG_PORT \
        --log-level info \
        > /tmp/nlg.log 2>&1 &
    
    NLG_PID=$!
    echo $NLG_PID > /tmp/nlg.pid
    
    wait_for_service "http://127.0.0.1:$NLG_PORT" "NLG"
    
    print_success "NLG iniciado (PID: $NLG_PID)"
    print_info "Logs: tail -f /tmp/nlg.log"
}

start_conector() {
    print_header "🔌 Iniciando Conector Principal"
    
    if [ ! -d "$CONECTOR_DIR" ]; then
        print_error "Directorio no encontrado: $CONECTOR_DIR"
        return 1
    fi
    
    cd "$CONECTOR_DIR"
    
    if [ ! -d ".venv" ]; then
        print_warning "Creando entorno virtual..."
        python3 -m venv .venv
    fi
    
    source .venv/bin/activate
    
    if ! pip show fastapi > /dev/null 2>&1; then
        print_warning "Instalando dependencias..."
        pip install -q fastapi uvicorn[standard] pydantic psycopg2-binary pyyaml requests
    fi
    
    if [ -z "$PG_HOST" ] || [ -z "$PG_DB" ] || [ -z "$PG_USER" ] || [ -z "$PG_PASS" ]; then
        print_error "Variables de entorno faltantes: PG_HOST, PG_DB, PG_USER, PG_PASS"
        print_warning "Cargando desde .env si existe..."
        
        if [ -f ".env" ]; then
            export $(grep -v '^#' .env | xargs)
        else
            print_error "No se encontró archivo .env"
            return 1
        fi
    fi
    
    export SQLCODER_URL="http://127.0.0.1:$SQLCODER_PORT/generate_sql"
    export NLG_URL="http://127.0.0.1:$NLG_PORT/refine"
    export SQLCODER_TIMEOUT=180
    
    kill_service $CONECTOR_PORT "Conector"
    
    print_info "Iniciando Conector en puerto $CONECTOR_PORT..."
    PYTHONPATH=$CONECTOR_DIR nohup uvicorn bootstrap:app \
        --host 0.0.0.0 \
        --port $CONECTOR_PORT \
        --workers 1 \
        --log-level info \
        > /tmp/conector.log 2>&1 &
    
    CONECTOR_PID=$!
    echo $CONECTOR_PID > /tmp/conector.pid
    
    wait_for_service "http://127.0.0.1:$CONECTOR_PORT" "Conector"
    
    print_success "Conector iniciado (PID: $CONECTOR_PID)"
    print_info "Logs: tail -f /tmp/conector.log"
}

# ============================================================================
# FUNCIONES DE GESTIÓN
# ============================================================================

start_all() {
    print_header "🚀 Iniciando Sistema Completo MAR-IA"
    
    if [ "$IS_RUNPOD" = true ]; then
        print_warning "Modo RunPod detectado (Pod ID: $RUNPOD_POD_ID)"
    fi
    
    start_sqlcoder
    if [ $? -ne 0 ]; then
        print_error "Fallo al iniciar SQLCoder. Abortando."
        return 1
    fi
    
    sleep 2
    
    start_nlg
    if [ $? -ne 0 ]; then
        print_warning "Fallo al iniciar NLG. Continuando..."
    fi
    
    sleep 2
    
    start_conector
    if [ $? -ne 0 ]; then
        print_error "Fallo al iniciar Conector. Abortando."
        return 1
    fi
    
    echo ""
    print_header "✅ Sistema Iniciado Correctamente"
    status_all
    
    # Mostrar URLs públicas si es RunPod
    if [ "$IS_RUNPOD" = true ]; then
        show_public_urls
    fi
    
    echo ""
    print_info "Para probar el sistema:"
    echo "  curl -X POST http://127.0.0.1:8000/ask -H 'Content-Type: application/json' \\"
    echo "    -d '{\"question\":\"¿Cuántos compradores tengo?\",\"lang\":\"es\"}' | jq"
}

stop_all() {
    print_header "🛑 Deteniendo Sistema MAR-IA"
    
    kill_service $CONECTOR_PORT "Conector"
    sleep 1
    kill_service $NLG_PORT "NLG"
    sleep 1
    kill_service $SQLCODER_PORT "SQLCoder"
    
    rm -f /tmp/conector.pid /tmp/nlg.pid /tmp/sqlcoder.pid
    
    print_success "Todos los servicios detenidos"
}

restart_all() {
    print_header "🔄 Reiniciando Sistema MAR-IA"
    stop_all
    sleep 2
    start_all
}

status_all() {
    print_header "📊 Estado del Sistema MAR-IA"
    
    echo ""
    echo -e "${CYAN}Servicio          Puerto    Estado          URL${NC}"
    echo "─────────────────────────────────────────────────────────────"
    
    # SQLCoder
    if check_port $SQLCODER_PORT; then
        status=$(curl -s http://127.0.0.1:$SQLCODER_PORT/health 2>/dev/null | jq -r '.status // "unknown"')
        echo -e "SQLCoder          $SQLCODER_PORT       ${GREEN}✅ Running${NC}      http://127.0.0.1:$SQLCODER_PORT"
        if [ "$status" = "ok" ]; then
            queries=$(curl -s http://127.0.0.1:$SQLCODER_PORT/health | jq -r '.memory.total_queries // 0')
            echo "                              └─ Memoria: $queries consultas"
        fi
    else
        echo -e "SQLCoder          $SQLCODER_PORT       ${RED}❌ Stopped${NC}"
    fi
    
    # NLG
    if check_port $NLG_PORT; then
        echo -e "NLG (MAR-IA)      $NLG_PORT       ${GREEN}✅ Running${NC}      http://127.0.0.1:$NLG_PORT"
    else
        echo -e "NLG (MAR-IA)      $NLG_PORT       ${RED}❌ Stopped${NC}"
    fi
    
    # Conector
    if check_port $CONECTOR_PORT; then
        pg_status=$(curl -s http://127.0.0.1:$CONECTOR_PORT/health 2>/dev/null | jq -r '.pg_connection // "unknown"')
        echo -e "Conector          $CONECTOR_PORT       ${GREEN}✅ Running${NC}      http://127.0.0.1:$CONECTOR_PORT"
        if [ "$pg_status" = "ok" ]; then
            echo -e "                              └─ PostgreSQL: ${GREEN}✅ Conectado${NC}"
        else
            echo -e "                              └─ PostgreSQL: ${RED}❌ Desconectado${NC}"
        fi
    else
        echo -e "Conector          $CONECTOR_PORT       ${RED}❌ Stopped${NC}"
    fi
    
    echo ""
}

show_public_urls() {
    if [ "$IS_RUNPOD" = false ]; then
        return
    fi
    
    print_header "🌐 URLs Públicas de RunPod"
    
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANTE: Debes haber expuesto los puertos en RunPod${NC}"
    echo "   En la configuración del pod: 8000, 8002, 8011"
    echo ""
    
    echo -e "${GREEN}URLs Públicas:${NC}"
    echo "  Conector:  ${PUBLIC_BASE_URL}-8000.proxy.runpod.net"
    echo "  NLG:       ${PUBLIC_BASE_URL}-8002.proxy.runpod.net"
    echo "  SQLCoder:  ${PUBLIC_BASE_URL}-8011.proxy.runpod.net"
    echo ""
    
    echo -e "${BLUE}Ejemplo desde otro servidor:${NC}"
    echo "  curl -X POST ${PUBLIC_BASE_URL}-8000.proxy.runpod.net/ask \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"question\":\"¿Cuántos compradores tengo?\",\"lang\":\"es\"}'"
    echo ""
    
    # Guardar URLs en archivo
    cat > /workspace/PUBLIC_URLS.txt << EOF
🌐 URLs Públicas del Sistema MAR-IA en RunPod

Conector Principal: ${PUBLIC_BASE_URL}-8000.proxy.runpod.net
NLG (MAR-IA):      ${PUBLIC_BASE_URL}-8002.proxy.runpod.net
SQLCoder:          ${PUBLIC_BASE_URL}-8011.proxy.runpod.net

Uso desde otro servidor:
curl -X POST ${PUBLIC_BASE_URL}-8000.proxy.runpod.net/ask \\
  -H "Content-Type: application/json" \\
  -d '{"question":"¿Cuántos compradores tengo?","lang":"es"}'

Generado: $(date)
EOF
    
    print_success "URLs guardadas en /workspace/PUBLIC_URLS.txt"
}

logs_service() {
    local service=$1
    
    case $service in
        conector)
            print_info "Mostrando logs del Conector (Ctrl+C para salir)..."
            tail -f /tmp/conector.log
            ;;
        nlg)
            print_info "Mostrando logs del NLG (Ctrl+C para salir)..."
            tail -f /tmp/nlg.log
            ;;
        sqlcoder)
            print_info "Mostrando logs del SQLCoder (Ctrl+C para salir)..."
            tail -f /tmp/sqlcoder.log
            ;;
        *)
            print_error "Servicio desconocido: $service"
            print_info "Opciones: conector, nlg, sqlcoder"
            ;;
    esac
}

test_system() {
    print_header "🧪 Probando Sistema"
    
    echo ""
    print_info "Test 1: Health checks..."
    
    if curl -s http://127.0.0.1:$SQLCODER_PORT/health > /dev/null 2>&1; then
        print_success "SQLCoder: OK"
    else
        print_error "SQLCoder: FAIL"
    fi
    
    if curl -s http://127.0.0.1:$NLG_PORT/health > /dev/null 2>&1; then
        print_success "NLG: OK"
    else
        print_error "NLG: FAIL"
    fi
    
    if curl -s http://127.0.0.1:$CONECTOR_PORT/health > /dev/null 2>&1; then
        print_success "Conector: OK"
    else
        print_error "Conector: FAIL"
    fi
    
    echo ""
    print_info "Test 2: Consulta de prueba..."
    
    response=$(curl -s -X POST http://127.0.0.1:$CONECTOR_PORT/ask \
        -H "Content-Type: application/json" \
        -d '{"question":"¿Cuántos compradores tengo?","lang":"es"}')
    
    if echo "$response" | jq -e '.execution_success' > /dev/null 2>&1; then
        if [ "$(echo "$response" | jq -r '.execution_success')" = "true" ]; then
            print_success "Query ejecutado correctamente"
            echo "$response" | jq -r '"SQL: " + .sql'
            echo "$response" | jq -r '"Respuesta: " + .answer' | head -c 100
            echo "..."
        else
            print_error "Query falló"
            echo "$response" | jq -r '.error // "Error desconocido"'
        fi
    else
        print_error "Respuesta inválida del servidor"
    fi
}

show_help() {
    cat << EOF
${CYAN}============================================
🚀 Sistema de Gestión MAR-IA
============================================${NC}

${YELLOW}Uso:${NC}
  ./maria.sh [comando]

${YELLOW}Comandos disponibles:${NC}
  ${GREEN}start${NC}           Inicia todos los servicios
  ${GREEN}stop${NC}            Detiene todos los servicios
  ${GREEN}restart${NC}         Reinicia todos los servicios
  ${GREEN}status${NC}          Muestra el estado de los servicios
  ${GREEN}test${NC}            Ejecuta pruebas del sistema
  ${GREEN}public-urls${NC}     Muestra URLs públicas (solo RunPod)
  
  ${GREEN}start-sqlcoder${NC}  Inicia solo SQLCoder
  ${GREEN}start-nlg${NC}       Inicia solo NLG
  ${GREEN}start-conector${NC}  Inicia solo Conector
  
  ${GREEN}logs <servicio>${NC}  Muestra logs en tiempo real
                     Servicios: conector, nlg, sqlcoder
  
  ${GREEN}help${NC}            Muestra esta ayuda

${YELLOW}Ejemplos:${NC}
  ./maria.sh start              # Inicia todo el sistema
  ./maria.sh status             # Ver estado
  ./maria.sh public-urls        # Ver URLs públicas
  ./maria.sh logs conector      # Ver logs del conector
  ./maria.sh test               # Probar el sistema

EOF

    if [ "$IS_RUNPOD" = true ]; then
        echo -e "${YELLOW}RunPod detectado:${NC}"
        echo "  Pod ID: $RUNPOD_POD_ID"
        echo "  URLs públicas disponibles con: ./maria.sh public-urls"
        echo ""
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    case "$1" in
        start)
            start_all
            ;;
        stop)
            stop_all
            ;;
        restart)
            restart_all
            ;;
        status)
            status_all
            ;;
        test)
            test_system
            ;;
        public-urls)
            show_public_urls
            ;;
        start-sqlcoder)
            start_sqlcoder
            ;;
        start-nlg)
            start_nlg
            ;;
        start-conector)
            start_conector
            ;;
        logs)
            logs_service "$2"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Comando desconocido: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
