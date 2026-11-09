from app.exporters.docx_base import build_document

PROFILE = {
    "layout": "sidebar",
    "section_style": "plain",
    "section_en": False,
    "numbered": False,
    "dense": False,
    "serif": True,
    "sidebar_types": ("skills", "awards", "certificate"),
}


def build(resume: dict, theme: dict, photo=None):
    return build_document(resume, theme, PROFILE, photo)
