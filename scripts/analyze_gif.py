import imageio
import numpy as np

def analyze():
    reader = imageio.get_reader('app/ui/static/Start_Mia.gif')
    frame = reader.get_data(0)
    
    if frame.shape[2] == 4:
        rgb_frame = frame[:, :, :3]
    else:
        rgb_frame = frame
        
    # Get edge pixels to build background palette FROM FIRST FRAME
    top = rgb_frame[:10, :].reshape(-1, 3)
    bottom = rgb_frame[-10:, :].reshape(-1, 3)
    left = rgb_frame[:, :10].reshape(-1, 3)
    right = rgb_frame[:, -10:].reshape(-1, 3)
    
    edge_pixels = np.vstack([top, bottom, left, right])
    edge_colors = set(tuple(p) for p in edge_pixels)
    
    print(f"Found {len(edge_colors)} unique background colors on edges.")
    
    for fn in [0, 50, 100, 150]:
        frame = reader.get_data(fn)
        if frame.shape[2] == 4:
            rgb_f = frame[:, :, :3]
        else:
            rgb_f = frame
        pixels = rgb_f.reshape(-1, 3)
        remaining = 0
        for p in pixels:
            if tuple(p) not in edge_colors:
                remaining += 1
                
        print(f"Remaining pixels in frame {fn}: {remaining} / {len(pixels)} ({(remaining/len(pixels))*100:.1f}%)")
    
if __name__ == "__main__":
    analyze()
