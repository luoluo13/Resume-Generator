import { useRef } from "react";
import { api } from "../api";
import { IconImage, IconUpload, IconUser } from "../icons";
import { useResumeStore } from "../store";
import type { Basics } from "../types";
import { toast } from "../ui";
import { Field, TextInput, Toggle } from "./fields";

export function BasicForm() {
  const resume = useResumeStore((state) => state.resume);
  const update = useResumeStore((state) => state.update);
  const info = useResumeStore((state) => state.info);
  const fileRef = useRef<HTMLInputElement>(null);

  if (!resume) return null;
  const basics = resume.basics;

  const setField = <K extends keyof Basics>(key: K, value: Basics[K]) => {
    update((draft) => {
      draft.basics[key] = value;
    });
  };

  const setShow = (key: string, value: boolean) => {
    update((draft) => {
      draft.basics.show = { ...draft.basics.show, [key]: value };
    });
  };

  const uploadPhoto = async (file?: File) => {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      toast("warning", "照片不能超过 5MB");
      return;
    }
    try {
      const result = await api.uploadPhoto(file);
      update((draft) => {
        draft.basics.photo = result.path;
        draft.basics.show = { ...draft.basics.show, photo: true };
      });
      toast("success", "照片已更新");
    } catch (error) {
      toast("error", (error as Error).message);
    }
  };

  return (
    <>
      <div className="pane-head">
        <div>
          <p className="pane-eyebrow">BASICS</p>
          <h2>基本信息</h2>
          <p className="pane-hint">姓名与联系方式会出现在简历抬头，右侧预览实时更新。</p>
        </div>
      </div>
      <div className="panel is-active">
        <div className="field-grid">
          <TextInput label="姓名" value={basics.name} maxLength={30} placeholder="必填" onChange={(value) => setField("name", value)} />
          <TextInput
            label="求职意向"
            value={basics.jobIntention}
            maxLength={30}
            placeholder="如：高级后端开发工程师"
            onChange={(value) => setField("jobIntention", value)}
          />
          <TextInput label="电话" value={basics.phone} type="tel" placeholder="138-0000-0000" onChange={(value) => setField("phone", value)} />
          <TextInput label="邮箱" value={basics.email} type="email" placeholder="name@example.com" onChange={(value) => setField("email", value)} />
          <TextInput label="现居城市" value={basics.city} maxLength={20} placeholder="上海" onChange={(value) => setField("city", value)} />
          <TextInput label="到岗时间" value={basics.available} maxLength={20} placeholder="一个月内" onChange={(value) => setField("available", value)} />
          <TextInput
            label="工作经验"
            value={basics.yearsOfExperience}
            maxLength={20}
            placeholder="5 年"
            onChange={(value) => setField("yearsOfExperience", value)}
          />
        </div>

        <div className="form-divider">简历照片</div>
        <div className="photo-row">
          <div className="photo-thumb">
            {basics.photo ? <img src={`/media/${basics.photo}`} alt="" /> : <IconUser size={22} />}
          </div>
          <div className="photo-copy">
            <strong>{basics.photo ? "已上传照片" : "尚未上传照片"}</strong>
            <p>JPG / PNG / WEBP，不超过 5MB，导入后自动压缩。照片是否展示由模板与主题共同决定。</p>
            <div className="photo-actions">
              <button type="button" className="btn btn-sm" onClick={() => fileRef.current?.click()}>
                <IconUpload size={13} />
                {basics.photo ? "更换照片" : "上传照片"}
              </button>
              {basics.photo ? (
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  onClick={() => setField("photo", "")}
                >
                  移除
                </button>
              ) : null}
              <Toggle label="在简历中显示" checked={Boolean(basics.show.photo)} onChange={(value) => setShow("photo", value)} />
            </div>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            hidden
            onChange={(event) => {
              void uploadPhoto(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
        </div>

        <div className="form-divider">可选信息</div>
        <div className="field-grid">
          <TextInput label="性别" value={basics.gender} maxLength={10} placeholder="选填" onChange={(value) => setField("gender", value)} />
          <TextInput label="出生年月" value={basics.birth} maxLength={20} placeholder="如：1997.03" onChange={(value) => setField("birth", value)} />
          <Field label="政治面貌">
            <input
              value={basics.political}
              maxLength={20}
              placeholder="选填"
              onChange={(event) => setField("political", event.target.value)}
            />
          </Field>
        </div>
        <div className="toggle-row">
          <Toggle label="显示性别" checked={Boolean(basics.show.gender)} onChange={(value) => setShow("gender", value)} />
          <Toggle label="显示出生年月" checked={Boolean(basics.show.birth)} onChange={(value) => setShow("birth", value)} />
          <Toggle label="显示政治面貌" checked={Boolean(basics.show.political)} onChange={(value) => setShow("political", value)} />
        </div>

        {info && !info.fonts.ready ? (
          <div className="inline-note">
            <IconImage size={14} />
            未检测到可选字体，导出时将回退为微软雅黑。
          </div>
        ) : null}
      </div>
    </>
  );
}
