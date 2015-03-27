#!/usr/bin/env python

import os
import sys
import cgi
import stat
import time
import json
import socket
import select
import urllib
import urllib2
import urlparse
import multiprocessing

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import CGIHTTPServer
import SocketServer

PORT = 8080

class MyTCPServer(SocketServer.ForkingTCPServer):
    manager = multiprocessing.Manager()
    CACHE = manager.dict()

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        SocketServer.ForkingTCPServer.server_bind(self)

class AJAXRequestHandler(CGIHTTPServer.CGIHTTPRequestHandler):

    cgi_directories = [""]
    exposed_methods = []

    def __init__(self, *kwds, **args):
        CGIHTTPServer.CGIHTTPRequestHandler.__init__(self, *kwds, **args)

    def do_GET(self):
        (scm, netloc, path, params, query, fragment) = urlparse.urlparse(
            self.path, 'http')

        query_dict = {}
        if query: 
            query_dict = dict(qc.split("=") for qc in query.split("&"))
            print query_dict

        ctype = self.guess_type(path)

        ret = ""
        mname = path.lstrip('/')
        if mname not in self.exposed_methods:
            #print "Not an exposed method: ", mname
            #self.send_response(404)
            #self.end_headers()
            #return
            CGIHTTPServer.CGIHTTPRequestHandler.do_GET(self)
            return 

        if hasattr(self, mname):
            print "I has that attr"
            self.send_response(200)
            #self.send_header("Content-type", "text/html")
            method = getattr(self, mname)
            ret = method(query_dict)
        
        print "Content length: ", len(ret)   
            
        self.send_header("Content-Length", str(len(ret)))
        self.end_headers()
        self.wfile.write(ret) 
        print "Done with do_GET"
        return True

    def test(self, *args):
        print "TEST:", args
        return {"TEST":args}

    def do_POST(self):
        print "POST"
        ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        print "CTYPE:", ctype
        length = int(self.headers.getheader('content-length'))
        print "LEN:", length
        if ctype == 'multipart/form-data':
            self.body = cgi.parse_multipart(self.rfile, pdict)
            print "BODY:", self.body
        elif ctype == 'application/x-www-form-urlencoded':
            qs = self.rfile.read(length)
            "QS:", qs
            self.body = cgi.parse_qs(qs, keep_blank_values=1)
            print "BODY:", self.body
        else:
            self.body = {} # Unknown content-type
            print "BODY:", self.body
        # throw away additional data [see bug #427345]
        while select.select([self.rfile._sock], [], [], 0)[0]:
            if not self.rfile._sock.recv(1):
                break
        ret = self.handle_data()
        self.wfile.write(json.dumps(ret))

        #self.do_GET()
    def handle_data(self):
        print "handle_data"
        print "BODY:", self.body
        for key in self.body:
            data = json.loads(key)
            mname = data[0]
            if hasattr(self, mname):
                method = getattr(self, mname)
                ret = method(data[1:])
            else:
                print "Method (%s) not valid" % mname
        #print "DATA: ", self.rfile.read()
        print "handle data"
        return ret

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = StringIO()
        displaypath = cgi.escape(urllib.unquote(self.path))
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<title>Directory listing for %s</title>\n" % displaypath)
        f.write("<head><style> td { padding-left: 2em; } \n")
        f.write("th { padding-left: 2em; } </style></head> \n")
        f.write("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath)
        f.write("<hr>\n<table>\n")
        f.write("<tr><th></th><th ALIGN=left>Name</th><th>Size</th><th ALIGN=right>Date Modified</th></tr>\n")
        for name in list:
            f.write('<tr>\n')
            fullname = os.path.join(path, name)
            stats = os.stat(fullname)
            size = stats[stat.ST_SIZE]
            mtime = time.ctime(stats[stat.ST_MTIME])
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write('<td></td>')
            f.write('<td><a href="%s">%s</a></td>\n'
                    % (urllib.quote(linkname), cgi.escape(displayname)))
            f.write('<td>%s</td><td>%s</td>' % (size, mtime))
        f.write("</table>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    #do_HEAD = do_GET
    #do_PUT = do_GET
    #do_DELETE = do_GET

if __name__ == "__main__":
    argc = len(sys.argv)
    if argc >= 2:
        path = sys.argv[1]
        os.chdir(path)
    if argc >= 3:
        PORT = int(sys.argv[2])

    print "Running from %s" % os.getcwd()

    name = ""
    handler = MyRequestHandler
    httpd = MyTCPServer((name, PORT), handler)
    httpd.server_name = name
    httpd.server_port = PORT

    os.putenv("HTTP_HOST","%s:%s" % (name, PORT))
    os.environ["HTTP_HOST"] = "%s:%s" %(name, PORT)
    print os.getenv("HTTP_HOST")

    print "Serving at port %s" % PORT
    httpd.serve_forever()
