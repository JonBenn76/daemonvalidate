from typing import Dict, Any, Type, Tuple
from pydantic import create_model, BaseModel

# Map clean configuration strings to core Python types
TYPE_MAPPING: Dict[str, Type] = {
    "string": str,
    "integer": int,
    "float": float,
    "boolean": bool
}

def compile_dynamic_model(model_name: str, schema_definition: Dict[str, Any]) -> Type[BaseModel]:
    """
    Compiles a raw configuration schema shape into a strict, executable Pydantic model.
    
    Expected schema_definition format:
        {
            "fields": {
                "transaction_id": "string",
                "total_revenue": "float",
                "quantity": "integer"
            }
        }
    """
    fields_config = schema_definition.get("fields")
    if not fields_config or not isinstance(fields_config, dict):
        raise ValueError("Invalid schema layout. A 'fields' dictionary mapping must be provided.")

    pydantic_fields: Dict[str, Tuple[Type, Any]] = {}
    
    for field_name, type_str in fields_config.items():
        if not isinstance(type_str, str):
            raise ValueError(f"Field type for '{field_name}' must be a string descriptor.")
            
        target_type = TYPE_MAPPING.get(type_str.lower())
        if target_type is None:
            raise ValueError(
                f"Unsupported data type '{type_str}' for field '{field_name}'. "
                f"Supported types are: {list(TYPE_MAPPING.keys())}"
            )
            
        # Pydantic field definitions use a tuple: (type, default_value)
        # Using ... (Ellipsis) specifies that the field is strictly REQUIRED.
        pydantic_fields[field_name] = (target_type, ...)
        
    # Dynamically build and return the Pydantic BaseModel class
    return create_model(model_name, **pydantic_fields)  # type: ignore