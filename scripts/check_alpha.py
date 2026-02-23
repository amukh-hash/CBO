from PIL import Image

def analyze():
    img = Image.open('app/ui/static/Start_Mia_first_frame.png')
    print("Mode:", img.mode)
    
    # Check if there's any pixel with alpha < 255
    data = img.getdata()
    transparent_pixels = 0
    for p in data:
        if len(p) == 4 and p[3] < 255:
            transparent_pixels += 1
            
    print(f"Transparent pixels: {transparent_pixels} / {len(data)}")

if __name__ == "__main__":
    analyze()
