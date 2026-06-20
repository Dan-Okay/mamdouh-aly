#!/usr/bin/env python3
"""Static server with HTTP Range support (needed for <video> scroll-scrubbing/seeking)."""
import http.server, os, re, sys, functools

class RangeHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        rng = self.headers.get('Range')
        if not rng:
            self.send_header_accept = True
            f = super().send_head()
            return f
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404); return None
        fs = os.fstat(f.fileno()); size = fs.st_size
        m = re.match(r'bytes=(\d*)-(\d*)', rng)
        start, end = m.group(1), m.group(2)
        start = int(start) if start else 0
        end = int(end) if end else size - 1
        end = min(end, size - 1)
        length = end - start + 1
        ctype = self.guess_type(path)
        self.send_response(206)
        self.send_header('Content-Type', ctype)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(length))
        self.end_headers()
        f.seek(start)
        self.copy_range(f, length)
        f.close()
        return None

    def copy_range(self, f, length):
        bufsize = 64 * 1024
        while length > 0:
            chunk = f.read(min(bufsize, length))
            if not chunk:
                break
            try:
                self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                break
            length -= len(chunk)

    def end_headers(self):
        # advertise range support on normal responses too
        if not self.headers.get('Range'):
            self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4599
    directory = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    handler = functools.partial(RangeHandler, directory=directory)
    httpd = http.server.ThreadingHTTPServer(('0.0.0.0', port), handler)
    print(f'Serving {directory} on :{port} with Range support')
    httpd.serve_forever()
