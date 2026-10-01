declare module "lucide-react" {
  import type { ComponentType, SVGProps } from "react";

  type IconProps = SVGProps<SVGSVGElement> & {
    size?: string | number;
    absoluteStrokeWidth?: boolean;
  };
  type LucideIcon = ComponentType<IconProps>;

  export const Activity: LucideIcon;
  export const Award: LucideIcon;
  export const BarChart3: LucideIcon;
  export const Camera: LucideIcon;
  export const Check: LucideIcon;
  export const ChevronRight: LucideIcon;
  export const Clock3: LucideIcon;
  export const Dumbbell: LucideIcon;
  export const Footprints: LucideIcon;
  export const Flame: LucideIcon;
  export const Heart: LucideIcon;
  export const ImagePlus: LucideIcon;
  export const LayoutDashboard: LucideIcon;
  export const LoaderCircle: LucideIcon;
  export const LogOut: LucideIcon;
  export const Menu: LucideIcon;
  export const Plus: LucideIcon;
  export const Send: LucideIcon;
  export const ShieldCheck: LucideIcon;
  export const Sparkles: LucideIcon;
  export const Trophy: LucideIcon;
  export const UserPlus: LucideIcon;
  export const UserRound: LucideIcon;
  export const Users: LucideIcon;
  export const X: LucideIcon;
}
