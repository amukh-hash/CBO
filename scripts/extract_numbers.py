from PIL import Image
import os

def extract():
    img_path = 'app/ui/static/Text_Number_Sheet.png'
    out_dir = 'app/ui/static/numbers'
    os.makedirs(out_dir, exist_ok=True)
    
    img = Image.open(img_path).convert("RGBA")
    width, height = img.size
    
    # Pre-process image to make white transparent
    data = img.getdata()
    new_data = []
    tolerance = 240
    for r, g, b, a in data:
        if r > tolerance and g > tolerance and b > tolerance:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    
    cell_w = width / 7.0
    cell_h = height / 2.0
    
    def get_cell(c, r):
        left = int(c * cell_w)
        top = int(r * cell_h)
        right = int((c + 1) * cell_w)
        bottom = int((r + 1) * cell_h)
        cropped = img.crop((left, top, right, bottom))
        return cropped

    # Top row: 0 1 2 3 4 5 6
    for i in range(7):
        num_img = get_cell(i, 0)
        num_img.save(os.path.join(out_dir, f"{i}.png"))
        
    # Bottom row: 7 5 6 7 9 8 9
    # c=0 -> 7
    get_cell(0, 1).save(os.path.join(out_dir, "7.png"))
    # c=5 -> 8
    get_cell(5, 1).save(os.path.join(out_dir, "8.png"))
    # c=4 or c=6 -> 9
    get_cell(4, 1).save(os.path.join(out_dir, "9.png"))
    
    print("Done extracting 0-9")

if __name__ == "__main__":
    extract()
