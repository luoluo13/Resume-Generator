import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect } from "react";
import { IconBold, IconItalic, IconLink, IconTrash } from "../icons";
import { toast } from "../ui";

interface BulletEditorProps {
  value: string;
  onChange: (html: string) => void;
  onRemove: () => void;
}

export function BulletEditor({ value, onChange, onRemove }: BulletEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        blockquote: false,
        codeBlock: false,
        horizontalRule: false,
        bulletList: false,
        orderedList: false,
        listItem: false
      }),
      Link.configure({ openOnClick: false, autolink: true }),
      Placeholder.configure({ placeholder: "描述成果，建议包含动作、方法与数据" })
    ],
    content: value || "<p></p>",
    onUpdate: ({ editor: instance }) => onChange(instance.getHTML())
  });

  useEffect(() => {
    if (editor && !editor.isFocused && editor.getHTML() !== value) {
      editor.commands.setContent(value || "<p></p>", false);
    }
  }, [editor, value]);

  if (!editor) return null;

  const setLink = () => {
    const previous = (editor.getAttributes("link").href as string) || "";
    const url = window.prompt("链接地址（以 http:// 或 https:// 开头）", previous);
    if (url === null) return;
    if (!url.trim()) {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }
    if (!/^https?:\/\//i.test(url.trim())) {
      toast("warning", "链接必须以 http:// 或 https:// 开头");
      return;
    }
    editor.chain().focus().extendMarkRange("link").setLink({ href: url.trim() }).run();
  };

  return (
    <div className="bullet-row">
      <i className="bullet-dot" />
      <div className="bullet-main">
        <EditorContent editor={editor} className="bullet-text" />
        <div className="rt-toolbar">
          <button
            type="button"
            className={`rt-btn${editor.isActive("bold") ? " is-active" : ""}`}
            title="加粗 Ctrl+B"
            onClick={() => editor.chain().focus().toggleBold().run()}
          >
            <IconBold size={13} />
          </button>
          <button
            type="button"
            className={`rt-btn${editor.isActive("italic") ? " is-active" : ""}`}
            title="斜体 Ctrl+I"
            onClick={() => editor.chain().focus().toggleItalic().run()}
          >
            <IconItalic size={13} />
          </button>
          <button type="button" className="rt-btn" title="插入链接" onClick={setLink}>
            <IconLink size={13} />
          </button>
          <span className="rt-hint">Ctrl+B / Ctrl+I</span>
        </div>
      </div>
      <button type="button" className="bullet-del" title="删除这条要点" onClick={onRemove}>
        <IconTrash size={13} />
      </button>
    </div>
  );
}
