"""Start the local lab and open a browser after the health check succeeds."""
import argparse
import socket
import threading
import time
import urllib.request
import webbrowser


def open_when_ready(url):
    for _ in range(100):
        try:
            with urllib.request.urlopen(url + '/api/health', timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except OSError:
            time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    url = f'http://localhost:{args.port}'
    try:
        with socket.socket() as check:
            check.bind(('127.0.0.1', args.port))
    except OSError:
        print(f'Port {args.port} is already in use. Close the previous Graph Lab window, or use --port 8001.')
        return 1
    print(f'Graph Processing Lab: {url}\nKeep this window open. Press Ctrl+C to stop.')
    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
    import uvicorn
    uvicorn.run('graphlab.api:app', host='127.0.0.1', port=args.port)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
