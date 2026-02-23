import imageio
from rembg import remove
from PIL import Image
import os
import sys

def process_video():
    input_path = 'app/ui/static/Start_Mia.mp4'
    output_webp = 'app/ui/static/Start_Mia_transparent.webp'
    output_png = 'app/ui/static/Start_Mia_first_frame.png'
    
    print("Reading video...")
    reader = imageio.get_reader(input_path)
    fps = reader.get_meta_data()['fps']
    
    frames = []
    print("Processing frames...")
    for i, frame in enumerate(reader):
        img = Image.fromarray(frame)
        out_img = remove(img)
        frames.append(out_img)
        if i % 10 == 0:
            print(f"Processed frame {i}")
            
    print(f"Total frames: {len(frames)}")
    
    # Save the first frame natively
    frames[0].save(output_png)
    
    # Save the full animation
    print("Saving animated WebP...")
    frames[0].save(output_webp, save_all=True, append_images=frames[1:], duration=int(1000/fps), loop=0)
    print(f"Done! Animation duration is {len(frames)/fps:.2f} seconds.")

if __name__ == "__main__":
    process_video()
