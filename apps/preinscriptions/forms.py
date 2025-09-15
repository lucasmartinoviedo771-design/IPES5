import io, os
import re
from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
from .models import Preinscripcion
from .logic import compute_condicion_admin, is_docente_track

try:
    from apps.academics.models import Carrera
except Exception:
    Carrera = None

def validar_dni(valor: str) -> str:
    s = "".join(ch for ch in str(valor) if ch.isdigit())
    if not (7 <= len(s) <= 8):
        raise ValidationError("DNI inválido (7-8 dígitos)")
    return s

def validar_cuit(cuit: str) -> str:
    s = "".join(ch for ch in str(cuit) if ch.isdigit())
    if len(s) != 11:
        raise ValidationError("CUIL/CUIT inválido (11 dígitos)")
    pesos = [5,4,3,2,7,6,5,4,3,2]
    suma = sum(int(d)*p for d,p in zip(s[:10], pesos))
    dv = 11 - (suma % 11)
    dv = {10: 9, 11: 0}.get(dv, dv)
    if dv != int(s[10]):
        raise ValidationError("CUIL/CUIT inválido (dígito verificador)")
    return f"{s[:2]}-{s[2:10]}-{s[10:]}"

class PreinscripcionForm(forms.ModelForm):
    localidad_nac = forms.CharField(max_length=80, required=True)
    provincia_nac = forms.CharField(max_length=80, required=True)
    pais_nac = forms.CharField(max_length=80, required=True)

    class Meta:
        model = Preinscripcion
        # Incluir SOLO campos que carga el/la estudiante en la preinscripción
        fields = [
            "carrera",
            "cuil", "dni", "apellido", "nombres",
            "fecha_nacimiento", "estado_civil",
            "localidad_nac", "provincia_nac", "pais_nac", "nacionalidad",
            "domicilio", "tel_fijo", "tel_movil", "email",
            # "contacto_emergencia_telefono", "contacto_emergencia_parentesco",
            "trabaja", "empleador", "horario_trabajo", "domicilio_trabajo",
            # Estudios secundarios
            "sec_titulo", "sec_establecimiento", "sec_fecha_egreso",
            "sec_localidad", "sec_provincia", "sec_pais",
            # Estudios superiores (opcionales)
            "sup1_titulo", "sup1_establecimiento", "sup1_fecha_egreso",
            "sup1_localidad", "sup1_provincia", "sup1_pais",
            "sup2_titulo", "sup2_establecimiento", "sup2_fecha_egreso",
            "sup2_localidad", "sup2_provincia", "sup2_pais",
            # Foto
            "foto_4x4",
        ]
        widgets = {
            "cuil": forms.TextInput(attrs={
                "placeholder": "00-00000000-0",
                "autocomplete": "off",
            }),
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
            "sec_fecha_egreso": forms.DateInput(attrs={"type": "date"}),
            "sup1_fecha_egreso": forms.DateInput(attrs={"type": "date"}),
            "sup2_fecha_egreso": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "carrera" in self.fields and Carrera is not None:
            try:
                self.fields["carrera"].queryset = Carrera.objects.filter(activa=True).order_by("nombre")
            except Exception:
                self.fields["carrera"].queryset = Carrera.objects.none()
        if "foto_4x4" in self.fields:
            self.fields["foto_4x4"].widget.attrs.update({"accept": "image/*"})

        # Asegurar placeholders para todos los campos de texto/email/fecha
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.DateInput)):
                field.widget.attrs.setdefault("placeholder", field.label)
            elif isinstance(field.widget, forms.Select):
                # Para los Select, el placeholder es la primera opción vacía
                field.empty_label = field.label

    def clean_dni(self):
        return validar_dni(self.cleaned_data.get("dni"))

    def clean_cuil(self):
        val = self.cleaned_data.get("cuil")
        if val:
            return validar_cuit(val)
        return val

    def clean_foto_4x4(self):
        foto = self.cleaned_data.get("foto_4x4")
        if not foto:
            return foto

        try:
            img = Image.open(foto).convert("RGB")
        except Exception:
            raise forms.ValidationError("El archivo no es una imagen válida.")

        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        upper = (h - side) // 2
        img = img.crop((left, upper, left + side, upper + side)).resize((600, 600), Image.LANCZOS)
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)

        # Validar tamaño final
        MAX_BYTES = 4 * 1024 * 1024
        if buf.getbuffer().nbytes > MAX_BYTES:
            raise forms.ValidationError("La foto, aun comprimida, supera 4 MB. Subí una imagen más liviana.")

        foto_normalizada = InMemoryUploadedFile(
            buf, 
            None, 
            "foto4x4.jpg", 
            "image/jpeg", 
            buf.getbuffer().nbytes, 
            None
        )
        return foto_normalizada

    def clean(self):
        cd = super().clean()
        carrera = cd.get("carrera")
        is_certificacion = False
        try:
            if carrera and "certific" in (getattr(carrera, "nombre", "") or "").lower():
                is_certificacion = True
        except Exception:
            pass

        if is_certificacion:
            ter_ok = bool(cd.get("sup1_titulo") or cd.get("sup2_titulo"))
            if not ter_ok:
                self.add_error(
                    None,
                    "Para Certificación Docente Docente debés informar al menos un título terciario/universitario."
                )
        return cd

