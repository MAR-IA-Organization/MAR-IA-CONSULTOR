-- seed_database.sql
-- Script para llenar la base de datos con datos de prueba realistas
-- Ejecutar con: psql -h HOST -U USER -d agrodb -f seed_database.sql

-- ============================================
-- LIMPIEZA (OPCIONAL - comentar si no quieres borrar datos existentes)
-- ============================================
-- TRUNCATE TABLE commerce_workerpayment, commerce_workerdebt, commerce_worker,
--          commerce_invoice, commerce_bid, commerce_listing, commerce_marketprice,
--          farm_production, farm_cost, farm_income, farm_tool, farm_employee,
--          farm_crop, farm_farm, commerce_buyer, users_user CASCADE;

-- ============================================
-- 1. USUARIOS (users_user)
-- ============================================
INSERT INTO users_user (id, password, username, email, first_name, last_name, is_staff, is_active, is_superuser, date_joined, role)
VALUES
  (1, 'pbkdf2_sha256$260000$dummy', 'admin', 'admin@agrodb.com', 'Carlos', 'Administrador', true, true, true, '2024-01-01 10:00:00-05', 'admin'),
  (2, 'pbkdf2_sha256$260000$dummy', 'juan.farmer', 'juan@finca.com', 'Juan', 'Pérez', false, true, false, '2024-01-15 08:30:00-05', 'farmer'),
  (3, 'pbkdf2_sha256$260000$dummy', 'maria.seller', 'maria@campo.com', 'María', 'González', false, true, false, '2024-02-01 09:00:00-05', 'seller'),
  (4, 'pbkdf2_sha256$260000$dummy', 'pedro.buyer', 'pedro@comercio.com', 'Pedro', 'Ramírez', false, true, false, '2024-02-10 11:00:00-05', 'buyer'),
  (5, 'pbkdf2_sha256$260000$dummy', 'ana.admin', 'ana@agrodb.com', 'Ana', 'López', true, true, false, '2024-03-01 07:00:00-05', 'admin')
ON CONFLICT (id) DO NOTHING;

-- Actualizar secuencia
SELECT setval('users_user_id_seq', (SELECT MAX(id) FROM users_user));

-- ============================================
-- 2. COMPRADORES (commerce_buyer)
-- ============================================
INSERT INTO commerce_buyer (id, name, email, phone)
VALUES
  (1, 'Distribuidora El Valle S.A.S', 'ventas@elvalle.com', '+57 312 456 7890'),
  (2, 'Supermercados Frescos Ltda', 'compras@superfrescos.com', '+57 315 234 5678'),
  (3, 'Exportadora Andina', 'export@andina.co', '+57 320 987 6543'),
  (4, 'Mercado Central de Abastos', 'mercado@abastos.com', '+57 318 765 4321'),
  (5, 'Comercializadora AgroMax', 'info@agromax.com', '+57 314 555 6789'),
  (6, 'Procesadora de Alimentos Del Campo', 'delcampo@alimentos.com', '+57 316 444 5555'),
  (7, 'Tiendas Naturales Vida Sana', 'vidasana@natural.com', '+57 319 333 4444'),
  (8, 'Restaurantes Gourmet Unidos', 'compras@gourmet.com', '+57 321 222 3333'),
  (9, 'Cooperativa de Consumo Popular', 'coop@popular.com', '+57 313 111 2222'),
  (10, 'Industrias de Jugos y Conservas', 'jugos@industrias.com', '+57 317 999 8888')
ON CONFLICT (id) DO NOTHING;

SELECT setval('commerce_buyer_id_seq', (SELECT MAX(id) FROM commerce_buyer));

-- ============================================
-- 3. FINCAS (farm_farm)
-- ============================================
INSERT INTO farm_farm (id, name, location, area_hectares, owner_id)
VALUES
  (1, 'Finca La Esperanza', 'Palmira, Valle del Cauca', 25.5, 2),
  (2, 'Hacienda El Roble', 'Buga, Valle del Cauca', 50.0, 3),
  (3, 'Finca Santa Rosa', 'Tuluá, Valle del Cauca', 15.8, 2),
  (4, 'Granja Orgánica Los Pinos', 'Caicedonia, Valle del Cauca', 10.2, 3),
  (5, 'Finca Villa Nueva', 'Sevilla, Valle del Cauca', 32.0, 2)
ON CONFLICT (id) DO NOTHING;

SELECT setval('farm_farm_id_seq', (SELECT MAX(id) FROM farm_farm));

