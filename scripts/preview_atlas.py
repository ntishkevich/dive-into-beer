"""Serve the atlas locally, with a frozen snapshot for Lighthouse."""

import argparse
import gzip
import logging
import os
import re
from contextlib import contextmanager
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit

from site_files import MANIFEST, ROOT, SiteFile, read_json, read_site_file_types

AUDIT_REPORT = "/beer-design-audit.html"


def project_path(root=ROOT):
    return urlsplit(read_json(root / "assets/site-metadata.json")["url"]).path


def make_server(port, root=ROOT, snapshot=None):
    root = root.resolve()
    prefixes = sorted({project_path(root), "/beer/", "/"}, key=len, reverse=True)

    def prepare(file):
        return (
            file,
            gzip.compress(file.body, compresslevel=6, mtime=0),
            sha256(file.body).hexdigest(),
        )

    frozen = None if snapshot is None else {name: prepare(file) for name, file in snapshot.items()}
    cache = {}

    def live_file(name, content_type):
        if content_type is None:
            return None
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return None
        stamp = path.stat().st_mtime_ns, content_type
        if name not in cache or cache[name][0] != stamp:
            cache[name] = stamp, prepare(SiteFile(path.read_bytes(), content_type))
        return cache[name][1]

    class PreviewHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            self.serve_file(send_body=True)

        def do_HEAD(self):
            self.serve_file(send_body=False)

        def serve_file(self, *, send_body):
            pathname = urlsplit(self.path).path or "/"
            prefix = next(prefix for prefix in prefixes if pathname.startswith(prefix))
            name = pathname[len(prefix) :] or "index.html"
            try:
                if frozen is not None:
                    entry = frozen.get(name)
                elif pathname == AUDIT_REPORT:
                    entry = live_file("output/beer-design-audit.html", "text/html; charset=utf-8")
                else:
                    types = read_site_file_types((root / MANIFEST).read_bytes())
                    entry = live_file(name, types.get(name))
            except (OSError, ValueError) as error:
                logging.error("Cannot serve %s: %s", pathname, error)
                self.send_error(500, "Unable to read the site files")
                return
            if entry is None:
                self.send_error(404, "Not found")
                return

            file, compressed, digest = entry
            accepts_gzip = re.search(r"\bgzip\b", self.headers.get("Accept-Encoding", ""))
            body = compressed if accepts_gzip else file.body
            self.send_response(200)
            self.send_header("Content-Type", file.content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Artifact-Sha256", digest)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Vary", "Accept-Encoding")
            if accepts_gzip:
                self.send_header("Content-Encoding", "gzip")
            self.end_headers()
            if send_body:
                self.wfile.write(body)

    return ThreadingHTTPServer(("127.0.0.1", port), PreviewHandler)


@contextmanager
def preview_server(root=ROOT, snapshot=None):
    with make_server(0, root, snapshot) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve the atlas on localhost.")
    parser.add_argument("--port", type=int, default=os.environ.get("BEER_PREVIEW_PORT") or "4173")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    with make_server(args.port) as server:
        print(f"Beer atlas: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
