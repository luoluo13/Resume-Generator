import { BasicForm } from "../editor/BasicForm";
import { SectionForm } from "../editor/SectionForm";
import { SectionRail } from "../editor/SectionRail";
import { useResumeStore } from "../store";
import { useUiStore } from "../ui";
import { PreviewPane } from "./PreviewPane";

export function EditorView() {
  const resume = useResumeStore((state) => state.resume);
  const activeSectionId = useUiStore((state) => state.activeSectionId);
  const activeIndex = resume ? resume.sections.findIndex((section) => section.id === activeSectionId) : -1;
  const section = activeIndex >= 0 && resume ? resume.sections[activeIndex] : null;

  return (
    <div className="screen-editor">
      <SectionRail />
      <section className="form-pane">{section ? <SectionForm section={section} index={activeIndex} /> : <BasicForm />}</section>
      <PreviewPane />
    </div>
  );
}
