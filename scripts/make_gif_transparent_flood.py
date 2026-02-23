import sys
from PIL import Image

def is_bg_color(r, g, b):
    # Generous threshold to catch all the yellowish and bluish checkerboard colors
    return r > 140 and g > 140 and b > 120

def process_frame(frame, frame_idx):
    data = list(frame.getdata())
    w, h = frame.size
    
    visited = set()
    queue = []
    
    # Add all edge pixels that are light colored
    for x in range(w):
        if is_bg_color(*data[x][:3]): 
            p = (x, 0)
            if p not in visited:
                visited.add(p)
                queue.append(p)
        
        idx = (h-1)*w + x
        if is_bg_color(*data[idx][:3]): 
            p = (x, h-1)
            if p not in visited:
                visited.add(p)
                queue.append(p)
                
    for y in range(h):
        idx = y*w
        if is_bg_color(*data[idx][:3]): 
            p = (0, y)
            if p not in visited:
                visited.add(p)
                queue.append(p)
                
        idx = y*w + w - 1
        if is_bg_color(*data[idx][:3]): 
            p = (w-1, y)
            if p not in visited:
                visited.add(p)
                queue.append(p)
                
    # 4-way flood fill to prevent leaking diagonally across thin outlines
    head = 0
    while head < len(queue):
        x, y = queue[head]
        head += 1
        
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                if (nx, ny) not in visited:
                    idx = ny * w + nx
                    r, g, b, a = data[idx]
                    if is_bg_color(r, g, b):
                        visited.add((nx, ny))
                        queue.append((nx, ny))
                            
    # Apply transparency
    new_data = []
    for y in range(h):
        for x in range(w):
            if (x, y) in visited:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(data[y*w + x])
                
    frame.putdata(new_data)
    
    # Just a debug print to see if any frame fills significantly more than others
    # Expected background size is roughly 65000 pixels
    if len(visited) > 70000:
        print(f"Warning: Frame {frame_idx} filled {len(visited)} pixels (possible leak)")
        
    return frame

def convert_gif_flood_fill(input_path, output_path):
    img = Image.open(input_path)
    frames = []
    
    frame_idx = 0
    try:
        while True:
            frame = img.copy().convert("RGBA")
            processed = process_frame(frame, frame_idx)
            frames.append(processed)
            img.seek(img.tell() + 1)
            frame_idx += 1
    except EOFError:
        pass
        
    print(f"Processed {len(frames)} frames. Saving as WebP...")
    
    # Save animated WebP
    frames[0].save(
        output_path, 
        save_all=True,
        append_images=frames[1:],
        duration=img.info.get('duration', 100), 
        loop=img.info.get('loop', 0),
        disposal=2 # clear frame before drawing next
    )
    print(f"Saved cleanly to {output_path}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python process_gif.py <input.gif> <output.webp>")
        sys.exit(1)
    convert_gif_flood_fill(sys.argv[1], sys.argv[2])
