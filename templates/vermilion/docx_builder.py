from app.exporters.docx_base import build_document

PROFILE = {
    "layout": "band",
    "band_color": "accent",
    "section_style": "badge",
    "section_en": False,
    "numbered": True,
    "dense": False,
    "serif": True,
}


def build(resume: dict, theme: dict, photo=None):
    return build_document(resume, theme, PROFILE, photo)
