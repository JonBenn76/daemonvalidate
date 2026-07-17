import pytest
from pydantic import ValidationError
from daemonvalidate.models import compile_dynamic_model

def test_dynamic_model_compilation_and_coercion():
    # 1. Define a mock configuration schema layout
    mock_schema = {
        "fields": {
            "transaction_id": "string",
            "amount": "float",
            "quantity": "integer",
            "is_retail": "boolean"
        }
    }
    
    # 2. Compile our dynamic model class
    SalesModel = compile_dynamic_model("SalesModel", mock_schema)
    
    # 3. Test a clean payload where types match or can be cleanly coerced
    valid_payload = {
        "transaction_id": "TXN-001",
        "amount": "125.50",  # String float -> coerced to float
        "quantity": 3,
        "is_retail": "true"  # String boolean -> coerced to True
    }
    
    instance = SalesModel(**valid_payload)
    
    assert instance.transaction_id == "TXN-001"
    assert instance.amount == 125.50
    assert instance.quantity == 3
    assert instance.is_retail is True


def test_dynamic_model_missing_required_fields():
    mock_schema = {
        "fields": {
            "transaction_id": "string",
            "amount": "float"
        }
    }
    SalesModel = compile_dynamic_model("SalesModel", mock_schema)
    
    # Missing 'amount' which is required
    invalid_payload = {"transaction_id": "TXN-002"}
    
    with pytest.raises(ValidationError) as exc_info:
        SalesModel(**invalid_payload)
        
    assert "Field required" in str(exc_info.value)


def test_dynamic_model_invalid_types():
    mock_schema = {
        "fields": {
            "quantity": "integer"
        }
    }
    SalesModel = compile_dynamic_model("SalesModel", mock_schema)
    
    # Passing text that cannot be parsed as an integer
    invalid_payload = {"quantity": "not_a_number"}
    
    with pytest.raises(ValidationError):
        SalesModel(**invalid_payload)