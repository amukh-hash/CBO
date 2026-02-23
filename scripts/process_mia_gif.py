import imageio
import numpy as np
from PIL import Image
from collections import deque
from rembg import remove

PAD = 60  # pixels of padding on each side

def process_video():
    input_path = 'app/ui/static/Start_Mia.gif'
    output_webp = 'app/ui/static/Start_Mia_transparent.webp'
    
    print("Reading gif...")
    reader = imageio.get_reader(input_path)
    fps = reader.get_meta_data().get('fps', 30)
    duration_ms = reader.get_meta_data().get('duration', 33)
    
    raw_frames = [f[:, :, :3] if f.shape[2] == 4 else f for f in reader]
    orig_h, orig_w, _ = raw_frames[0].shape
    
    # --- Detect background color from the corners of the first frame ---
    first = raw_frames[0]
    bg_color = first[0, 0].copy()  # top-left pixel as reference
    print(f"Detected background color: {bg_color}")
    
    # --- Pad every frame with background color so Mia isn't clipped ---
    frames = []
    for f in raw_frames:
        padded = np.full((orig_h + 2 * PAD, orig_w + 2 * PAD, 3), bg_color, dtype=np.uint8)
        padded[PAD:PAD + orig_h, PAD:PAD + orig_w] = f
        frames.append(padded)
    
    h, w, _ = frames[0].shape
    print(f"Original size: {orig_w}x{orig_h}, padded size: {w}x{h}")
    
    # --- PHASE 1: Temporal Background Flood Fill ---
    first = frames[0]
    top = first[0:10, :].reshape(-1, 3)
    left = first[10:h-100, 0:10].reshape(-1, 3)
    right = first[10:h-100, w-10:w].reshape(-1, 3)
    edge_pixels = np.vstack([top, left, right])
    edge_colors = set(tuple(p) for p in edge_pixels)
    
    master_mask = np.zeros((h, w), dtype=bool)
    
    def get_flood_mask(img):
        mask = np.zeros((h, w), dtype=bool)
        q = deque()
        for x in range(w):
            if tuple(img[0, x]) in edge_colors:
                q.append((0, x))
                mask[0, x] = True
        while q:
            y, x = q.popleft()
            for dy, dx in ((-1,0), (1,0), (0,-1), (0,1)):
                ny, nx = y+dy, x+dx
                if 0 <= ny < h and 0 <= nx < w and not mask[ny, nx]:
                    if tuple(img[ny, nx]) in edge_colors:
                        mask[ny, nx] = True
                        q.append((ny, nx))
        return mask

    print('Building dynamic master mask over all frames...')
    for i, f in enumerate(frames):
        master_mask |= get_flood_mask(f)
        if i % 20 == 0:
            print(f"Flood fill frame {i}...")
            
    # Define the safe box where cat body lives (to prevent flood leak deletion)
    # Coordinates are in the PADDED frame space (offset by PAD=60)
    # Original cat body spans roughly y=10..260, x=100..479 (full width incl. tail)
    safe_mask = np.zeros((h, w), dtype=bool)
    safe_mask[PAD + 10 : PAD + orig_h, PAD + 100 : PAD + orig_w] = True
    
    # Area that we strictly FORCE to 0 opacity regardless of AI
    strict_bg = master_mask & (~safe_mask)
    
    # --- PHASE 2: AI Matting & Hybrid Merge ---
    out_frames = []
    print("Processing frames with hybrid rembg + flood mask...")
    for i, frame in enumerate(frames):
        img_pil = Image.fromarray(frame).convert("RGBA")
        
        # AI removes outer background nicely, default parameters preserve the tail!
        out_img = remove(img_pil)
        
        # Convert to numpy to apply our strict BG override for the tail loop hole
        rgba = np.array(out_img)
        rgba[strict_bg, 3] = 0
        
        # Clean up semi-transparent checkerboard residue from rembg:
        # - Kill very low alpha pixels (checkerboard bleed-through)
        # - Boost high alpha to fully opaque (clean cat body edges)
        alpha = rgba[:, :, 3]
        rgba[alpha < 50, 3] = 0
        rgba[alpha > 200, 3] = 255
        
        out_frames.append(Image.fromarray(rgba))
        if i % 10 == 0:
            print(f"Hybrid processed frame {i}")
            
    print("Saving animated WebP...")
    out_frames[0].save(output_webp, save_all=True, append_images=out_frames[1:], duration=duration_ms, loop=0)
    print("Done!")

if __name__ == "__main__":
    process_video()
