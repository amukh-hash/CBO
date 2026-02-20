export type FrameRect = {
  id: number;
  x: number;
  y: number;
  w: number;
  h: number;
};

export type Clip = {
  frames: number[];
  fps: number;
  loop: boolean;
};

export type AtlasMeta = {
  imagePath: string;
  frameW: number;
  frameH: number;
  cols: number;
  rows: number;
  frames: FrameRect[];
  clips: Record<string, Clip>;
};
