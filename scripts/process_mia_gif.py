import imageio
from rembg import remove, new_session
from PIL import Image
import numpy as np

def process_gif():
    input_path = 'app/ui/static/Start_Mia.gif'
    output_path = 'app/ui/static/Start_Mia_transparent.webp'
    
    # Load the GIF
    reader = imageio.get_reader(input_path)
    fps = reader.get_meta_data().get('fps', 10)
    
    session = new_session()
    
    frames = []
    print(f"Processing {input_path} with rembg...")
    for i, frame in enumerate(reader):
        print(f"Processing frame {i}")
        img = Image.fromarray(frame).convert('RGBA')
        
        # apply rembg
        out_img = remove(img, session=session, post_process_mask=True)
        frames.append(out_img)
        
    print(f"Processed {len(frames)} frames. Saving to {output_path}...")
    frames[0].save(
        output_path,
        format='WEBP',
        save_all=True,
        append_images=frames[1:],
        duration=int(1000/fps),
        loop=0,
        disposal=2
    )
    print("Done!")

if __name__ == "__main__":
    process_gif()
