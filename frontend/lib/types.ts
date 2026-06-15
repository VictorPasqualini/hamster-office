export interface WorkspaceBrief {
  id: string;
  slug: string;
  name: string;
  role: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string | null;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  workspaces: WorkspaceBrief[];
}

export interface Project {
  id: string;
  name: string;
  client_name?: string | null;
  description?: string | null;
  status: string;
}

export type TaskStatus =
  | "backlog"
  | "todo"
  | "in_progress"
  | "review"
  | "blocked"
  | "done"
  | "canceled";

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description?: string | null;
  status: TaskStatus;
  priority: "low" | "medium" | "high" | "urgent";
  due_date?: string | null;
  assignee_kind?: string | null;
  assignee_id?: string | null;
}

export interface Room {
  id: string;
  type: string;
  name?: string | null;
  topic?: string | null;
  project_id?: string | null;
}

export interface Message {
  id: string;
  room_id: string;
  author_kind: "user" | "agent" | "system";
  author_id?: string | null;
  content: string;
  parent_id?: string | null;
  agent_run_id?: string | null;
  mentions: { kind: string; id: string; name?: string }[];
  created_at?: string | null;
}

export interface Agent {
  id: string;
  name: string;
  type: string;
  persona?: string | null;
  model: string;
  temperature: number;
  tools: string[];
  is_active: boolean;
  appearance: Record<string, unknown>;
}

export interface DocumentItem {
  id: string;
  title: string;
  mime?: string | null;
  status: string;
  project_id?: string | null;
}

export interface Member {
  membership_id: string;
  user_id: string;
  name: string;
  email: string;
  role: string;
  status: string;
}

export interface Overview {
  members: number;
  projects: number;
  open_tasks: number;
  agents: number;
  documents: number;
  agent_runs: number;
  total_tokens: number;
  total_cost_usd: number;
}

export interface UsageRow {
  agent_id: string;
  name: string;
  type: string;
  total_tokens: number;
  total_cost_usd: number;
  run_count: number;
}

export interface FurnitureCatalogItem {
  code: string;
  name: string;
  category: string;
  width: number;
  depth: number;
  color: string;
  icon: string;
  walkable: boolean;
}

export interface Placement {
  id: string;
  furniture_code: string;
  x: number;
  y: number;
  rotation: number;
}

export interface OfficeAvatar {
  id: string;
  owner_kind: "user" | "agent";
  owner_id: string;
  name: string;
  color: string;
  home_x: number;
  home_y: number;
}

export interface PresenceEntry {
  avatar_id: string;
  x: number;
  y: number;
  facing?: string;
  status?: string;
  name?: string;
  color?: string;
  kind?: string;
}

export interface Scene {
  id: string;
  name: string;
  grid_width: number;
  grid_height: number;
  theme: string;
  furniture: Placement[];
  avatars: OfficeAvatar[];
  catalog: FurnitureCatalogItem[];
  presence: PresenceEntry[];
}

export interface AuditEvent {
  id: string;
  type: string;
  actor_kind: string;
  actor_id?: string | null;
  target_kind?: string | null;
  target_id?: string | null;
  payload: Record<string, unknown>;
  occurred_at?: string | null;
}
