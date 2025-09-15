from django import forms
from apps.preinscriptions.models import Preinscripcion

# Mapeo: nombre_en_form -> nombre_en_modelo
FIELD_MAP = {
    "titulo_legalizado": "doc_fotocopia_titulo_legalizada",
    "analitico_legalizado": "doc_fotocopia_analitico_legalizado",
    "fotos_4x4": "doc_fotos_4x4",
    "titulo_terciario_universitario": "doc_titulo_secundario",  # o el que corresponda en tu modelo
    "cert_alumno_regular": "doc_cert_alumno_regular",
    "titulo_en_tramite": "doc_cert_titulo_en_tramite",
    "tres_folios": "doc_folios",
    "adeuda_materias": "doc_adeuda_materias",
    "escuela": "doc_adeuda_materias_escuela",
    "detalle": "doc_adeuda_materias_detalle",
    "buena_salud": "doc_buena_salud",                # si existe en el modelo
    "declaracion_jurada": "doc_declaracion_jurada",  # si existe en el modelo
}

class PreAutorizarForm(forms.ModelForm):
    # Campos “humanos” que vienen de la plantilla
    titulo_legalizado = forms.BooleanField(required=False, label="Título legalizado")
    analitico_legalizado = forms.BooleanField(required=False, label="Analítico legalizado")
    fotos_4x4 = forms.BooleanField(required=False, label="2 fotos 4x4")
    titulo_terciario_universitario = forms.BooleanField(required=False, label="Título terciario/universitario")
    cert_alumno_regular = forms.BooleanField(required=False, label="Cert. alumno regular")
    titulo_en_tramite = forms.BooleanField(required=False, label="Título en trámite")
    tres_folios = forms.BooleanField(required=False, label="3 folios")
    adeuda_materias = forms.BooleanField(required=False, label="Adeuda materias")
    escuela = forms.CharField(required=False, label="Escuela")
    detalle = forms.CharField(required=False, widget=forms.Textarea, label="Detalle")
    buena_salud = forms.BooleanField(required=False, label="Buena salud")
    declaracion_jurada = forms.BooleanField(required=False, label="Declaración jurada")

    class Meta:
        model = Preinscripcion
        # Solo campos que 100% existen en el modelo
        fields = ["estado"]  # agregá aquí otros campos REALES que quieras editar

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inicializar los campos “humanos” con el valor del modelo
        inst = self.instance
        if inst and inst.pk:
            for form_name, model_name in FIELD_MAP.items():
                if form_name in self.fields and hasattr(inst, model_name):
                    self.fields[form_name].initial = getattr(inst, model_name)

    def save(self, commit=True):
        inst = super().save(commit=False)
        # Pasar del nombre “humano” al campo real del modelo
        for form_name, model_name in FIELD_MAP.items():
            if hasattr(inst, model_name) and form_name in self.cleaned_data:
                setattr(inst, model_name, self.cleaned_data[form_name])
        if commit:
            inst.save()
        return inst