-- ============================================
-- 4. CULTIVOS (farm_crop)
-- ============================================
INSERT INTO farm_crop (id, name, variety, planted_at, expected_harvest_at, farm_id)
VALUES
  (1, 'Café', 'Arabica Castillo', '2023-06-15', '2024-10-15', 1),
  (2, 'Plátano', 'Hartón', '2023-09-01', '2024-06-01', 1),
  (3, 'Aguacate', 'Hass', '2023-01-10', '2025-01-10', 2),
  (4, 'Cacao', 'Criollo', '2023-03-20', '2025-09-20', 2),
  (5, 'Tomate', 'Chonto', '2024-01-15', '2024-05-15', 3),
  (6, 'Pimentón', 'Rojo', '2024-02-01', '2024-06-01', 3),
  (7, 'Maíz', 'Amarillo', '2024-03-10', '2024-07-10', 4),
  (8, 'Frijol', 'Cargamanto', '2024-03-15', '2024-07-15', 4),
  (9, 'Papaya', 'Maradol', '2023-11-20', '2024-08-20', 5),
  (10, 'Limón', 'Tahití', '2023-08-05', '2024-11-05', 5)
ON CONFLICT (id) DO NOTHING;

SELECT setval('farm_crop_id_seq', (SELECT MAX(id) FROM farm_crop));

-- ============================================
-- 5. EMPLEADOS (farm_employee)
-- ============================================
INSERT INTO farm_employee (id, full_name, role, daily_rate, farm_id)
VALUES
  (1, 'Jorge Luis Moreno', 'Recolector', 50000, 1),
  (2, 'Sandra Milena Cruz', 'Supervisora', 80000, 1),
  (3, 'Carlos Alberto Díaz', 'Operario', 55000, 2),
  (4, 'Rosa Elena Vargas', 'Recolectora', 50000, 2),
  (5, 'Miguel Ángel Torres', 'Tractorista', 70000, 2),
  (6, 'Lucía Patricia Rojas', 'Empacadora', 45000, 3),
  (7, 'David Fernando Soto', 'Aplicador fitosanitario', 60000, 3),
  (8, 'Gloria Isabel Méndez', 'Recolectora', 50000, 4),
  (9, 'Andrés Felipe Castro', 'Operario general', 55000, 4),
  (10, 'Carmen Liliana Pardo', 'Seleccionadora', 48000, 5)
ON CONFLICT (id) DO NOTHING;

SELECT setval('farm_employee_id_seq', (SELECT MAX(id) FROM farm_employee));

-- ============================================
-- 6. HERRAMIENTAS (farm_tool)
-- ============================================
INSERT INTO farm_tool (id, name, purchase_date, cost, farm_id)
VALUES
  (1, 'Motosierra Stihl MS 170', '2023-05-10', 1200000, 1),
  (2, 'Fumigadora de espalda 20L', '2023-06-15', 350000, 1),
  (3, 'Tractor John Deere 5045E', '2022-08-20', 65000000, 2),
  (4, 'Guadañadora Honda UMK425', '2023-09-05', 1800000, 2),
  (5, 'Sistema de riego por goteo', '2023-10-12', 5500000, 3),
  (6, 'Carretilla motorizada', '2024-01-08', 2300000, 3),
  (7, 'Despulpadora de café', '2023-07-20', 3200000, 1),
  (8, 'Báscula digital 500kg', '2023-11-15', 850000, 2),
  (9, 'Arado de discos', '2023-04-25', 4500000, 2),
  (10, 'Bomba de agua diesel', '2024-02-10', 3800000, 5)
ON CONFLICT (id) DO NOTHING;

SELECT setval('farm_tool_id_seq', (SELECT MAX(id) FROM farm_tool));

-- ============================================
-- 7. PRODUCCIÓN (farm_production)
-- ============================================
INSERT INTO farm_production (id, date, quantity_kg, crop_id)
VALUES
  (1, '2024-10-15', 850.5, 1),
  (2, '2024-10-20', 920.0, 1),
  (3, '2024-06-05', 1200.0, 2),
  (4, '2024-06-12', 980.5, 2),
  (5, '2024-05-18', 450.0, 5),
  (6, '2024-05-25', 520.5, 5),
  (7, '2024-06-03', 380.0, 6),
  (8, '2024-07-12', 650.0, 7),
  (9, '2024-07-18', 420.5, 8),
  (10, '2024-08-22', 890.0, 9),
  (11, '2024-10-22', 780.0, 1),
  (12, '2024-10-25', 850.0, 1),
  (13, '2024-06-18', 1100.0, 2),
  (14, '2024-05-30', 480.0, 5),
  (15, '2024-08-28', 920.0, 9)
