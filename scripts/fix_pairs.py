import re
path = 'scripts/batch_migrate2.py'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Remove count param from triple tuples: (a, b, N) -> (a, b)
c = re.sub(r"\("("[^"]*",\s*"[^"]*e.sub(r\"\\(\"(\"[^\"]*\",\\s*\"[^\"]*\"\),\\s*\\d+\\)\", r'(\\1)', c)\nc = re.sub(r\"\\(\\('[^']*',\\s*'[^']*'\\),\\s*\\d+\\)\", r'(\\1)', c)\n\nwith open(path, 'w', encoding='utf-8') as f:\n    f.write(c)\nprint('Fixed')\n"}