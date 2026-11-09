import { IconClose, IconPalette } from "../icons";
import { useResumeStore } from "../store";
import type { Theme } from "../types";
import { useUiStore } from "../ui";

const ACCENTS = [
  { value: "#bf4a2e", name: "朱砂" },
  { value: "#1f4e79", name: "靛蓝" },
  { value: "#2f6b4f", name: "松绿" },
  { value: "#6b4b8a", name: "紫檀" },
  { value: "#a0742c", name: "赭金" },
  { value: "#1b1a17", name: "墨黑" }
];

const FONTS: { value: Theme["fontFamily"]; label: string }[] = [
  { value: "SourceHanSansSC", label: "思源黑体" },
  { value: "SourceHanSerifSC", label: "思源宋体" },
  { value: "MicrosoftYaHei", label: "微软雅黑" }
];

export function ThemeDrawer() {
  const open = useUiStore((state) => state.themeOpen);
  const setOpen = useUiStore((state) => state.setThemeOpen);
  const resume = useResumeStore((state) => state.resume);
  const templates = useResumeStore((state) => state.templates);
  const info = useResumeStore((state) => state.info);
  const setTheme = useResumeStore((state) => state.setTheme);

  if (!resume) return null;
  const theme = resume.theme;
  const manifest = templates.find((item) => item.id === theme.template);
  const supports = manifest?.supports ?? { columns: [1, 2], photo: true, divider: ["line", "block", "none"] };
  const fontMissing = info ? !info.fonts.available[theme.fontFamily] : false;

  const reset = () => {
    setTheme({
      accent: "#bf4a2e",
      fontFamily: "SourceHanSansSC",
      fontSize: 10.5,
      lineHeight: 1.35,
      pageMargin: 18,
      columns: supports.columns[0],
      photoPosition: supports.photo ? "right" : "none",
      dividerStyle: supports.divider[0] as Theme["dividerStyle"],
      density: "normal",
      variants: {}
    });
  };

  return (
    <aside className={`drawer${open ? " is-open" : ""}`} aria-hidden={!open}>
      <div className="drawer-head">
        <div>
          <h3>主题与排版</h3>
          <p>所有调整实时作用于预览与三种导出格式。</p>
        </div>
        <button type="button" className="icon-btn" title="关闭" onClick={() => setOpen(false)}>
          <IconClose size={16} />
        </button>
      </div>

      <div className="drawer-body">
        <section className="theme-group">
          <h4>强调色</h4>
          <p>用于标题、分隔线与要点标记，同时写入 DOCX。</p>
          <div className="swatches">
            {ACCENTS.map((accent) => (
              <button
                type="button"
                key={accent.value}
                className={`swatch${theme.accent.toLowerCase() === accent.value ? " is-active" : ""}`}
                style={{ background: accent.value }}
                title={accent.name}
                onClick={() => setTheme({ accent: accent.value })}
              />
            ))}
            <label className="swatch swatch-custom" title="自定义颜色">
              <input type="color" value={theme.accent} onChange={(event) => setTheme({ accent: event.target.value })} />
              <IconPalette size={12} />
            </label>
          </div>
        </section>

        <section className="theme-group">
          <h4>正文字体</h4>
          <p>标题字体由模板决定，正文字体对全文生效。</p>
          <div className="segmented">
            {FONTS.map((font) => (
              <button
                type="button"
                key={font.value}
                className={theme.fontFamily === font.value ? "is-active" : ""}
                title={info && !info.fonts.available[font.value] ? "系统中未检测到该字体，将自动回退" : font.label}
                onClick={() => setTheme({ fontFamily: font.value })}
              >
                {font.label}
              </button>
            ))}
          </div>
          {fontMissing ? <p className="inline-note">未检测到该字体，渲染与导出时会回退为微软雅黑。</p> : null}
        </section>

        <section className="theme-group">
          <h4>字号</h4>
          <p>9~12pt，默认 10.5pt。中文简历建议保持在 10~11pt。</p>
          <Slider
            value={theme.fontSize}
            min={9}
            max={12}
            step={0.5}
            display={`${theme.fontSize.toFixed(1)}pt`}
            onChange={(value) => setTheme({ fontSize: value })}
          />
        </section>

        <section className="theme-group">
          <h4>行距</h4>
          <p>1.0~1.6，默认 1.35。内容偏多时优先压行距。</p>
          <Slider
            value={theme.lineHeight}
            min={1}
            max={1.6}
            step={0.05}
            display={theme.lineHeight.toFixed(2)}
            onChange={(value) => setTheme({ lineHeight: value })}
          />
        </section>

        <section className="theme-group">
          <h4>页边距</h4>
          <p>12~25mm，默认 18mm。打印投递建议不小于 15mm。</p>
          <Slider
            value={theme.pageMargin}
            min={12}
            max={25}
            step={1}
            display={`${theme.pageMargin}mm`}
            onChange={(value) => setTheme({ pageMargin: value })}
          />
        </section>

        <section className="theme-group">
          <h4>栏数</h4>
          <p>双栏会把技能、奖项等模块放入侧栏，模板能力决定是否可用。</p>
          <Segmented
            value={theme.columns}
            options={[
              { value: 1, label: "单栏", disabled: !supports.columns.includes(1) },
              { value: 2, label: "双栏", disabled: !supports.columns.includes(2) }
            ]}
            onChange={(value) => setTheme({ columns: value })}
          />
        </section>

        <section className="theme-group">
          <h4>照片位置</h4>
          <p>没有上传照片时，此处设置不会改变版面。</p>
          <Segmented
            value={theme.photoPosition}
            options={[
              { value: "none", label: "不显示", disabled: false },
              { value: "right", label: "右上", disabled: !supports.photo },
              { value: "left", label: "左上", disabled: !supports.photo }
            ]}
            onChange={(value) => setTheme({ photoPosition: value })}
          />
        </section>

        <section className="theme-group">
          <h4>分隔样式</h4>
          <p>控制模块标题后的装饰线，模板可按自身风格覆盖。</p>
          <Segmented
            value={theme.dividerStyle}
            options={[
              { value: "line", label: "细线", disabled: !supports.divider.includes("line") },
              { value: "block", label: "色块", disabled: !supports.divider.includes("block") },
              { value: "none", label: "无", disabled: !supports.divider.includes("none") }
            ]}
            onChange={(value) => setTheme({ dividerStyle: value as Theme["dividerStyle"] })}
          />
        </section>

        {manifest?.variants?.map((group) => (
          <section className="theme-group" key={group.key}>
            <h4>{group.label}</h4>
            <p>{group.description || "由当前模板提供的版式变体。"}</p>
            <Segmented
              value={theme.variants?.[group.key] ?? group.default}
              options={group.options}
              onChange={(value) =>
                setTheme({ variants: { ...(theme.variants ?? {}), [group.key]: value } })
              }
            />
          </section>
        ))}

        <section className="theme-group">
          <h4>内容密度</h4>
          <p>紧凑会缩小模块间距与段落间距，适合内容接近一页时微调。</p>
          <Segmented
            value={theme.density}
            options={[
              { value: "loose", label: "宽松" },
              { value: "normal", label: "标准" },
              { value: "compact", label: "紧凑" }
            ]}
            onChange={(value) => setTheme({ density: value as Theme["density"] })}
          />
        </section>
      </div>

      <div className="drawer-foot">
        <button type="button" className="btn" onClick={reset}>
          恢复默认
        </button>
        <button type="button" className="btn btn-primary drawer-done" onClick={() => setOpen(false)}>
          完成
        </button>
      </div>
    </aside>
  );
}

interface SliderProps {
  value: number;
  min: number;
  max: number;
  step: number;
  display: string;
  onChange: (value: number) => void;
}

function Slider({ value, min, max, step, display, onChange }: SliderProps) {
  return (
    <div className="slider-row">
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <span className="slider-val">{display}</span>
    </div>
  );
}

interface SegmentedOption<T extends string | number> {
  value: T;
  label: string;
  disabled?: boolean;
}

interface SegmentedProps<T extends string | number> {
  value: T;
  options: SegmentedOption<T>[];
  onChange: (value: T) => void;
}

function Segmented<T extends string | number>({ value, options, onChange }: SegmentedProps<T>) {
  return (
    <div className="segmented">
      {options.map((option) => (
        <button
          type="button"
          key={String(option.value)}
          className={value === option.value ? "is-active" : ""}
          disabled={option.disabled}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