ON CONFLICT (id) DO NOTHING;

SELECT setval('farm_production_id_seq', (SELECT MAX(id) FROM farm_production));

-- ============================================
-- 8. COSTOS (farm_cost)
-- ============================================
INSERT INTO farm_cost (id, date, category, amount, notes, farm_id)
VALUES
  (1, '2024-01-05', 'Semillas', 450000, 'Semillas de tomate certificadas', 3),
  (2, '2024-01-10', 'Fertilizantes', 850000, 'Abono orgánico y NPK', 1),
  (3, '2024-02-03', 'Mano de obra', 2500000, 'Jornales febrero', 1),
  (4, '2024-02-15', 'Pesticidas', 320000, 'Fungicida preventivo', 2),
  (5, '2024-03-01', 'Combustible', 450000, 'Diesel para maquinaria', 2),
  (6, '2024-03-05', 'Mano de obra', 2800000, 'Jornales marzo', 2),
  (7, '2024-04-10', 'Riego', 180000, 'Mantenimiento sistema riego', 3),
  (8, '2024-04-20', 'Transporte', 350000, 'Flete de insumos', 3),
  (9, '2024-05-02', 'Mano de obra', 1950000, 'Jornales mayo', 4),
  (10, '2024-05-15', 'Empaques', 220000, 'Cajas y mallas para cosecha', 3),
  (11, '2024-06-01', 'Mano de obra', 3200000, 'Jornales junio - cosecha', 1),
  (12, '2024-06-08', 'Transporte', 580000, 'Flete de cosecha', 1),
  (13, '2024-07-12', 'Fertilizantes', 620000, 'Fertilización post-cosecha', 2),
  (14, '2024-08-05', 'Mantenimiento', 450000, 'Reparación tractor', 2),
  (15, '2024-09-10', 'Seguros', 1200000, 'Póliza agrícola anual', 2)
ON CONFLICT (id) DO NOTHING;

SELECT setval('farm_cost_id_seq', (SELECT MAX(id) FROM farm_cost));

-- ============================================
-- 9. INGRESOS (farm_income)
-- ============================================
INSERT INTO farm_income (id, date, source, amount, farm_id)
VALUES
  (1, '2024-06-10', 'Venta plátano', 4500000, 1),
  (2, '2024-06-20', 'Venta plátano', 3800000, 1),
  (3, '2024-05-22', 'Venta tomate', 2650000, 3),
  (4, '2024-06-05', 'Venta pimentón', 1980000, 3),
  (5, '2024-07-15', 'Venta maíz', 3200000, 4),
  (6, '2024-07-20', 'Venta frijol', 2100000, 4),
  (7, '2024-08-25', 'Venta papaya', 4200000, 5),
  (8, '2024-10-18', 'Venta café pergamino', 8500000, 1),
  (9, '2024-10-23', 'Venta café pergamino', 7850000, 1),
  (10, '2024-06-25', 'Venta plátano', 4100000, 1)
ON CONFLICT (id) DO NOTHING;

SELECT setval('farm_income_id_seq', (SELECT MAX(id) FROM farm_income));

-- ============================================
-- 10. PRECIOS DE MERCADO (commerce_marketprice)
-- ============================================
INSERT INTO commerce_marketprice (id, crop_name, price_per_kg, observed_at)
VALUES
  (1, 'Café pergamino', 9800, '2024-10-01 08:00:00-05'),
  (2, 'Café pergamino', 10200, '2024-10-15 08:00:00-05'),
  (3, 'Plátano hartón', 1800, '2024-06-01 08:00:00-05'),
  (4, 'Plátano hartón', 1950, '2024-06-15 08:00:00-05'),
  (5, 'Aguacate Hass', 6500, '2024-05-01 08:00:00-05'),
  (6, 'Aguacate Hass', 7200, '2024-05-15 08:00:00-05'),
  (7, 'Tomate chonto', 3200, '2024-05-01 08:00:00-05'),
  (8, 'Tomate chonto', 3500, '2024-05-15 08:00:00-05'),
  (9, 'Pimentón', 4800, '2024-06-01 08:00:00-05'),
  (10, 'Maíz amarillo', 2200, '2024-07-01 08:00:00-05'),
  (11, 'Frijol cargamanto', 8500, '2024-07-01 08:00:00-05'),
  (12, 'Papaya', 2800, '2024-08-01 08:00:00-05'),
  (13, 'Limón tahití', 3500, '2024-08-01 08:00:00-05'),
  (14, 'Café pergamino', 10500, '2024-10-25 08:00:00-05'),
  (15, 'Plátano hartón', 2100, '2024-06-25 08:00:00-05')
