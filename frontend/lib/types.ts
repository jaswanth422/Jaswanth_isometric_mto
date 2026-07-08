export type Category =
  | "PIPE"
  | "FITTING"
  | "FLANGE"
  | "VALVE"
  | "GASKET"
  | "BOLT"
  | "SUPPORT"
  | "INSTRUMENTATION";

export type Unit = "M" | "EA" | "NO" | "SET";

export type VerificationStatus = "match" | "conflict" | "unverified" | "no_bom_available";

export interface DrawingMeta {
  drawing_no: string | null;
  revision: string | null;
  line_number: string | null;
  nps: string | null;
  material_class: string | null;
  service: string | null;
}

export interface MTOItem {
  item_no: number;
  category: Category;
  description: string;
  size_nps: string | null;
  schedule_rating: string | null;
  material_spec: string | null;
  end_type: string | null;
  quantity: number;
  unit: Unit;
  length_m: number | null;
  confidence: number | null;
  remarks: string | null;
  derived_from: string | null;
  source_page: number | null;
  verification_status: VerificationStatus;
}

export interface MTOSummary {
  total_pipe_length_m: number;
  fittings: number;
  flanges: number;
  valves: number;
  gaskets: number;
  bolt_sets: number;
  supports: number;
  instrumentation_connections: number;
  field_welds: number;
}

export interface MTOResponse {
  drawing_meta: DrawingMeta;
  items: MTOItem[];
  summary: MTOSummary;
  needs_review: number[];
  mock: boolean;
  provider: string;
  mock_reason: string | null;
  mock_details: string | null;
}

export interface ApiError {
  detail: string;
}
