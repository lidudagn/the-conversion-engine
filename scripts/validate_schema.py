import json
import jsonschema
from jsonschema import validate

def validate_schema():
    with open('data/schemas/hiring_signal_brief.schema.json', 'r') as f:
        schema = json.load(f)
    
    with open('data/schemas/sample_hiring_signal_brief.json', 'r') as f:
        sample = json.load(f)
    
    try:
        validate(instance=sample, schema=schema)
        print("Validation successful!")
    except jsonschema.exceptions.ValidationError as err:
        print("Validation failed!")
        print(err)

if __name__ == "__main__":
    validate_schema()
