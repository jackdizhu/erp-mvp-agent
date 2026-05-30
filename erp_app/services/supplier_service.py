from erp_app.db import query_supplier, query_all_suppliers
from erp_app.errors import data_invalid_supplier


def get_supplier_service(supplier_id: str) -> dict:
    result = query_supplier(supplier_id)
    if not result:
        raise ValueError(data_invalid_supplier(supplier_id))
    return {"success": True, "data": result}


def list_suppliers_service() -> dict:
    results = query_all_suppliers()
    return {"success": True, "data": results}
