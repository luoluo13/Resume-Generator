import type { ReactNode, SVGProps } from "react";

interface IconProps extends Omit<SVGProps<SVGSVGElement>, "children"> {
  size?: number;
  children: ReactNode;
}

function Icon({ size = 16, children, ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const IconPen = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M12 20h9" />
    <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" />
  </Icon>
);

export const IconTemplate = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M3 9h18M9 9v11" />
  </Icon>
);

export const IconPalette = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M12 3a9 9 0 1 0 0 18h1.5a2 2 0 0 0 1.4-3.4 2 2 0 0 1 1.4-3.4H18a3 3 0 0 0 3-3A9 9 0 0 0 12 3z" />
    <circle cx="7.5" cy="10" r="1" />
    <circle cx="11" cy="7" r="1" />
    <circle cx="15.5" cy="8.5" r="1" />
  </Icon>
);

export const IconDownload = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M12 3v12" />
    <path d="m7 10 5 5 5-5" />
    <path d="M4 21h16" />
  </Icon>
);

export const IconEye = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" />
    <circle cx="12" cy="12" r="3" />
  </Icon>
);

export const IconEyeOff = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M3 3l18 18" />
    <path d="M10.6 5.2A10.9 10.9 0 0 1 12 5c6.4 0 10 7 10 7a17.6 17.6 0 0 1-3 3.9" />
    <path d="M6.2 6.7A17.4 17.4 0 0 0 2 12s3.6 7 10 7a10.8 10.8 0 0 0 4.1-.8" />
  </Icon>
);

export const IconPlus = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M12 5v14M5 12h14" />
  </Icon>
);

export const IconTrash = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13" />
  </Icon>
);

export const IconChevron = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="m6 9 6 6 6-6" />
  </Icon>
);

export const IconGrip = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <circle cx="9" cy="6" r="1" />
    <circle cx="15" cy="6" r="1" />
    <circle cx="9" cy="12" r="1" />
    <circle cx="15" cy="12" r="1" />
    <circle cx="9" cy="18" r="1" />
    <circle cx="15" cy="18" r="1" />
  </Icon>
);

export const IconZoomIn = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.6-3.6M11 8v6M8 11h6" />
  </Icon>
);

export const IconZoomOut = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.6-3.6M8 11h6" />
  </Icon>
);

export const IconClose = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Icon>
);

export const IconCheck = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="m4 12 5 5L20 6" />
  </Icon>
);

export const IconAlert = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M12 3 2.5 20h19z" />
    <path d="M12 9v5M12 17.2v.1" />
  </Icon>
);

export const IconFolder = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
  </Icon>
);

export const IconUpload = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M12 16V4" />
    <path d="m7 9 5-5 5 5" />
    <path d="M4 20h16" />
  </Icon>
);

export const IconFileJson = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
    <path d="M14 3v6h6M9 13v4M15 13v4" />
  </Icon>
);

export const IconUser = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <circle cx="12" cy="8" r="3.6" />
    <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
  </Icon>
);

export const IconGraduation = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="m3 9 9-5 9 5-9 5z" />
    <path d="M7 11.5V16c0 1.7 2.2 3 5 3s5-1.3 5-3v-4.5" />
    <path d="M21 9v5" />
  </Icon>
);

export const IconBriefcase = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <rect x="3" y="7" width="18" height="13" rx="2" />
    <path d="M9 7V5h6v2M3 12h18" />
  </Icon>
);

export const IconLayers = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="m12 3 9 5-9 5-9-5z" />
    <path d="m3 13 9 5 9-5" />
  </Icon>
);

export const IconStar = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z" />
  </Icon>
);

export const IconAward = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <circle cx="12" cy="9" r="5" />
    <path d="m8.5 13.5-1.5 7 5-2.6 5 2.6-1.5-7" />
  </Icon>
);

export const IconWand = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="m3 21 12-12" />
    <path d="m14 4 1.2 2.8L18 8l-2.8 1.2L14 12l-1.2-2.8L10 8l2.8-1.2z" />
    <path d="M19 3h1M21 7h-1M17 2v1" />
  </Icon>
);

export const IconArrowUp = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M12 19V5M6 11l6-6 6 6" />
  </Icon>
);

export const IconArrowDown = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M12 5v14M6 13l6 6 6-6" />
  </Icon>
);

export const IconLink = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1" />
    <path d="M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1" />
  </Icon>
);

export const IconBold = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M7 4h6a4 4 0 0 1 0 8H7zM7 12h7a4 4 0 0 1 0 8H7z" />
  </Icon>
);

export const IconItalic = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M15 4h-5M14 20H9M14 4 10 20" />
  </Icon>
);

export const IconRefresh = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M20 11a8 8 0 1 0-2.3 6.3M20 5v6h-6" />
  </Icon>
);

export const IconImage = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <circle cx="8.5" cy="9.5" r="1.5" />
    <path d="m4 18 5-5 3 3 3-4 5 6" />
  </Icon>
);

export const IconFilePdf = (p: Omit<IconProps, "children">) => (
  <Icon {...p}>
    <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
    <path d="M14 3v6h6M8 14h2a1.5 1.5 0 0 1 0 3H8zM8 17v2M13 14v5h1.5a2.5 2.5 0 0 0 0-5z" />
  </Icon>
);
