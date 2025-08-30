import json
from django.contrib.admin.widgets import AdminTextareaWidget


class PrettyJSONWidget(AdminTextareaWidget):
    def format_value(self, value):
        if value in ("", None):
            return ""
        try:
            # Si ya viene como dict/list (JSONField), formatea
            if not isinstance(value, str):
                return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
            # Si viene string, intenta cargar y re-formatear
            return json.dumps(
                json.loads(value), indent=2, ensure_ascii=False, sort_keys=True
            )
        except Exception:
            # Si no es JSON válido, muestra tal cual para no ocultar el error
            return value
