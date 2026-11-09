from app.exporters.docx_base import build_document

PROFILE = {
    "layout": "single",
    "section_style": "rule",
    "section_en": True,
    "numbered": True,
    "dense": False,
    "serif": True,
}


def build(resume: dict, theme: dict, photo=None):
    return build_document(resume, theme, PROFILE, photo)
