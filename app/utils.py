import base64
import subprocess
import os

def generate_changelog():
    """
    Erzeugt CHANGELOG.md automatisch aus den letzten git-Commits (Datum + Message).
    """
    proj_dir = os.path.dirname(os.path.dirname(__file__))
    changelog_path = os.path.join(proj_dir, 'CHANGELOG.md')
    try:
        log = subprocess.check_output(
            ['git', 'log', '--pretty=format:- %ad %s', '--date=short'],
            cwd=proj_dir, encoding='utf-8', stderr=subprocess.STDOUT
        )
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write('# Changelog (automatisch generiert)\n\n')
            f.write(log)
    except Exception as e:
        return str(e)
    return 'Changelog erfolgreich generiert.'


def generate_ai_changelog(api_key, n=10):
    """
    Generiert eine verständliche KI-Zusammenfassung der letzten n Git-Commits mit OpenAI GPT.
    api_key: OpenAI API Key (z.B. aus Umgebungsvariable oder Eingabe)
    n: Anzahl der letzten Commits
    Gibt die KI-Zusammenfassung als String zurück.
    """
    import requests
    proj_dir = os.path.dirname(os.path.dirname(__file__))
    log = subprocess.check_output(
        ['git', 'log', f'-n{n}', '--pretty=format:%h %ad %s', '--date=short'],
        cwd=proj_dir, encoding='utf-8', stderr=subprocess.STDOUT
    )
    prompt = (
        "Fasse die folgenden Git-Commits als verständlichen, strukturierten Changelog für Anwender zusammen. "
        "Nutze eine Gliederung nach Features, Bugfixes, Verbesserungen, falls möglich. Schreibe auf Deutsch.\n\n" + log
    )
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=60
    )
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Fehler bei OpenAI: {response.status_code} {response.text}"

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
