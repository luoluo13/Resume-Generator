from app.exporters.docx_base import build_document

PROFILE = {
    "layout": "single",
    "section_style": "plain",
    "section_en": False,
    "numbered": True,
    "dense": False,
    "bullet": "dash",
    "serif": False,
}


def build(resume: dict, theme: dict, photo=None):
    return build_document(resume, theme, PROFILE, photo)
