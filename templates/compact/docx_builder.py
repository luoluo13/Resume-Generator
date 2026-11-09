from app.exporters.docx_base import build_document

PROFILE = {
    "layout": "single",
    "section_style": "bar",
    "section_en": False,
    "numbered": False,
    "dense": True,
    "bullet": "dot",
    "serif": False,
}


def build(resume: dict, theme: dict, photo=None):
    return build_document(resume, theme, PROFILE, photo)
