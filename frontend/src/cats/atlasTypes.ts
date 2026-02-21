export type FrameRect = {
  id: number;
  x: number;
  y: number;
  w: number;
  h: number;
};

export type TimelineEntry = [number, number];

export type ClipPage = {
  imagePath: string;
  frames?: FrameRect[];
};

export type Clip = {
  frames?: number[];
  fps: number;
  loop: boolean;
  imagePath?: string;
  return_to?: string | null;
  frame_count?: number;
  pages?: ClipPage[];
  timeline?: TimelineEntry[];
  tags?: string[];
  cooldown_ms?: number;
  hold_last_ms?: number;
};

export type SequencePlaylist = {
  mode: "sequence";
  idle_clip?: string;
  idle_hold_ms?: number;
  between_hold_ms?: number;
  clips: string[];
};

export type WeightedRandomPlaylist = {
  mode: "weighted_random";
  idle_clip?: string;
  idle_hold_ms_range?: [number, number];
  between_hold_ms_range?: [number, number];
  pool: [string, number][];
};

export type Playlist = SequencePlaylist | WeightedRandomPlaylist;

export type AtlasLibrary = {
  foundation?: string;
  groups?: Record<string, string[]>;
  playlists?: Record<string, Playlist>;
};

export type AtlasMeta = {
  version?: number;
  imagePath: string;
  frameW: number;
  frameH: number;
  cols: number;
  rows: number;
  frames?: FrameRect[];
  clips: Record<string, Clip>;
  default_clip?: string;
  library?: AtlasLibrary;
};
