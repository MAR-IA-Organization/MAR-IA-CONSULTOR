import random
import json
from datetime import datetime, timedelta
from faker import Faker

fake = Faker(['es_CO', 'es_ES'])  # Nombres colombianos/españoles

# ====================================
# CONFIGURACIÓN
# ====================================
NUM_FARMS = 3
NUM_USERS = 15
NUM_WORKERS = 25
NUM_BUYERS = 10
NUM_CROPS_PER_FARM = 5
NUM_DAYS = 180  # 6 meses de datos

# Datos base
CROP_TYPES = [
    {"name": "Café", "variety": "Castillo", "cycle_days": 180},
    {"name": "Café", "variety": "Caturra", "cycle_days": 180},
    {"name": "Plátano", "variety": "Hartón", "cycle_days": 270},
    {"name": "Yuca", "variety": "Venezolana", "cycle_days": 240},
    {"name": "Maíz", "variety": "Amarillo", "cycle_days": 120},
]

COST_CATEGORIES = ["Fertilizantes", "Mano de obra", "Herramientas", "Transporte", "Mantenimiento", "Servicios"]
TOOL_TYPES = ["Machete", "Azadón", "Bomba fumigadora", "Carretilla", "Guadaña", "Motosierra"]

# ====================================
# GENERADORES DE DATOS
# ====================================

