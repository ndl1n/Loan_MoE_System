class Field:
    def __init__(self, name, required=True, ftype=str, validator=None):
        self.name = name
        self.required = required
        self.type = ftype
        self.validator = validator

class FieldSchema:

    def __init__(self):
        self.fields = {
            "name": Field("name"),
            "id": Field("id"),
            "phone": Field("phone", validator="phone"),
            "loan_purpose": Field("loan_purpose"),
            "job": Field("job"),
            "income": Field("income", ftype=int),
            "amount": Field("amount", ftype=int)
        }

    def get_missing_fields(self, profile_state):
        missing = []
        for k, field in self.fields.items():
            if field.required and not profile_state.get(k):
                missing.append(k)
        return missing

    def all_required_filled(self, profile_state):
        return len(self.get_missing_fields(profile_state)) == 0
