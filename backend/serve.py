"""Production server: one process serves the API and the built frontend (Windows or Linux).

    python serve.py                 # listens on 0.0.0.0:8000
    python serve.py --port 80

Configuration comes from backend/.env (see .env.example).
"""
import argparse
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default=os.environ.get('HOST', '0.0.0.0'))
    ap.add_argument('--port', type=int, default=int(os.environ.get('PORT', 8000)))
    ap.add_argument('--threads', type=int, default=int(os.environ.get('THREADS', 8)))
    args = ap.parse_args()

    from django.core.wsgi import get_wsgi_application
    from django.conf import settings
    from waitress import serve

    app = get_wsgi_application()
    # warm the Russian morphology dictionaries so the first search is fast
    from corpus.text import morph
    morph()
    print(f'Rucorpus listening on http://{args.host}:{args.port}')
    proxy = {}
    if settings.BEHIND_HTTPS_PROXY:
        proxy = {'trusted_proxy': '127.0.0.1', 'trusted_proxy_headers': {'x-forwarded-proto'}}
    serve(app, host=args.host, port=args.port, threads=args.threads, url_scheme='http', **proxy)


if __name__ == '__main__':
    main()
