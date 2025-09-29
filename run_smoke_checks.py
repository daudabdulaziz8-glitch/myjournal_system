from journal import create_app

app = create_app()
client = app.test_client()

routes = [
    ('GET', '/'),
    ('GET', '/login'),
    ('GET', '/register'),
    ('GET', '/issues'),
    ('GET', '/dashboard'),  # requires login -> should redirect
    ('GET', '/admin/submissions'),  # requires admin -> should redirect/403
    ('GET', '/reviewer/queue'),  # requires reviewer -> redirect
]

for method, path in routes:
    resp = client.open(path, method=method)
    print(f'{method} {path} -> {resp.status_code}')
    if resp.status_code >= 500:
        print('  ERROR response body:')
        print(resp.get_data(as_text=True)[:800])