ESTADO_CHOICES = [
    ("NUEVA", "Nueva"),
    ("PENDIENTE", "Pendiente"),
    ("CONFIRMADA", "Confirmada"),
    ("BAJA", "Baja"),
]


class BedelConfirmForm(forms.ModelForm):
    estado = forms.ChoiceField(choices=ESTADO_CHOICES)

    class Meta:
        model = Preinscripcion
        fields = [
            # Documentación
            "doc_fotocopia_titulo_legalizada",
            "doc_fotocopia_analitico_legalizada",
            "doc_fotos_4x4",
            "doc_titulo_terciario_universitario",
            "doc_cert_alumno_regular",
            "doc_cert_titulo_en_tramite",
            "doc_cert_buena_salud",
            "doc_folios",
            "doc_declaracion_jurada",
            "doc_incumbencias",
            "doc_adeuda_materias",
            "adeuda_materias_escuela",
            "adeuda_materias_detalle",
            # Estado
            "estado",
        ]
        widgets = {
            "adeuda_materias_detalle": forms.Textarea(attrs={"rows": 3}),
            "adeuda_materias_escuela": forms.TextInput(),
        }
        labels = {
            "doc_declaracion_jurada": "Declaración jurada / Nota compromiso",
        }

    def clean(self):
        cleaned = super().clean()
        docente = is_docente_track(self.instance.carrera)

        # Exclusión mutua: Título vs Cert. en trámite vs Adeuda (adeuda no aplica en docente)
        t_sec = bool(cleaned.get("doc_fotocopia_titulo_legalizada"))
        t_ter = bool(cleaned.get("doc_titulo_terciario_universitario"))
        c_tram = bool(cleaned.get("doc_cert_titulo_en_tramite"))
        adeuda = bool(cleaned.get("doc_adeuda_materias")) and not docente

        triad = [c_tram, adeuda]
        if docente:
            triad.append(t_ter)
            cleaned["doc_adeuda_materias"] = False
            cleaned["adeuda_materias_escuela"] = ""
            cleaned["adeuda_materias_detalle"] = ""
        else:
            triad.append(t_sec or t_ter)

        if sum(1 for x in triad if x) > 1:
            raise forms.ValidationError("Solo una de: Título (legalizado) / Certificado en trámite / Adeuda materias.")

        # Reglas de adeuda materias
        if adeuda:
            if not cleaned.get("doc_fotocopia_analitico_legalizada"):
                self.add_error("doc_fotocopia_analitico_legalizada", "Requerido si adeuda materias (analítico).")
            if not cleaned.get("adeuda_materias_escuela"):
                self.add_error("adeuda_materias_escuela", "Requerido si adeuda materias.")
            if not cleaned.get("adeuda_materias_detalle"):
                self.add_error("adeuda_materias_detalle", "Requerido si adeuda materias.")

        # Reglas para Certificación Docente
        if docente:
            if cleaned.get("doc_adeuda_materias"):
                self.add_error("doc_adeuda_materias", "No aplica en Certificación Docente.")
            if not cleaned.get("doc_titulo_terciario_universitario"):
                self.add_error("doc_titulo_terciario_universitario", "Obligatorio en Certificación Docente.")
            if not cleaned.get("doc_incumbencias"):
                self.add_error("doc_incumbencias", "Obligatorio en Certificación Docente.")
            cleaned["doc_fotocopia_titulo_legalizada"] = False  # se oculta/ignora

        # Cálculo de condición
        cond = compute_condicion_admin(self.instance, cleaned)
        cleaned["__condicion_admin"] = cond
        if cond == "CONDICIONAL" and not cleaned.get("doc_declaracion_jurada"):
            self.add_error("doc_declaracion_jurada", "Requerida para condición administrativa 'Condicional'.")

        return cleaned