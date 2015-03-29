InstallFunction(server, 'do_add_comment');
InstallFunction(server, 'do_get_comments');

$(document).ready(function() {
    alert("Ready!");
});

$(".linenum").each(function() {
    alert("Function");
})

function add_comment(linenum) {
  // Hide all other comment boxes 
  $( ".comment" ).css("visibility", "hidden");

  // Open current comment box
  $( "#comment_" + linenum ).css("visibility", "visible");

  // If it changes....
  $('#comment_' + linenum).on('change',function(){
    // Get the comment
    var acomment = $( "#text_" + linenum).val().trim();
    if(acomment != "") {
        // Comment not blank so change color for indication
        $( "#" + linenum ).css("background-color", "#8888FF");
    } else {
        $( "#" + linenum ).css("background-color", "");
    }
    //alert("change " + linenum + " :"+ acomment);
    // Tell the server
    server.do_add_comment(linenum, acomment);
    // Re-hide the comment box
    $( ".comment" ).css("visibility", "hidden");
  });
}

function do_comment() {
    alert("Comment");
}

function do_changeset() {
    var myid = event.target.id;
    //myid.innerHTML = "FOO BAR BAZ";
    alert("ID: " + myid)
}

function load_comments(file_id) {
    server.do_get_comments(file_id, onCommentResponse);
}

function onCommentResponse(response) {
    var comment_list = jQuery.parseJSON(response);
    var arrayLength = comment_list.length;
    for (var i = 0; i < arrayLength; i++) {
        var obj = comment_list[i];
        var linenum = obj.fileid + "_" + obj.type + "_" + obj.line;
        $("#text_" + linenum).val(obj.comment); 
        if(obj.comment != "") {
            // Comment not blank so change color for indication
            $( "#" + linenum ).css("background-color", "#8888FF");
        } else {
            $( "#" + linenum ).css("background-color", "");
        }
    } 
}
