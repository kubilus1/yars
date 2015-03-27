import os
import sys
import urllib2
import urlparse
import subprocess

import simplehttpd

PORT = 8080

class MyRequestHandler(simplehttpd.AJAXRequestHandler):
    def do_GET(self):
        print "DO_GET"
        (scm, netloc, path, params, query, fragment) = urlparse.urlparse(
            self.path, 'http')
        print "scm:", scm
        print "netloc:", netloc
        print "path:", path
        print "params:", params
        print "query:", query
        print "fragment:", fragment
        print "Command:", self.command
        #u = urlparse.urlunparse((scm, "www.titantv.com", path, params, query, fragment))
        #print "URL:", u
        query_dict = dict(qc.split("=") for qc in query.split("&"))
        print query_dict

        ctype = self.guess_type(path)
        print "Guessed:", ctype
        #f = self.send_head(u)


        #self.send_response(200)
        #self.send_header("Content-type", ctype)
        #self.end_headers()

        #f = urllib2.urlopen(u)
        #if f:
        #    self.copyfile(f, self.wfile)
        #    f.close()

        ret = False
        mname = path.lstrip('/')
        if hasattr(self, mname):
            method = getattr(self, mname)
            ret = method(query_dict)

        if ret:
            self.send_response(200)
        else:
            self.send_response(404)

        self.end_headers()
        self.wfile.write(ret) 


    def do_review(self, *args, **kwds):
        print args
        print kwds

        if args:
            arg_dict = args[0]

        outdata = """
        <html>
        <head>
        <style>
          body {background-color:lightblue}
          h1   {color:blue}
          p {
                display: block;
                margin-top: 0;
                margin-bottom: 0;
                margin-left: 0;
                margin-right: 0;
            }
        </style>
        </head>
        <body>
        <code>
        <pre>
        """
    
        color = False
        old_num = 0
        new_num = 0

        with open('patch.diff', 'r') as h:
            
            for line in h.readlines():

                
                if line.startswith("Index"):
                    color = False
                    old_num = 0
                    new_num = 0
                elif line.startswith("@@"):
                    print line
                    splits = line.split()
                    old_num = abs(int(splits[1].split(',')[0]))
                    new_num = abs(int(splits[2].split(',')[0]))
                elif line.startswith('+'):
                    outdata += "<p style='background-color:#88FF88'>"
                    outdata += "     %04d " % (new_num)
                    color = True
                    new_num += 1
                elif line.startswith('-'):
                    outdata += "<p style='background-color:#FF8888'>"
                    outdata += "%04d      " % (old_num)
                    color = True
                    old_num += 1
                elif old_num == new_num:
                    outdata += "%04d      " % (new_num)
                    old_num += 1
                    new_num += 1
                else:
                    outdata += "%04d %04d " % (old_num, new_num)
                    old_num += 1
                    new_num += 1

                outdata += "%s" % (
                        line.replace('<','&lt;').replace('>','&gt;')
                )

                if color:
                    outdata += "</p>"
                    color = False

        outdata += """
        </pre>
        </code>
        </body>
        </html>
        """
    
        return outdata

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
    httpd = simplehttpd.MyTCPServer((name, PORT), handler)
    httpd.server_name = name
    httpd.server_port = PORT

    os.putenv("HTTP_HOST","%s:%s" % (name, PORT))
    os.environ["HTTP_HOST"] = "%s:%s" %(name, PORT)
    print os.getenv("HTTP_HOST")

    print "Serving at port %s" % PORT
    httpd.serve_forever()

