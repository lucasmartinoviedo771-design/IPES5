import re
from django import forms
from django.core.exceptions import ValidationError
from PIL import Image
from .models import Preinscripcion

try:
    from apps.academics.models import Carrera
except Exception:
    Carrera = None

class PreinscripcionForm(forms.ModelForm):
    class Meta:
        model = Preinscripcion
        fields = [
            # Datos personales y de carrera
            "carrera", "cuil", "dni", "apellido", "nombres", "fecha_nacimiento",
            "estado_civil", "localidad_nac", "provincia_nac", "pais_nac", "nacionalidad",
            # Contacto
            "domicilio", "tel_fijo", "tel_movil", "email",
            # TODO: Estos campos no están en el modelo actual, revisar si se deben agregar
            # "emergencia_telefono", "emergencia_parentesco",
            # Laborales
            "trabaja", "empleador", "horario_trabajo", "domicilio_trabajo",
            # Estudios
            "sec_titulo", "sec_establecimiento", "sec_fecha_egreso", "sec_localidad",
            "sec_provincia", "sec_pais",
            "sup1_titulo", "sup1_establecimiento", "sup1_fecha_egreso", "sup1_localidad",
            "sup1_provincia", "sup1_pais",
            "sup2_titulo", "sup2_establecimiento", "sup2_fecha_egreso", "sup2_localidad",
            "sup2_provincia", "sup2_pais",
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

    def clean_cuil(self):
        val = self.cleaned_data.get("cuil", "") or ""
        digits = re.sub(r"\D", "", val)
        if len(digits) != 11:
            raise forms.ValidationError("Ingresá los 11 dígitos del CUIL.")
        return f"{digits[:2]}-{digits[2:10]}-{digits[10:]}"

    def clean_foto_4x4(self):
        """
        Acepta cualquier imagen, corrige orientación, la hace cuadrada, redimensiona y comprime.
        """
        f = self.cleaned_data.get("foto_4x4")
        if not f:
            return f

        # Tamaño de salida
        TARGET = 600        # px (lado)
        QUALITY = 85        # JPEG quality

        # Lee la imagen y corrige orientación
        try:
            img = Image.open(f)
        except Exception:
            raise forms.ValidationError("No se pudo leer la imagen. Subí un JPG/PNG válido.")

        # Corrige rotación por EXIF
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Convierte a RGB para JPEG
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")

        # ---- Normalización a CUADRADO ----
        w, h = img.size
        if w != h:
            # Opción A: recorte centrado (se ve mejor)
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))

        # Redimensiona a 600x600 con buena calidad
        img = img.resize((TARGET, TARGET), Image.LANCZOS)

        # Comprime a JPEG en memoria
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=QUALITY, optimize=True)
        buffer.seek(0)

        # Construye un nuevo InMemoryUploadedFile para reemplazar el original
        new_name = f"foto4x4_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        new_file = InMemoryUploadedFile(
            buffer,
            field_name=getattr(f, "field_name", "foto_4x4"),
            name=new_name,
            content_type="image/jpeg",
            size=buffer.getbuffer().nbytes,
            charset=None,
        )

        return new_file

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
