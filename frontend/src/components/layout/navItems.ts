import {
  BarChart3,
  Building2,
  Clock,
  LayoutDashboard,
  PencilLine,
  Settings,
  Target,
  Users,
  Wand2,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Generate Copy', to: '/generate', icon: PencilLine },
  { label: 'History', to: '/history', icon: Clock },
  { label: 'Templates', to: '/templates', icon: Wand2 },
  { label: 'Brands & Products', to: '/brands', icon: Building2 },
  { label: 'Audience Segments', to: '/audience-segments', icon: Users },
  { label: 'CTA Rules', to: '/cta-rules', icon: Target },
  { label: 'Logs & Analytics', to: '/logs', icon: BarChart3 },
  { label: 'Settings', to: '/settings', icon: Settings },
];
