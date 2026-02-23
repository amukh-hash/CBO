import sys
from PIL import Image

def is_bg_color(r, g, b):
    # Generous threshold to catch all the yellowish and bluish checkerboard colors
    return r > 140 and g > 140 and b > 120

def test_flood_fill():
    img = Image.open('app/ui/static/DC_snuggle.gif')
    frame = img.copy().convert("RGBA")
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
                
    # 8-way flood fill
    head = 0
    while head < len(queue):
        x, y = queue[head]
        head += 1
        
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0: continue
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
    frame.save('app/ui/static/test_frame_flood.png')
    print(f"Removed {len(visited)} background pixels out of {w*h}")

if __name__ == '__main__':
    # Increase recursion depth just in case though we are using iterative BFS
    sys.setrecursionlimit(100000)
    test_flood_fill()
