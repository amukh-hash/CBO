from PIL import Image

def test_heuristic():
    img = Image.open('app/ui/static/DC_snuggle.gif')
    frame = img.copy().convert("RGBA")
    data = list(frame.getdata())
    w, h = frame.size
    
    new_data = []
    
    for r, g, b, a in data:
        # If blue is very high and it's generally bright
        if b >= 200 and r >= 170 and g >= 170:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append((r, g, b, a))
            
    frame.putdata(new_data)
    frame.save('app/ui/static/test_frame.png')
    
if __name__ == '__main__':
    test_heuristic()
