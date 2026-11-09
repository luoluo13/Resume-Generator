from app.exporters.docx_base import build_document

PROFILE = {
    "layout": "band",
    "band_color": "1E1C18",
    "section_style": "boxed",
    "section_en": False,
    "numbered": True,
    "dense": True,
    "serif": False,
}


def build(resume: dict, theme: dict, photo=None):
    return build_document(resume, theme, PROFILE, photo)
