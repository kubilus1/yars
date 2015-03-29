import os
import sys
import json
import shelve
import urllib
import urllib2
import urlparse
import cStringIO
import subprocess

import simplehttpd

PORT = 8080

RTCCMD = os.path.expanduser("~/jazz/scmtools/eclipse/lscm")
RTCURI="https://rtp-rtc6.tivlab.raleigh.ibm.com:9443/jazz/"

HTML_HEADER="""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<link rel="stylesheet" type="text/css" href="css/main.css">

<!--
<link rel="stylesheet" href="//code.jquery.com/ui/1.11.4/themes/smoothness/jquery-ui.css">
-->

<meta name="author" content="Matt Kubilus" />
<meta http-equiv="content-type" content="text/html; charset=utf-8"/>
<script type="text/javascript" src="/js/ajax_stuff.js"></script>
<script type="text/javascript" src="/js/yars.js"></script>
<script src="//code.jquery.com/jquery-1.10.2.js"></script>
<script src="//code.jquery.com/ui/1.11.4/jquery-ui.js"></script>

<script type="text/javascript">
//$(function() {
//    $( "#accordion" ).accordion({
//        collapsible: true
//    });
//});
$(document).click(function() {
//alert("Attempt to close");
// $( ".comment" ).css("visibility", "hidden");
});

$("body").click(function(){
//close popup
 $( ".comment" ).css("visibility", "hidden");
});

jQuery(document).ready(function() {
  jQuery(".changeset").hide();
  //toggle the componenet with class msg_body
  jQuery(".changeset_header").click(function()
  {
    jQuery(this).next(".changeset").slideToggle(500);
  });

  $('.file_id').each(function() {
    load_comments( this.id );
  });

});


</script>

<div id="dialog" title="Basic dialog">
<div id='%d_%d' class='comment'>    
<textarea rows="4" cols="50">
This is a comment
</textarea></div>
</div>

<div class="all_diffs">
"""

HTML_FOOTER="</div></div></body></html>"

DB="yars.db"

class MyRequestHandler(simplehttpd.AJAXRequestHandler):
    exposed_methods = ["do_review", "rtc_review"]

    def get_rtc_changeset(self, uuid):
        outdata = ""
        print "Getting diff for %s" % uuid
        command = [RTCCMD, 'diff', 'changeset', uuid, '-r', RTCURI]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=False)
        return p.communicate()[0]


    def do_add_comment(self, *args, **kwds):
        identifier = args[0][0];
        id_splits = identifier.split("_")
        if len(id_splits) != 3:
            print "Incorrect split len"
            return 

        file_id = id_splits[0]
        print "FILEID:", file_id
        shelf = shelve.open(DB)
        comment_list = json.loads(shelf.get(str(file_id),"[]"))
        shelf.close()
       
        comm_dict = {
            "fileid":file_id,
            "type":id_splits[1],
            "line":id_splits[2],
            "comment":args[0][1]
        }
        comment_list.append(comm_dict)

        shelf = shelve.open(DB)
        shelf[str(file_id)] = str(json.dumps(comment_list))
        shelf.close()
        
    def do_get_comments(self, *args, **kwds):
        file_id = args[0][0]
        print "FILEID: ", file_id
        shelf = shelve.open(DB)
        outdata = shelf.get(str(file_id),"[]")
        print "OUTDATA:", outdata
        shelf.close()
        return outdata

    def rtc_review(self, *args, **kwds):
        print args
        print kwds
        if args:
            arg_dict = args[0]

        outdata = ""

        workitem = arg_dict.get('workitem')
        shelf = shelve.open(DB)

        cache_data = shelf.get(str(workitem))
        
        if cache_data:
            changesets_raw = cache_data
        else:
            command = [RTCCMD, 'list', 'changesets', '-W', workitem, '-j', '-r', RTCURI]
            p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=False)
            changesets_raw = p.communicate()[0].strip()
            shelf[str(workitem)] = changesets_raw
       
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
        try:
            for uuid in uuids:
                print "Getting diff for %s" % uuid
            
                #cache_data = self.server.CACHE.get(uuid)
                cache_data = shelf.get(str(uuid))
                if cache_data:
                    print "Cache hit for: ", uuid
                    cs = cStringIO.StringIO(cache_data)
                    outdata += self.render_diff(cs, diff_id=uuid)
                    cs.close()
                else:
                    print "Cache miss for: ", uuid
                    diffdata = self.get_rtc_changeset(uuid)
                    
                    cs = cStringIO.StringIO(diffdata)
                    outdata += self.render_diff(cs, diff_id=uuid)
                    cs.close()
                    
                    shelf[str(uuid)] = diffdata
                    outdata += diffdata
        finally:
            shelf.close()

        print "Done with rtc_review" 
        
        return HTML_HEADER + outdata + HTML_FOOTER


    def render_diff(self, diff_handle, diff_name="Changeset", diff_id=None):
        outdata = """
        <div class="changeset_header" id="%s_header">
        <h3> %s </h3>
        </div>
        <div class="changeset" id="%s">
        <code>
        <pre>
        """ % (diff_id, diff_name, diff_id)
    
        color = False
        old_num = 0
        new_num = 0
        new_file = ""
        old_file = ""
            
        for line in diff_handle.readlines():
            if line.startswith("Index") or line.startswith("diff"):
                color = False
                old_num = 0
                new_num = 0
                new_file = ""
                old_file = ""
            elif line.startswith("+++ "):
                print line.split()
                new_file = line.split()[1].encode('base64')[:-3]
                outdata += "<div class='file_id' id='%s'></div>" % new_file
            elif line.startswith("--- "):
                print line.split()
                old_file = line.split()[1].encode('base64')[:-3]
                outdata += "<div class='file_id' id='%s'></div>" % old_file
            elif line.startswith("@@"):
                print line
                splits = line.split()
                old_num = abs(int(splits[1].split(',')[0]))
                new_num = abs(int(splits[2].split(',')[0]))
            elif line.startswith('+'):
                line =  line[1:]
                outdata += """<div id='comment_%s_add_%d' class='comment'>
<textarea id="text_%s_add_%d" rows="4" cols="20">
</textarea>
</div>""" % (new_file, new_num, new_file, new_num)
            
                outdata += "<div class='linenum' id='linenum_%s_add_%d'>" % (new_file, new_num) 
                outdata += '<a id="%s_add_%d" href="#" onclick="add_comment(\'%s_add_%d\');return false;">' % (new_file, new_num, new_file, new_num)
                outdata += "     %04d " % (new_num)
                outdata += "</a>"
                outdata += "</div>"
                outdata += "<p>"
                outdata += "<div class='addline'>"
                color = True
                new_num += 1
            elif line.startswith('-'):
                line =  line[1:]
                outdata += """<div id='comment_%s_sub_%d' class='comment'>
<form id="form_%s_sub_%d" method="post" action="javascript:do_comment()">    
<textarea rows="4" cols="20">
</textarea>
<input type="submit">
</form></div>""" % (diff_id, old_num, diff_id, old_num)
            
                outdata += "<div class='linenum'>"
                outdata += '<a id="sub_%d" href="#" onclick="add_comment(\'sub_%d\'); return false;">' % (old_num, old_num)
                outdata += "%04d      " % (old_num)
                outdata += "</a>"
                outdata += "</div>"
                outdata += "<p>"
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
        </div>
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