ON CONFLICT (id) DO NOTHING;

SELECT setval('commerce_marketprice_id_seq', (SELECT MAX(id) FROM commerce_marketprice));

-- ============================================
-- 11. LISTADOS DE VENTA (commerce_listing)
-- ============================================
INSERT INTO commerce_listing (id, quantity_kg, min_price_per_kg, is_auction, status, crop_id, seller_id)
VALUES
  (1, 850.5, 10000, false, 'vendido', 1, 2),
  (2, 920.0, 10200, true, 'vendido', 1, 2),
  (3, 1200.0, 1800, false, 'vendido', 2, 2),
  (4, 980.5, 1900, false, 'vendido', 2, 2),
  (5, 450.0, 3200, false, 'vendido', 5, 2),
  (6, 520.5, 3400, false, 'vendido', 5, 2),
  (7, 380.0, 4800, false, 'vendido', 6, 2),
  (8, 650.0, 2200, true, 'vendido', 7, 3),
  (9, 420.5, 8500, false, 'vendido', 8, 3),
  (10, 890.0, 2800, false, 'vendido', 9, 3),
  (11, 780.0, 10300, false, 'activo', 1, 2),
  (12, 500.0, 2000, false, 'activo', 2, 2),
  (13, 300.0, 3500, true, 'en_subasta', 5, 2)
ON CONFLICT (id) DO NOTHING;

SELECT setval('commerce_listing_id_seq', (SELECT MAX(id) FROM commerce_listing));

-- ============================================
-- 12. OFERTAS (commerce_bid)
-- ============================================
INSERT INTO commerce_bid (id, price_per_kg, created_at, buyer_id, listing_id)
VALUES
  (1, 10250, '2024-10-20 10:30:00-05', 1, 2),
  (2, 10300, '2024-10-20 11:00:00-05', 3, 2),
  (3, 10400, '2024-10-20 11:30:00-05', 1, 2),
  (4, 2250, '2024-07-12 09:00:00-05', 2, 8),
  (5, 2300, '2024-07-12 09:30:00-05', 4, 8),
  (6, 3600, '2024-10-26 10:00:00-05', 5, 13),
  (7, 3650, '2024-10-26 10:30:00-05', 6, 13),
  (8, 3700, '2024-10-26 11:00:00-05', 5, 13)
ON CONFLICT (id) DO NOTHING;

SELECT setval('commerce_bid_id_seq', (SELECT MAX(id) FROM commerce_bid));

-- ============================================
-- 13. FACTURAS (commerce_invoice)
-- ============================================
INSERT INTO commerce_invoice (id, total_amount, created_at, is_proforma, buyer_id, listing_id)
VALUES
  (1, 8505000, '2024-10-18 14:00:00-05', false, 1, 1),
  (2, 9568000, '2024-10-21 15:30:00-05', false, 1, 2),
  (3, 2160000, '2024-06-10 16:00:00-05', false, 2, 3),
  (4, 1862950, '2024-06-20 14:30:00-05', false, 2, 4),
  (5, 1440000, '2024-05-22 13:00:00-05', false, 4, 5),
  (6, 1769700, '2024-06-01 11:30:00-05', false, 4, 6),
  (7, 1824000, '2024-06-05 15:00:00-05', false, 5, 7),
  (8, 1495000, '2024-07-15 16:30:00-05', false, 2, 8),
  (9, 3574250, '2024-07-20 14:00:00-05', false, 6, 9),
  (10, 2492000, '2024-08-25 13:30:00-05', false, 7, 10),
  (11, 1050000, '2024-10-26 10:00:00-05', true, 5, 12)
ON CONFLICT (id) DO NOTHING;

SELECT setval('commerce_invoice_id_seq', (SELECT MAX(id) FROM commerce_invoice));

