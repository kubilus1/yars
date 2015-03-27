import os
import sys
import json
import shelve
import urllib2
import urlparse
import cStringIO
import subprocess

import simplehttpd

PORT = 8080

RTCCMD = os.path.expanduser("~/jazz/scmtools/eclipse/lscm")
RTCURI="https://rtp-rtc6.tivlab.raleigh.ibm.com:9443/jazz/"

HTML_HEADER="""<html>
<head>
<link rel="stylesheet" type="text/css" href="css/main.css">
</head>
<body>
<div class="all_diffs">
"""

HTML_FOOTER="</div></body></html>"

DB="yars.db"


class MyRequestHandler(simplehttpd.AJAXRequestHandler):
    exposed_methods = ["do_review", "rtc_review"]

    def get_rtc_changeset(self, uuid):
        outdata = ""
        print "Getting diff for %s" % uuid
        command = [RTCCMD, 'diff', 'changeset', uuid, '-r', RTCURI]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=False)
        return p.communicate()[0]


    def rtc_review(self, *args, **kwds):
        print args
        print kwds
        if args:
            arg_dict = args[0]

        outdata = ""

        workitem = arg_dict.get('workitem')
        
        command = [RTCCMD, 'list', 'changesets', '-W', workitem, '-j', '-r', RTCURI]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=False)
        changesets_raw = p.communicate()[0].strip()
       
        try:
            changesets = json.loads(changesets_raw)
        except ValueError:
            return "<html><body>" + changesets_raw + "</body></html>"
        
        print "Got workitem changesets.  Getting diffs..."

        uuids = []
        for cset in changesets['workitems'][0]['changesets']:
            if cset.get('state').get('complete') == True:
                uuids.append(cset['uuid'])
            else:
                print "UUID: %d is not complete, skipping" % uuid

        shelf = shelve.open(DB)

        try:
            for uuid in uuids:
                print "Getting diff for %s" % uuid
            
                #cache_data = self.server.CACHE.get(uuid)
                cache_data = shelf.get(str(uuid))
                if cache_data:
                    print "Cache hit for: ", uuid
                    cs = cStringIO.StringIO(cache_data)
                    outdata += self.render_diff(cs)
                    cs.close()
                else:
                    print "Cache miss for: ", uuid
                    diffdata = self.get_rtc_changeset(uuid)
                    
                    cs = cStringIO.StringIO(diffdata)
                    outdata += self.render_diff(cs)
                    cs.close()
                    
                    shelf[str(uuid)] = diffdata
                    outdata += diffdata
        finally:
            shelf.close()

        print "Done with rtc_review" 
        
        return HTML_HEADER + outdata + HTML_FOOTER


    def render_diff(self, diff_handle, id=None):
        outdata = """
        <code>
        <pre>
        """
    
        color = False
        old_num = 0
        new_num = 0
            
        for line in diff_handle.readlines():
            
            if line.startswith("Index") or line.startswith("diff"):
                color = False
                old_num = 0
                new_num = 0
            elif line.startswith("@@"):
                print line
                splits = line.split()
                old_num = abs(int(splits[1].split(',')[0]))
                new_num = abs(int(splits[2].split(',')[0]))
            elif line.startswith('+'):
                line =  line[1:]
                outdata += "<p>"
                outdata += "<div class='linenum'>"
                outdata += "     %04d " % (new_num)
                outdata += "</div>"
                outdata += "<div class='addline'>"
                color = True
                new_num += 1
            elif line.startswith('-'):
                line =  line[1:]
                outdata += "<p>"
                outdata += "<div class='linenum'>"
                outdata += "%04d      " % (old_num)
                outdata += "</div>"
                outdata += "<div class='subline'>"
                color = True
                old_num += 1
            elif old_num == new_num:
                outdata += "<div class='linenum'>"
                outdata += "%04d      " % (new_num)
                outdata += "</div>"
                old_num += 1
                new_num += 1
            else:
                outdata += "<div class='linenum'>"
                outdata += "%04d %04d " % (old_num, new_num)
                outdata += "</div>"
                old_num += 1
                new_num += 1

            outdata += '<div class="diff">'
            outdata += "%s" % (
                    line.replace('<','&lt;').replace('>','&gt;')
            )
            outdata += '</div>'

            if color:
                outdata += "</p>"
                outdata += "</div>"
                color = False

        outdata += """
        </pre>
        </code>
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

