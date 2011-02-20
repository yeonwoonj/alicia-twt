function load(no) {

 $.getJSON('/crawl/cont/' + no, function(data) {

  $('#loading').text(data.result);

  $('#main-cont').html(data.cont);

  var comments = data.comments;
  if (comments.length > 0) {
   for (var c in comments) {
    if (comments[c]) {
     $('<li><h3>'+comments[c].name+':</h3><p>'+comments[c].cont+'</p></li>').appendTo('#comments')
    }
   }
   $('#loading').removeClass('ui-corner-bottom');
   $('ul').listview('refresh');
  }
 })
 .error(function(e) {

  $('#loading').html('게시물 데이터를 읽지 못했습니다.');

 });

}