-- ============================================
-- 14. TRABAJADORES (commerce_worker)
-- ============================================
INSERT INTO commerce_worker (id, full_name, document, phone, is_active)
VALUES
  (1, 'Luis Fernando Gómez', '1234567890', '+57 310 111 2222', true),
  (2, 'Martha Cecilia Ruiz', '9876543210', '+57 311 333 4444', true),
  (3, 'Roberto Carlos Muñoz', '5556667778', '+57 312 555 6666', true),
  (4, 'Diana Patricia Silva', '1112223334', '+57 313 777 8888', false),
  (5, 'Hernán Darío Ortiz', '9998887776', '+57 314 999 0000', true)
ON CONFLICT (id) DO NOTHING;

SELECT setval('commerce_worker_id_seq', (SELECT MAX(id) FROM commerce_worker));

-- ============================================
-- 15. DEUDAS DE TRABAJADORES (commerce_workerdebt)
-- ============================================
INSERT INTO commerce_workerdebt (id, description, amount, created_at, paid, worker_id)
VALUES
  (1, 'Adelanto de sueldo septiembre', 300000, '2024-09-10', true, 1),
  (2, 'Préstamo personal', 500000, '2024-08-15', false, 2),
  (3, 'Adelanto de sueldo octubre', 250000, '2024-10-05', false, 3),
  (4, 'Compra de herramientas', 180000, '2024-07-20', true, 1),
  (5, 'Préstamo de emergencia', 400000, '2024-09-25', false, 5)
ON CONFLICT (id) DO NOTHING;

SELECT setval('commerce_workerdebt_id_seq', (SELECT MAX(id) FROM commerce_workerdebt));

-- ============================================
-- 16. PAGOS A TRABAJADORES (commerce_workerpayment)
-- ============================================
INSERT INTO commerce_workerpayment (id, amount, created_at, note, debt_id, worker_id)
VALUES
  (1, 300000, '2024-09-30 17:00:00-05', 'Pago completo adelanto septiembre', 1, 1),
  (2, 250000, '2024-09-01 17:00:00-05', 'Abono préstamo personal', 2, 2),
  (3, 180000, '2024-08-05 17:00:00-05', 'Pago herramientas', 4, 1),
  (4, 100000, '2024-10-10 17:00:00-05', 'Abono adelanto octubre', 3, 3)
ON CONFLICT (id) DO NOTHING;

SELECT setval('commerce_workerpayment_id_seq', (SELECT MAX(id) FROM commerce_workerpayment));

-- ============================================
-- 17. MENSAJES DE CHAT (chat_chatmessage)
-- ============================================
INSERT INTO chat_chatmessage (id, role, content, created_at, user_id)
VALUES
  (1, 'user', '¿Cuántos compradores tengo?', '2024-10-24 10:00:00-05', 2),
  (2, 'assistant', 'Tienes 10 compradores registrados en el sistema.', '2024-10-24 10:00:05-05', 2),
  (3, 'user', 'Muéstrame las últimas 5 facturas', '2024-10-24 10:05:00-05', 2),
  (4, 'assistant', 'Aquí están las últimas 5 facturas...', '2024-10-24 10:05:08-05', 2),
  (5, 'user', '¿Cuál es el total de ventas del mes?', '2024-10-24 10:10:00-05', 3)
ON CONFLICT (id) DO NOTHING;

SELECT setval('chat_chatmessage_id_seq', (SELECT MAX(id) FROM chat_chatmessage));

-- ============================================
-- RESUMEN DE DATOS INSERTADOS
-- ============================================
DO $$
DECLARE
    v_users INT;
    v_buyers INT;
    v_farms INT;
    v_crops INT;
    v_listings INT;
    v_invoices INT;
BEGIN
    SELECT COUNT(*) INTO v_users FROM users_user;
    SELECT COUNT(*) INTO v_buyers FROM commerce_buyer;
    SELECT COUNT(*) INTO v_farms FROM farm_farm;
    SELECT COUNT(*) INTO v_crops FROM farm_crop;
    SELECT COUNT(*) INTO v_listings FROM commerce_listing;
    SELECT COUNT(*) INTO v_invoices FROM commerce_invoice;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'DATOS DE PRUEBA INSERTADOS EXITOSAMENTE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Usuarios: %', v_users;
    RAISE NOTICE 'Compradores: %', v_buyers;
    RAISE NOTICE 'Fincas: %', v_farms;
    RAISE NOTICE 'Cultivos: %', v_crops;
    RAISE NOTICE 'Listados: %', v_listings;
    RAISE NOTICE 'Facturas: %', v_invoices;
    RAISE NOTICE '========================================';
END $$;
