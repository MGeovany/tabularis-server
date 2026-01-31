# Arquitectura: Service + Repository y patrones de diseño

## Service + Repository

- **Repository**: acceso a datos (CRUD). No lógica de negocio.
  - `app/repositories/user_repository.py` — UserRepository
  - `app/repositories/conversion_repository.py` — ConversionRepository
  - `app/repositories/audit_log_repository.py` — AuditLogRepository
- **Service**: orquesta repositorios y reglas de negocio.
  - Los endpoints (API) llaman a **Services**; los Services usan **Repositories** y otros componentes (Strategy, Policy, Builder).

Flujo: **API (router) → Service → Repository → DB**.

---

## Strategy: extracción de tablas PDF

Intercambiable según el tipo de PDF (por ejemplo pdfplumber vs camelot).

- **`TableExtractorStrategy`** (abstracto): `get_page_count(content)`, `extract_tables(content) -> TablesByPage`.
- **`PdfplumberTableExtractor`**: implementación con pdfplumber.

El **ConversionService** recibe una estrategia por constructor; en producción se inyecta `PdfplumberTableExtractor` (en `dependencies.get_conversion_service`). Para añadir otra librería se crea una nueva clase que implemente `TableExtractorStrategy`.

---

## Policy: planes Free / Pro

Reglas de uso por plan sin `if plan == "FREE"` en el servicio.

- **`UsagePolicy`** (abstracto): `can_convert(user) -> bool`, `limit_exceeded_message() -> str`.
- **`FreePlanPolicy`**: límite fijo (ej. 10 conversiones).
- **`ProPlanPolicy`**: usa `user.conversions_limit` (0 = ilimitado).
- **`get_usage_policy(plan)`**: devuelve la política según el nombre del plan.

El servicio de uso (`usage_limits.check_can_convert`) usa `get_usage_policy(user.plan).can_convert(user)` y el mensaje de la política si se supera el límite.

---

## Builder: exportación a Excel

Construcción paso a paso del XLSX (hojas y tablas).

- **`ExcelExportBuilder`**: `add_sheet(name)`, `add_table(rows)`, `build() -> bytes`.
- Encadenable: `builder.add_sheet("Page 1").add_table(rows).add_table(rows2).build()`.

El **ConversionService** crea un builder, recorre las tablas extraídas (Strategy), va añadiendo hojas y tablas, y al final llama a `build()` para obtener los bytes del XLSX.

---

## Resumen de dependencias

| Componente        | Usa                                                                                                   |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| API (convert)     | ConversionService, Repos, Policy (vía check_can_convert)                                              |
| ConversionService | TableExtractorStrategy, ExcelExportBuilder (interno)                                                  |
| usage_limits      | get_usage_policy(plan)                                                                                |
| dependencies      | UserRepository, ConversionRepository, AuditLogRepository, ConversionService(PdfplumberTableExtractor) |
