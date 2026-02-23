import sys
from PIL import Image

def make_gif_transparent(input_path, output_path):
    # Open the GIF
    img = Image.open(input_path)
    
    # We'll collect the processed frames
    frames = []
    
    # If the GIF has a palette, this might be tricky if the background
    # color isn't a single clear index, but we'll convert to RGBA to be safe
    
    # Assume the color at (0, 0) is the background color we want to remove
    # (Checking the first frame)
    first_frame = img.copy().convert("RGBA")
    bg_color = first_frame.getpixel((0, 0))
    print(f"Detected background color: {bg_color}")
    
    # Tolerance for similar colors
    tolerance = 20
    
    # Process each frame
    try:
        while True:
            # Convert frame to RGBA
            frame = img.copy().convert("RGBA")
            data = frame.getdata()
            new_data = []
            
            for item in data:
                # If pixel is close to background, make it transparent
                r, g, b, a = item
                if (abs(r - bg_color[0]) < tolerance and 
                    abs(g - bg_color[1]) < tolerance and 
                    abs(b - bg_color[2]) < tolerance):
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            
            frame.putdata(new_data)
            
            # For saving as GIF, we need to handle transparency carefully
            # PIL can save RGBA as GIF but results vary. Usually best to keep as PNG
            # if we just need an animated image with alpha in modern browsers.
            # OR we can save the GIF with the disposal methods configured
            
            # Let's try to just write standard GIF with a specific transparent color index
            # This requires converting back to P mode with a transparency index
            # Actually, modern web supports APNG or WebP better for true alpha animation.
            
            # Let's just try to build the RGBA frames and we'll save as WebP 
            # or try saving as GIF if Pillow supports it well enough.
            frames.append(frame)
            
            img.seek(img.tell() + 1)
    except EOFError:
        pass # End of sequence
        
    print(f"Processed {len(frames)} frames.")
    
    # Save as animated WebP if the output ends in .webp, 
    # else try GIF (GIF only supports 1-bit transparency so rough edges might appear)
    frames[0].save(
        output_path, 
        save_all=True,
        append_images=frames[1:],
        duration=img.info.get('duration', 100), 
        loop=img.info.get('loop', 0),
        disposal=2 # clear frame before drawing next
    )
    print(f"Saved {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python make_gif_transparent.py <input.gif> <output.gif|webp>")
        sys.exit(1)
    make_gif_transparent(sys.argv[1], sys.argv[2])
