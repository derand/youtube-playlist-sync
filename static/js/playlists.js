$( document ).ready(function() {
  $.ajax({
    url: "/playlists.json",
    dataType: "json",
    success: function( data ) {
        var trHTML = '';
        $.each(data.playlists, function (i, item) {
            trHTML += '<div class="rTableRow"><div class="rThumbCell"><img src="' + item.snippet.thumbnails.default.url + '"></div><div class="rTableCell">' + item.snippet.title + '<br><small>' + item.snippet.description + '</small></div></div>';
        });
        $('#playlists_table').append(trHTML);
    }
  });
});