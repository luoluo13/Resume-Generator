from app.exporters.docx_base import build_document

PROFILE = {
    "layout": "centered",
    "section_style": "centered",
    "section_en": True,
    "numbered": True,
    "dense": False,
    "bullet": "dash",
    "serif": True,
}


def build(resume: dict, theme: dict, photo=None):
    return build_document(resume, theme, PROFILE, photo)
