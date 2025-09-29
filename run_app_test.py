from journal import create_app

app = create_app()

with app.test_client() as client:
    resp = client.get('/')
    print('Status code:', resp.status_code)
    print(resp.get_data(as_text=True)[:1000])
