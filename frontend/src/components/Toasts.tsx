import { IconAlert, IconCheck, IconClose } from "../icons";
import { useUiStore } from "../ui";

export function Toasts() {
  const toasts = useUiStore((state) => state.toasts);
  const dismiss = useUiStore((state) => state.dismissToast);

  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((item) => (
        <div className={`toast-item toast-${item.kind}`} key={item.id}>
          <span className="toast-icon">
            {item.kind === "success" ? <IconCheck size={14} /> : <IconAlert size={14} />}
          </span>
          <span className="toast-message">{item.message}</span>
          <button type="button" className="toast-close" title="关闭" onClick={() => dismiss(item.id)}>
            <IconClose size={12} />
          </button>
        </div>
      ))}
    </div>
  );
}
