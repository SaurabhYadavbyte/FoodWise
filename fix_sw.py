import re

with open('app/static/service-worker.js', 'r', encoding='utf-8') as f:
    content = f.read()

target = r"const privateRoutes = \['/dashboard', '/food', '/meals', '/waste', '/login', '/register', '/logout'\];"
replacement = """const privateRoutes = [
    '/dashboard',
    '/food',
    '/meals',
    '/waste',
    '/login',
    '/register',
    '/logout',
    '/feedback',
    '/admin'
];"""

content = re.sub(target, replacement, content)

with open('app/static/service-worker.js', 'w', encoding='utf-8') as f:
    f.write(content)
