import { useState, type ReactNode } from "react";
import { IconClose, IconPlus } from "../icons";

interface FieldProps {
  label: string;
  full?: boolean;
  hint?: string;
  children: ReactNode;
}

export function Field({ label, full, hint, children }: FieldProps) {
  return (
    <label className={`field${full ? " full" : ""}`}>
      <span>{label}</span>
      {children}
      {hint ? <em className="field-hint">{hint}</em> : null}
    </label>
  );
}

interface TextInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  full?: boolean;
  maxLength?: number;
  type?: "text" | "email" | "tel";
  hint?: string;
  autoFocus?: boolean;
}

export function TextInput({
  label,
  value,
  onChange,
  placeholder,
  full,
  maxLength,
  type = "text",
  hint,
  autoFocus
}: TextInputProps) {
  return (
    <Field label={label} full={full} hint={hint}>
      <input
        type={type}
        value={value}
        maxLength={maxLength}
        placeholder={placeholder}
        autoFocus={autoFocus}
        onChange={(event) => onChange(event.target.value)}
      />
    </Field>
  );
}

interface TextAreaProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
}

export function TextArea({ label, value, onChange, placeholder, rows = 3 }: TextAreaProps) {
  return (
    <Field label={label} full>
      <textarea rows={rows} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </Field>
  );
}

interface TagInputProps {
  label: string;
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  full?: boolean;
}

export function TagInput({ label, value, onChange, placeholder, full }: TagInputProps) {
  const [draft, setDraft] = useState("");

  const commit = (raw: string) => {
    const tags = raw
      .split(/[,，、]/)
      .map((tag) => tag.trim())
      .filter(Boolean);
    if (!tags.length) return;
    onChange([...new Set([...value, ...tags])]);
    setDraft("");
  };

  return (
    <div className={`field${full ? " full" : ""}`}>
      <span>{label}</span>
      <div className="tag-editor">
        {value.map((tag) => (
          <span className="tag" key={tag}>
            {tag}
            <button type="button" className="tag-x" onClick={() => onChange(value.filter((item) => item !== tag))}>
              <IconClose size={11} />
            </button>
          </span>
        ))}
        <input
          className="tag-input"
          value={draft}
          placeholder={value.length ? "" : placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === "," || event.key === "，") {
              event.preventDefault();
              commit(draft);
            } else if (event.key === "Backspace" && !draft && value.length) {
              onChange(value.slice(0, -1));
            }
          }}
          onBlur={() => commit(draft)}
        />
      </div>
      <em className="field-hint">回车或逗号分隔，可添加多个</em>
    </div>
  );
}

interface ToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export function Toggle({ label, checked, onChange }: ToggleProps) {
  return (
    <button type="button" className={`chip-toggle${checked ? "" : " is-off"}`} onClick={() => onChange(!checked)}>
      <i className="dot" />
      {label}
    </button>
  );
}

interface AddButtonProps {
  label: string;
  onClick: () => void;
}

export function AddButton({ label, onClick }: AddButtonProps) {
  return (
    <button type="button" className="add-entry" onClick={onClick}>
      <IconPlus size={14} />
      {label}
    </button>
  );
}
