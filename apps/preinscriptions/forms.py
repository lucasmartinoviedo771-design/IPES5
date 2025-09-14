import io, os
import re
from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image
from .models import Preinscripcion

try:
    from apps.academics.models import Carrera
except Exception:
    Carrera = None

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

    def clean_cuil(self):
        val = self.cleaned_data.get("cuil", "") or ""
        digits = re.sub(r"\D", "", val)
        if len(digits) != 11:
            raise forms.ValidationError("Ingresá los 11 dígitos del CUIL.")
        return f"{digits[:2]}-{digits[2:10]}-{digits[10:]}"

    def clean_foto_4x4(self):
        f = self.cleaned_data.get("foto_4x4")
        if not f:
            return f  # opcional, no validar si no suben nada

        # 1) Abrir imagen
        try:
            img = Image.open(f)
        except Exception:
            raise forms.ValidationError("El archivo no es una imagen válida.")

        # 2) Normalizar modo
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")

        # 3) Recortar al centro para dejarla cuadrada
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))

        # 4) Redimensionar a 600×600 (ajustá si querés)
        target = 600
        if img.size != (target, target):
            img = img.resize((target, target), Image.LANCZOS)

        # 5) Guardar y controlar tamaño (máx. 4 MB)
        MAX_BYTES = 4 * 1024 * 1024  # cambiá el tope si lo necesitás
        quality = 90

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
        buf.seek(0)

        # Bajar calidad si supera el tope
        while buf.tell() > MAX_BYTES and quality > 60:
            quality -= 5
            buf.seek(0); buf.truncate(0)
            img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
            buf.seek(0)

        # Último recurso: achicar un poco la resolución si todavía pesa mucho
        if buf.tell() > MAX_BYTES:
            shrink = 0.85
            while buf.tell() > MAX_BYTES and min(img.size) > 300:  # no bajar de 300×300
                new_wh = (int(img.size[0] * shrink), int(img.size[1] * shrink))
                img = img.resize(new_wh, Image.LANCZOS)
                buf.seek(0); buf.truncate(0)
                img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
                buf.seek(0)

        if buf.tell() > MAX_BYTES:
            raise forms.ValidationError("La foto, aun comprimida, supera 4 MB. Subí una imagen más liviana.")

        # 6) Devolver el archivo procesado
        base, _ = os.path.splitext(getattr(f, "name", "foto_4x4.jpg"))
        new_name = f"{base}_4x4.jpg"
        return ContentFile(buf.read(), name=new_name)

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
                    "Para Certificación Docente debés informar al menos un título terciario/universitario."
                )
        return cd
