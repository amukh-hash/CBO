import imageio
import numpy as np
from PIL import Image

def process_video():
    input_path = 'public/GIF/Wheel_Mia.gif'
    output_webp = 'app/ui/static/Wheel_Mia_transparent.webp'
    
    print("Reading gif...")
    reader = imageio.get_reader(input_path)
    
    fps = reader.get_meta_data().get('fps', 30)
    duration_ms = reader.get_meta_data().get('duration', 33)
    
    frames = []
    print("Processing frames with color keying (GIF)...")
    for i, frame in enumerate(reader):
        # Handle RGBA transparent GIFs or RGB GIFs
        if frame.shape[2] == 4:
            rgb_frame = frame[:, :, :3]
            alpha_orig = frame[:, :, 3]
        else:
            rgb_frame = frame
            alpha_orig = np.ones((frame.shape[0], frame.shape[1]), dtype=np.uint8) * 255
            
        # Create an alpha channel based on the color condition
        alpha = alpha_orig.copy()
        
        # Identify the checkerboard pixels (very light grey/white)
        mask = (rgb_frame[:, :, 0] > 200) & (rgb_frame[:, :, 1] > 200) & (rgb_frame[:, :, 2] > 200)
        
        # Set alpha to 0 for these pixels
        alpha[mask] = 0
        
        # Combine RGB and Alpha
        rgba_frame = np.dstack((rgb_frame, alpha))
        
        img = Image.fromarray(rgba_frame)
        frames.append(img)
        
        if i % 10 == 0:
            print(f"Processed frame {i}")
            
    print(f"Total frames: {len(frames)}")
    
    # Save the full animation
    print("Saving animated WebP...")
    frames[0].save(output_webp, save_all=True, append_images=frames[1:], duration=duration_ms, loop=0)
    print(f"Done! Animation duration is {(len(frames)*duration_ms)/1000:.2f} seconds.")

if __name__ == "__main__":
    process_video()
