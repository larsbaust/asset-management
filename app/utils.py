import base64

def svg_placeholder(name, size=48):
    # Initialen extrahieren (max. 2 Buchstaben)
    initials = ''.join([part[0].upper() for part in name.split() if part])[:2]
    # Einfache Farbcodierung basierend auf dem Namen
    color = "#" + ''.join([format(ord(c)*123 % 256, '02x') for c in initials])[:6]
    svg = f'''
    <svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
      <rect width="100%" height="100%" fill="{color}"/>
      <text x="50%" y="55%" font-size="{size//2}" text-anchor="middle" fill="#fff" dy=".3em" font-family="Arial">{initials}</text>
    </svg>
    '''
    data = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{data}"