class DataGenerator:
    def __init__(self):
        self.data = {
            "users": [],
            "farms": [],
            "crops": [],
            "workers": [],
            "buyers": [],
            "production": [],
            "income": [],
            "costs": [],
            "tools": [],
            "employees": [],
            "listings": [],
            "bids": [],
            "invoices": [],
            "worker_debts": [],
            "worker_payments": []
        }
        self.start_date = datetime.now() - timedelta(days=NUM_DAYS)
    
    def generate_users(self):
        """Genera usuarios del sistema"""
        roles = ["farmer", "buyer", "admin"]
        for i in range(NUM_USERS):
            user = {
                "id": i + 1,
                "username": fake.user_name(),
                "email": fake.email(),
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "role": random.choice(roles),
                "is_active": True,
                "date_joined": (self.start_date - timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
            }
            self.data["users"].append(user)
        print(f"✅ Generados {len(self.data['users'])} usuarios")
    
    def generate_farms(self):
        """Genera fincas"""
        locations = ["Vereda El Café, Chinchiná", "Vereda La Esperanza, Manizales", "Vereda Santa Rita, Palestina"]
        farmer_users = [u for u in self.data["users"] if u["role"] == "farmer"]
        
        for i in range(NUM_FARMS):
            owner = random.choice(farmer_users) if farmer_users else self.data["users"][0]
            farm = {
                "id": i + 1,
                "name": f"Finca {fake.last_name()}",
                "location": locations[i] if i < len(locations) else fake.address(),
                "area_hectares": round(random.uniform(2.5, 15.0), 2),
                "owner_id": owner["id"]
            }
            self.data["farms"].append(farm)
        print(f"✅ Generadas {len(self.data['farms'])} fincas")
    
    def generate_crops(self):
        """Genera cultivos por finca"""
        crop_id = 1
        for farm in self.data["farms"]:
            num_crops = random.randint(3, NUM_CROPS_PER_FARM)
            for _ in range(num_crops):
                crop_type = random.choice(CROP_TYPES)
                planted_date = self.start_date - timedelta(days=random.randint(0, 365))
                expected_harvest = planted_date + timedelta(days=crop_type["cycle_days"])
                
                crop = {
                    "id": crop_id,
                    "name": crop_type["name"],
                    "variety": crop_type["variety"],
                    "planted_at": planted_date.strftime("%Y-%m-%d"),
                    "expected_harvest_at": expected_harvest.strftime("%Y-%m-%d"),
                    "farm_id": farm["id"]
                }
                self.data["crops"].append(crop)
                crop_id += 1
        print(f"✅ Generados {len(self.data['crops'])} cultivos")
    
    def generate_workers(self):
        """Genera trabajadores agrícolas"""
        for i in range(NUM_WORKERS):
            worker = {
                "id": i + 1,
                "full_name": fake.name(),
                "document": str(random.randint(10000000, 99999999)),
                "phone": f"3{random.randint(100000000, 199999999)}",
                "is_active": random.choice([True, True, True, False])  # 75% activos
            }
            self.data["workers"].append(worker)
        print(f"✅ Generados {len(self.data['workers'])} trabajadores")
    
    def generate_buyers(self):
        """Genera compradores"""
        for i in range(NUM_BUYERS):
            buyer = {
                "id": i + 1,
                "name": fake.company(),
                "email": fake.company_email(),
                "phone": f"3{random.randint(100000000, 199999999)}"
            }
            self.data["buyers"].append(buyer)
        print(f"✅ Generados {len(self.data['buyers'])} compradores")
    
    def generate_production(self):
        """Genera producción diaria"""
        prod_id = 1
        for day in range(NUM_DAYS):
            date = self.start_date + timedelta(days=day)
            
            # Producción por cada cultivo
            for crop in self.data["crops"]:
                # Solo generar si está en época de cosecha
                planted = datetime.strptime(crop["planted_at"], "%Y-%m-%d")
                days_since_planted = (date - planted).days
                
                if 120 < days_since_planted < 300:  # Período de cosecha
                    # Producción con estacionalidad
                    month = date.month
                    if month in [4, 5, 6, 10, 11, 12]:  # Meses altos
                        quantity = random.randint(20, 80)
                    else:
                        quantity = random.randint(5, 30)
                    
                    if quantity > 0:
                        production = {
                            "id": prod_id,
                            "date": date.strftime("%Y-%m-%d"),
                            "quantity_kg": quantity,
                            "crop_id": crop["id"]
                        }
                        self.data["production"].append(production)
                        prod_id += 1
        print(f"✅ Generados {len(self.data['production'])} registros de producción")
    
    def generate_income(self):
        """Genera ingresos basados en producción"""
        income_id = 1
        
        # Agrupar producción por semana para ventas
        productions_by_week = {}
        for prod in self.data["production"]:
            date = datetime.strptime(prod["date"], "%Y-%m-%d")
            week = date.strftime("%Y-W%U")
            if week not in productions_by_week:
                productions_by_week[week] = []
            productions_by_week[week].append(prod)
        
        # Generar ventas semanales
        for week, productions in productions_by_week.items():
            total_kg = sum(p["quantity_kg"] for p in productions)
            if total_kg > 0:
                # Precio por kg varía
                price_per_kg = random.randint(8000, 12000)
                amount = total_kg * price_per_kg
                
                # Fecha de la venta (fin de semana)
                date = datetime.strptime(productions[0]["date"], "%Y-%m-%d") + timedelta(days=7)
                
                income = {
                    "id": income_id,
                    "date": date.strftime("%Y-%m-%d"),
                    "source": f"Venta de {productions[0]['crop_id']} - {total_kg} kg",
                    "amount": amount,
                    "farm_id": random.choice(self.data["farms"])["id"]
                }
                self.data["income"].append(income)
                income_id += 1
        print(f"✅ Generados {len(self.data['income'])} ingresos")
    
    def generate_costs(self):
        """Genera costos operativos"""
        cost_id = 1
        
        for day in range(0, NUM_DAYS, 7):  # Costos semanales
            date = self.start_date + timedelta(days=day)
            
            for farm in self.data["farms"]:
                # 2-4 costos por semana por finca
                num_costs = random.randint(2, 4)
                for _ in range(num_costs):
                    category = random.choice(COST_CATEGORIES)
                    
                    # Montos según categoría
                    if category == "Fertilizantes":
                        amount = random.randint(100000, 500000)
                    elif category == "Mano de obra":
                        amount = random.randint(200000, 800000)
                    else:
                        amount = random.randint(50000, 300000)
                    
                    cost = {
                        "id": cost_id,
                        "date": date.strftime("%Y-%m-%d"),
                        "category": category,
                        "amount": amount,
                        "notes": f"{category} - {fake.sentence(nb_words=5)}",
                        "farm_id": farm["id"]
                    }
                    self.data["costs"].append(cost)
                    cost_id += 1
        print(f"✅ Generados {len(self.data['costs'])} costos")
    
    def generate_tools(self):
        """Genera herramientas por finca"""
        tool_id = 1
        for farm in self.data["farms"]:
            num_tools = random.randint(3, 8)
            for _ in range(num_tools):
                tool_type = random.choice(TOOL_TYPES)
                purchase_date = self.start_date - timedelta(days=random.randint(0, 365))
                
                tool = {
                    "id": tool_id,
                    "name": tool_type,
                    "purchase_date": purchase_date.strftime("%Y-%m-%d"),
                    "cost": random.randint(50000, 1500000),
                    "farm_id": farm["id"]
                }
                self.data["tools"].append(tool)
                tool_id += 1
        print(f"✅ Generadas {len(self.data['tools'])} herramientas")
    
    def generate_employees(self):
        """Genera empleados por finca"""
        emp_id = 1
        roles = ["Jornalero", "Mayordomo", "Recolector", "Fumigador"]
        
        for farm in self.data["farms"]:
            num_employees = random.randint(3, 8)
            for _ in range(num_employees):
                employee = {
                    "id": emp_id,
                    "full_name": fake.name(),
                    "role": random.choice(roles),
                    "daily_rate": random.randint(40000, 80000),
                    "farm_id": farm["id"]
                }
                self.data["employees"].append(employee)
                emp_id += 1
        print(f"✅ Generados {len(self.data['employees'])} empleados")
    
    def generate_worker_debts_and_payments(self):
        """Genera deudas y pagos de trabajadores (sin rangos vacíos en randint)"""
        debt_id = 1
        payment_id = 1
        
        for worker in self.data["workers"]:
            if not worker["is_active"]:
                continue
            
            # Generar 2-5 deudas por trabajador
            num_debts = random.randint(2, 5)
            for _ in range(num_debts):
                created_date = self.start_date + timedelta(days=random.randint(0, NUM_DAYS))
                amount = random.randint(100000, 500000)
                paid = random.choice([True, True, False])  # 66% pagadas
                
                debt = {
                    "id": debt_id,
                    "description": f"Préstamo {fake.word()}",
                    "amount": amount,
                    "created_at": created_date.strftime("%Y-%m-%d"),
                    "paid": paid,
                    "worker_id": worker["id"]
                }
                self.data["worker_debts"].append(debt)
                
                # Si está pagada, generar pagos
                if paid:
                    num_payments = random.randint(1, 3)
                    remaining = amount
                    
                    for i in range(num_payments):
                        # Si es el último pago o el restante ya es pequeño, liquida todo
                        # Usamos 100000 como umbral porque los parciales tienen mínimo 50000.
                        if i == num_payments - 1 or remaining <= 100000:
                            payment_amount = remaining
                        else:
                            upper = remaining // 2
                            if upper < 50000:
                                payment_amount = remaining
                            else:
                                payment_amount = random.randint(50000, upper)

                        remaining -= payment_amount
                        payment_date = created_date + timedelta(days=random.randint(7, 60))
                        
                        payment = {
                            "id": payment_id,
                            "amount": payment_amount,
                            "created_at": payment_date.strftime("%Y-%m-%d"),
                            "note": f"Pago parcial {i+1}",
                            "debt_id": debt_id,
                            "worker_id": worker["id"]
                        }
                        self.data["worker_payments"].append(payment)
                        payment_id += 1
                
                debt_id += 1
        
        print(f"✅ Generadas {len(self.data['worker_debts'])} deudas")
        print(f"✅ Generados {len(self.data['worker_payments'])} pagos")
    
    def generate_listings_bids_invoices(self):
        """Genera listados de venta, ofertas y facturas"""
        listing_id = 1
        bid_id = 1
        invoice_id = 1
        
        # Crear listados basados en producción alta
        for crop in self.data["crops"][:10]:  # Solo algunos cultivos
            # Sumar producción del cultivo
            total_prod = sum(p["quantity_kg"] for p in self.data["production"] if p["crop_id"] == crop["id"])
            
            if total_prod > 100:  # Solo si hay suficiente producción
                listing = {
                    "id": listing_id,
                    "quantity_kg": random.randint(100, min(500, total_prod)),
                    "min_price_per_kg": random.randint(8000, 10000),
                    "is_auction": random.choice([True, False]),
                    "status": random.choice(["active", "active", "sold"]),
                    "crop_id": crop["id"],
                    "seller_id": crop["farm_id"]
                }
                self.data["listings"].append(listing)
                
                # Generar ofertas para este listado
                if listing["is_auction"]:
                    num_bids = random.randint(1, 5)
                    for _ in range(num_bids):
                        buyer = random.choice(self.data["buyers"])
                        bid = {
                            "id": bid_id,
                            "price_per_kg": listing["min_price_per_kg"] + random.randint(100, 1000),
                            "created_at": (self.start_date + timedelta(days=random.randint(0, NUM_DAYS))).strftime("%Y-%m-%d"),
                            "buyer_id": buyer["id"],
                            "listing_id": listing_id
                        }
                        self.data["bids"].append(bid)
                        bid_id += 1
                
                # Generar factura si está vendido
                if listing["status"] == "sold":
                    buyer = random.choice(self.data["buyers"])
                    final_price = listing["min_price_per_kg"] + random.randint(0, 500)
                    
                    invoice = {
                        "id": invoice_id,
                        "total_amount": listing["quantity_kg"] * final_price,
                        "created_at": (self.start_date + timedelta(days=random.randint(0, NUM_DAYS))).strftime("%Y-%m-%d"),
                        "is_proforma": random.choice([True, False]),
                        "buyer_id": buyer["id"],
                        "listing_id": listing_id
                    }
                    self.data["invoices"].append(invoice)
                    invoice_id += 1
                
                listing_id += 1
        
        print(f"✅ Generados {len(self.data['listings'])} listados")
        print(f"✅ Generadas {len(self.data['bids'])} ofertas")
        print(f"✅ Generadas {len(self.data['invoices'])} facturas")
    
    def generate_all(self):
        """Genera todos los datos"""
        print("=" * 60)
        print("🚀 GENERANDO BASE DE DATOS COMPLETA")
        print("=" * 60)
        
        self.generate_users()
        self.generate_farms()
        self.generate_crops()
        self.generate_workers()
        self.generate_buyers()
        self.generate_production()
        self.generate_income()
        self.generate_costs()
        self.generate_tools()
        self.generate_employees()
        self.generate_worker_debts_and_payments()
        self.generate_listings_bids_invoices()
        
        print("\n" + "=" * 60)
        print("✅ GENERACIÓN COMPLETADA")
        print("=" * 60)
        return self.data

# ====================================
# GENERADOR DE SQL
# ====================================

def sql_escape(value: str) -> str:
    """Escapa comillas simples para SQL."""
    if value is None:
        return ""
    return value.replace("'", "''")

def generate_sql(data):
    """Genera scripts SQL para todas las tablas"""
    sql = []
    
    sql.append("-- ============================================")
    sql.append("-- INSERCIÓN DE DATOS GENERADOS")
    sql.append("-- ============================================\n")
    
    # Users
    sql.append("-- Usuarios")
    for u in data["users"]:
        sql.append(
            "INSERT INTO users_user (id, username, email, first_name, last_name, role, is_active, date_joined, password, is_superuser, is_staff, last_login) "
            f"VALUES ({u['id']}, '{sql_escape(u['username'])}', '{sql_escape(u['email'])}', '{sql_escape(u['first_name'])}', '{sql_escape(u['last_name'])}', "
            f"'{sql_escape(u['role'])}', {str(u['is_active']).lower()}, '{u['date_joined']}', 'pbkdf2_sha256$dummy', false, false, NULL);"
        )
    
    # Farms
    sql.append("\n-- Fincas")
    for f in data["farms"]:
        sql.append(
            "INSERT INTO farm_farm (id, name, location, area_hectares, owner_id) "
            f"VALUES ({f['id']}, '{sql_escape(f['name'])}', '{sql_escape(f['location'])}', {f['area_hectares']}, {f['owner_id']});"
        )
    
    # Crops
    sql.append("\n-- Cultivos")
    for c in data["crops"]:
        sql.append(
            "INSERT INTO farm_crop (id, name, variety, planted_at, expected_harvest_at, farm_id) "
            f"VALUES ({c['id']}, '{sql_escape(c['name'])}', '{sql_escape(c['variety'])}', '{c['planted_at']}', '{c['expected_harvest_at']}', {c['farm_id']});"
        )
    
    # Workers
    sql.append("\n-- Trabajadores")
    for w in data["workers"]:
        sql.append(
            "INSERT INTO commerce_worker (id, full_name, document, phone, is_active) "
            f"VALUES ({w['id']}, '{sql_escape(w['full_name'])}', '{sql_escape(w['document'])}', '{sql_escape(w['phone'])}', {str(w['is_active']).lower()});"
        )
    
    # Buyers
    sql.append("\n-- Compradores")
    for b in data["buyers"]:
        sql.append(
            "INSERT INTO commerce_buyer (id, name, email, phone) "
            f"VALUES ({b['id']}, '{sql_escape(b['name'])}', '{sql_escape(b['email'])}', '{sql_escape(b['phone'])}');"
        )
    
    # Production (limitado para no saturar)
    sql.append("\n-- Producción")
    for p in data["production"][:500]:
        sql.append(
            "INSERT INTO farm_production (id, date, quantity_kg, crop_id) "
            f"VALUES ({p['id']}, '{p['date']}', {p['quantity_kg']}, {p['crop_id']});"
        )
    
    # Income
    sql.append("\n-- Ingresos")
    for i in data["income"]:
        sql.append(
            "INSERT INTO farm_income (id, date, source, amount, farm_id) "
            f"VALUES ({i['id']}, '{i['date']}', '{sql_escape(i['source'])}', {i['amount']}, {i['farm_id']});"
        )
    
    # Costs (limitado)
    sql.append("\n-- Costos")
    for c in data["costs"][:500]:
        sql.append(
            "INSERT INTO farm_cost (id, date, category, amount, notes, farm_id) "
            f"VALUES ({c['id']}, '{c['date']}', '{sql_escape(c['category'])}', {c['amount']}, '{sql_escape(c['notes'])}', {c['farm_id']});"
        )
    
    # Tools
    sql.append("\n-- Herramientas")
    for t in data["tools"]:
        sql.append(
            "INSERT INTO farm_tool (id, name, purchase_date, cost, farm_id) "
            f"VALUES ({t['id']}, '{sql_escape(t['name'])}', '{t['purchase_date']}', {t['cost']}, {t['farm_id']});"
        )
    
    # Employees
    sql.append("\n-- Empleados")
    for e in data["employees"]:
        sql.append(
            "INSERT INTO farm_employee (id, full_name, role, daily_rate, farm_id) "
            f"VALUES ({e['id']}, '{sql_escape(e['full_name'])}', '{sql_escape(e['role'])}', {e['daily_rate']}, {e['farm_id']});"
        )
    
    # Worker Debts
    sql.append("\n-- Deudas de trabajadores")
    for d in data["worker_debts"]:
        sql.append(
            "INSERT INTO commerce_workerdebt (id, description, amount, created_at, paid, worker_id) "
            f"VALUES ({d['id']}, '{sql_escape(d['description'])}', {d['amount']}, '{d['created_at']}', {str(d['paid']).lower()}, {d['worker_id']});"
        )
    
    # Worker Payments
    sql.append("\n-- Pagos de trabajadores")
    for p in data["worker_payments"]:
        sql.append(
            "INSERT INTO commerce_workerpayment (id, amount, created_at, note, debt_id, worker_id) "
            f"VALUES ({p['id']}, {p['amount']}, '{p['created_at']}', '{sql_escape(p['note'])}', {p['debt_id']}, {p['worker_id']});"
        )
    
    # Listings
    sql.append("\n-- Listados de venta")
    for l in data["listings"]:
        sql.append(
            "INSERT INTO commerce_listing (id, quantity_kg, min_price_per_kg, is_auction, status, crop_id, seller_id) "
            f"VALUES ({l['id']}, {l['quantity_kg']}, {l['min_price_per_kg']}, {str(l['is_auction']).lower()}, '{sql_escape(l['status'])}', {l['crop_id']}, {l['seller_id']});"
        )
    
    # Bids
    sql.append("\n-- Ofertas")
    for b in data["bids"]:
        sql.append(
            "INSERT INTO commerce_bid (id, price_per_kg, created_at, buyer_id, listing_id) "
            f"VALUES ({b['id']}, {b['price_per_kg']}, '{b['created_at']}', {b['buyer_id']}, {b['listing_id']});"
        )
    
    # Invoices
    sql.append("\n-- Facturas")
    for i in data["invoices"]:
        sql.append(
            "INSERT INTO commerce_invoice (id, total_amount, created_at, is_proforma, buyer_id, listing_id) "
            f"VALUES ({i['id']}, {i['total_amount']}, '{i['created_at']}', {str(i['is_proforma']).lower()}, {i['buyer_id']}, {i['listing_id']});"
        )
    
    return "\n".join(sql)

# ====================================
# EJECUCIÓN PRINCIPAL
# ====================================

if __name__ == "__main__":
    try:
        # Generar datos
        generator = DataGenerator()
        data = generator.generate_all()
        
        # Calcular totales
        total_produccion = sum(p["quantity_kg"] for p in data["production"])
        total_ingresos = sum(i["amount"] for i in data["income"])
        total_costos = sum(c["amount"] for c in data["costs"])
        total_deudas_pendientes = sum(d["amount"] for d in data["worker_debts"] if not d["paid"])
        
        print(f"\n📊 RESUMEN:")
        print(f"  Usuarios: {len(data['users'])}")
        print(f"  Fincas: {len(data['farms'])}")
        print(f"  Cultivos: {len(data['crops'])}")
        print(f"  Trabajadores: {len(data['workers'])}")
        print(f"  Compradores: {len(data['buyers'])}")
        print(f"  Registros de producción: {len(data['production'])}")
        print(f"  Producción total: {total_produccion:,} kg")
        print(f"  Ingresos totales: ${total_ingresos:,}")
        print(f"  Costos totales: ${total_costos:,}")
        print(f"  Balance: ${total_ingresos - total_costos:,}")
        print(f"  Deudas pendientes: ${total_deudas_pendientes:,}")
        
        # Guardar JSON
        with open('datos_completos.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("\n✅ Guardado: datos_completos.json")
        
        # Guardar SQL
        sql_script = generate_sql(data)
        with open('inserts_completos.sql', 'w', encoding='utf-8') as f:
            f.write(sql_script)
        print("✅ Guardado: inserts_completos.sql")
        
        print("\n" + "=" * 60)
        print("🎉 PROCESO COMPLETADO")
        print("=" * 60)
        
    except ImportError:
        print("\n⚠️  Necesitas instalar 'faker':")
        print("   pip install faker")
