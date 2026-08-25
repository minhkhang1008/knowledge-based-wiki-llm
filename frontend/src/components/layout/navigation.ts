import type { ComponentType, SVGProps } from "react";
import {
  AskIcon,
  DashboardIcon,
  DocumentsIcon,
  SearchIcon,
} from "@/components/ui/Icons";

export interface NavItem {
  href: string;
  label: string;
  description: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
}

export const NAV_ITEMS: NavItem[] = [
  {
    href: "/",
    label: "Dashboard",
    description: "Knowledge base status at a glance",
    icon: DashboardIcon,
  },
  {
    href: "/documents",
    label: "Documents",
    description: "Upload, browse, and remove articles",
    icon: DocumentsIcon,
  },
  {
    href: "/search",
    label: "Search",
    description: "Find the chunks behind an answer",
    icon: SearchIcon,
  },
  {
    href: "/ask",
    label: "Ask",
    description: "Question the knowledge base with citations",
    icon: AskIcon,
  },
];
