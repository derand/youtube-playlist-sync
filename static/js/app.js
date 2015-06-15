$( document ).ready(function() {
  var tasks = new Array();
  var cache_playlists = {};

  // https://jqueryui.com/dialog/#modal-form
  var dialog, form,
    source_playlist_id_input,
    dest_playlist_id_input;

  function addTask() {
    source_playlist_id_input.removeClass( "ui-state-error" );

    var valid = true;
    if (source_playlist_id_input.val().length == 0) {
      source_playlist_id_input.addClass( "ui-state-error" );
      valid = false;
    }

    if (valid) {
      var prms = {
        'source_playlist': source_playlist_id_input.val(),
        'playlist_prefix': ''
      };
      if (dest_playlist_id_input.val().length > 0) {
        prms['dest_playlist'] = dest_playlist_id_input.val();
      }
      $.post('/tasks/add.json', prms,
          function (response, status) {
            var data = jQuery.parseJSON(response);
            if (data.code != 200) {
                console.log(data);
                alert(data.message);
                return ;
            }
            tasks = data.tasks;
            updateTasks();
        });
      dialog.dialog( "close" );
    }
    return valid;
  };

  function createThumbCell(class_name, img_url, pl_info) {
    var cell = $('<div/>').attr('class', class_name);
    cell.append($('<img/>').attr('src', img_url));
    var tmp = $('<div/>').attr('class', 'video-counter');
    if (pl_info && pl_info.hasOwnProperty('contentDetails')) {
      tmp.html(pl_info.contentDetails.itemCount);
    }
    cell.append(tmp);
    return cell;
  };
  function channelURL(pl_info) {
    // https://www.youtube.com/channel/UCshG1-oUuFknWjXp5U1P9xw
    if (pl_info && pl_info.hasOwnProperty('snippet')) {
      return 'https://www.youtube.com/channel/' + pl_info.snippet.channelId;
    }
    return '#';
  };
  function playlistURL(pl_info) {
    // https://www.youtube.com/playlist?list=PLRX8fwDLJ1qk3J7hWYTuAd4Klqd6rJIDg
    if (pl_info && pl_info.hasOwnProperty('snippet')) {
      return 'https://www.youtube.com/playlist?list=' + pl_info.id;
    }
    return '#';
  };
  function zeropad(n) { return ("0" + n).slice(-2); };
  function updatedToString(timestamp) {
    var date = new Date(timestamp * 1000),
        today = new Date();
    today.setHours(0);
    today.setMinutes(0);
    today.setSeconds(0);
    today.setMilliseconds(0);
    var diff = today.getTime() - date.getTime();
    if (date.getTime() > today.getTime()) {
        return ' at '+zeropad(date.getHours())+':'+zeropad(date.getMinutes());
    } else if (diff <= (24 * 60 * 60 * 1000)) {
        return 'Yesterday at '+zeropad(date.getHours())+':'+zeropad(date.getMinutes());
    }
    var months = new Array('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec');
    return zeropad(date.getDate())+" "+months[date.getMonth()]+' '+date.getFullYear()+' at '+zeropad(date.getHours())+':'+zeropad(date.getMinutes());
  }
  function createTitleCell(class_name, pl_info, task_info, addDeleteButtonId) {
    var cell = $('<div/>').attr('class', class_name);
    if (pl_info && pl_info.hasOwnProperty('snippet')) {
      // title
      var tmp = $('<div/>').attr('class', 'pl-title');
      tmp.append($('<a/>').attr('href', playlistURL(pl_info)).html(pl_info.snippet.title));
      cell.append(tmp);
      // description
      tmp = $('<div/>').attr('class', 'pl-description');
      tmp.html(pl_info.snippet.description);
      cell.append(tmp);
      // channel title
      tmp = $('<div/>').attr('class', 'pl-ch-title');
      tmp.append($('<a/>').attr('href', channelURL(pl_info)).html(pl_info.snippet.channelTitle));
      cell.append(tmp);
    } else {
      cell.append($('<div/>').attr('class', 'pl-title').append($('<a/>').attr('href', '#')));
      cell.append($('<div/>').attr('class', 'pl-description'));
      cell.append($('<div/>').attr('class', 'pl-ch-title').append($('<a/>').attr('href', '#')));
    }
    // delete button and last update time
    if (addDeleteButtonId) {
      cell.append($('<a/>').attr('href', '#').attr('class', 'delete-button').attr('id', addDeleteButtonId).css('visibility', 'hidden').html('Delete'));

      if (task_info) {
        cell.append($('<div/>').attr('class', 'pl-status').html('Last sync ' + updatedToString(task_info.updated)));
      }
    }
    return cell;
  };
  function updateTasks() {
    var tasks_table = $('#tasks_table');

    if (tasks.length == 0) {
        tasks_table.html('No tasks');
    } else {
      var playlist_ids = new Array();
      var row_str = ''; // delete
      var table_row, curr_cell;
      tasks_table.html('');
      $.each(tasks, function (i, item) {
          console.log(item);
          table_row = $('<div/>').attr('class', 'rTableRow').attr('id', item.id);
          if (cache_playlists.hasOwnProperty(item.source_playlist_id) && cache_playlists[item.source_playlist_id].hasOwnProperty('snippet')) {
            pl_info = cache_playlists[item.source_playlist_id];
            if (pl_info.snippet.hasOwnProperty('thumbnails') && pl_info.snippet.thumbnails.hasOwnProperty('default') && pl_info.snippet.thumbnails.default.hasOwnProperty('url')) {
              curr_cell = createThumbCell('rSourceThumbCell', pl_info.snippet.thumbnails.default.url, pl_info);
            } else {
              curr_cell = createThumbCell('rSourceThumbCell', '/img/pl_default_thumb.jpg', pl_info);
            }
            table_row.append(curr_cell);
            table_row.append(createTitleCell('rSourceTableCell', pl_info));
          } else {
            table_row.append(createThumbCell('rSourceThumbCell', '/img/pl_default_thumb.jpg'));
            table_row.append(createTitleCell('rSourceTableCell'));
            playlist_ids.push(item.source_playlist_id);
          }
          table_row.append($('<div/>').attr('class', 'rSplitCell'));

          if (item.dest_playlist_id) {
            if (cache_playlists.hasOwnProperty(item.dest_playlist_id) && cache_playlists[item.dest_playlist_id].hasOwnProperty('snippet')) {
              pl_info = cache_playlists[item.dest_playlist_id];
              if (pl_info.snippet.hasOwnProperty('thumbnails') && pl_info.snippet.thumbnails.hasOwnProperty('default') && pl_info.snippet.thumbnails.default.hasOwnProperty('url')) {
                curr_cell = createThumbCell('rDestThumbCell', pl_info.snippet.thumbnails.default.url, pl_info);
              } else {
                curr_cell = createThumbCell('rDestThumbCell', '/img/pl_default_thumb.jpg', pl_info);
              }
              table_row.append(curr_cell);
              table_row.append(createTitleCell('rDestTableCell', pl_info, item, 'task-delete-'+item.id));
            } else {
              table_row.append(createThumbCell('rDestThumbCell', '/img/pl_default_thumb.jpg'));
              table_row.append(createTitleCell('rDestTableCell', undefined, item, 'task-delete-'+item.id));
              playlist_ids.push(item.dest_playlist_id);
            }
          } else {
            table_row.append(createThumbCell('rDestThumbCell', '/img/pl_default_thumb.jpg'));
            table_row.append(createTitleCell('rDestTableCell', undefined, item, 'task-delete-'+item.id));
          }
          tasks_table.append(table_row);
      });

      if (playlist_ids.length > 0) {
        console.log('Playlists info request:', playlist_ids);
        $.ajax({
          type: "POST",
          url: '/playlists.json',
          contentType: "application/json; charset=utf-8",
          dataType: "json",
          data: JSON.stringify(playlist_ids),
          success: function (pls) {
              console.log(pls);
              if (pls.code != 200) {
                console.log(pls);
                alert(pls.message);
                return ;
              }
              var pl_info, row;
              $.each(tasks, function (i, t) {
                  row = $('#'+t.id);
                  if (!row) {
                    return; //this is equivalent of 'continue' for jQuery loop
                  }
                  pl_info = $.grep(pls.playlists, function (e) { return e.id == t.source_playlist_id; });
                  if (pl_info.length > 0) {
                    pl_info = pl_info[0];
                    if (pl_info.hasOwnProperty('snippet')) {
                      cache_playlists[pl_info.id] = pl_info;
                      row.find('.rSourceTableCell').find('.pl-title').find('a').html(pl_info.snippet.title);
                      row.find('.rSourceTableCell').find('.pl-title').find('a').attr('href', playlistURL(pl_info));
                      row.find('.rSourceTableCell').find('.pl-description').html(pl_info.snippet.description);
                      row.find('.rSourceTableCell').find('.pl-ch-title').find('a').html(pl_info.snippet.channelTitle);
                      row.find('.rSourceTableCell').find('.pl-ch-title').find('a').attr('href', channelURL(pl_info));
                      if (pl_info.snippet.hasOwnProperty('thumbnails') && pl_info.snippet.thumbnails.hasOwnProperty('default') && pl_info.snippet.thumbnails.default.hasOwnProperty('url')) {
                        row.find('.rSourceThumbCell').find('img').attr('src', pl_info.snippet.thumbnails.default.url);
                      }
                    }
                    if (pl_info.hasOwnProperty('contentDetails')) {
                      row.find('.rSourceThumbCell').find('.video-counter').html(pl_info.contentDetails.itemCount);
                    }
                  }
                  if (t.dest_playlist_id) {
                    pl_info = $.grep(pls.playlists, function (e) { return e.id == t.dest_playlist_id; });
                    if (pl_info.length > 0) {
                      pl_info = pl_info[0];
                      if (pl_info.hasOwnProperty('snippet')) {
                        cache_playlists[pl_info.id] = pl_info;
                        row.find('.rDestTableCell').find('.pl-title').find('a').html(pl_info.snippet.title);
                        row.find('.rDestTableCell').find('.pl-title').find('a').attr('href', playlistURL(pl_info));
                        row.find('.rDestTableCell').find('.pl-description').html(pl_info.snippet.description);
                        row.find('.rDestTableCell').find('.pl-ch-title').find('a').html(pl_info.snippet.channelTitle);
                        row.find('.rDestTableCell').find('.pl-ch-title').find('a').attr('href', channelURL(pl_info));
                        if (pl_info.snippet.hasOwnProperty('thumbnails') && pl_info.snippet.thumbnails.hasOwnProperty('default') && pl_info.snippet.thumbnails.default.hasOwnProperty('url')) {
                          row.find('.rDestThumbCell').find('img').attr('src', pl_info.snippet.thumbnails.default.url);
                        }
                      }
                      if (pl_info.hasOwnProperty('contentDetails')) {
                        row.find('.rDestThumbCell').find('.video-counter').html(pl_info.contentDetails.itemCount);
                      }
                    }
                  }
              });
            }
        });
      }
    }

    // bind events
    $.each(tasks, function (i, item) {
      var timer1 = setInterval(function() {
        var row = tasks_table.find('#'+item.id);
        if (row.length) {
          row
            .mouseenter(function () {
              $(this).find('#task-delete-'+item.id).css('visibility', 'visible')
                .click(function() {
                  var task_id = $(this).attr('id').slice('task-delete-'.length),
                      prms = { 'task_id': task_id };
                  console.log('Delete task:', $(this).attr('id'));
                  $.post('/tasks/delete.json', prms,
                      function (response, status) {
                        var data = jQuery.parseJSON(response);
                        if (data.code != 200) {
                            console.log(data);
                            alert(data.message);
                            return ;
                        }
                        tasks = data.tasks;
                        updateTasks();
                    });
                });
            })
            .mouseleave(function() {
              $(this).find('#task-delete-'+item.id).css('visibility', 'hidden').unbind( "click" );
            });
          clearInterval(timer1);
        }
      });
    });
  };

  dialog = $("#dialog-form").dialog({
      autoOpen: false,
      height: 225,
      width: 330,
      modal: true,
      buttons: {
        "Add task": addTask,
        Cancel: function() {
          dialog.dialog( "close" );
        }
      },
      close: function() {
        form[0].reset();
        source_playlist_id_input.removeClass( "ui-state-error" );
      }
    });
  form = dialog.find( "form" ).on( "submit", function( event ) {
      event.preventDefault();
      addTask();
    });
  source_playlist_id_input = form.find('#source_playlist_id');
  dest_playlist_id_input = form.find('#dest_playlist_id');

  $('#create-task').click(function () {
    dialog.dialog( "open" );
  });

  $.ajax({
    url: "/tasks/list.json",
    dataType: "json",
    success: function(data) {
      if (data.code != 200) {
        console.log(data);
        alert(data.message);
        return ;
      }

      tasks = data.tasks;
      updateTasks();
    }
  });
});