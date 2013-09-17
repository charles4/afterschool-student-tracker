function convert_unix_to_local(unix_timestamp){
	// create a new javascript Date object based on the timestamp
	/// multiplied by 1000 so that the argument is in milliseconds, not seconds
	var date = new Date(unix_timestamp*1000);

	var year = date.getFullYear();
	/// getmonth returns 0-11
	var month = date.getMonth() + 1;
	var day = date.getDate();

	// hours part from the timestamp
	var hours = date.getHours();
	// minutes part from the timestamp
	var minutes = date.getMinutes();
	if (minutes < 10){
		minutes = "0"+minutes
	}
	// seconds part from the timestamp
	var seconds = date.getSeconds();


	var current_time = new Date().getTime();

	// 300000 is hopefully 5 minutes in milliseconds
	if (current_time - date.getTime() < 300000){
		var formattedTime = "<span class='recent_event'>" + month + '/' + day + '/' + year + "    <b>" + hours + ':' + minutes + '</b></span>';
	}else{
		// will display time in 10:30:23 format
		var formattedTime = month + '/' + day + '/' + year + "    <b>" + hours + ':' + minutes + '</b>';
	}
	
	return formattedTime
}

function update_event_list(sid){


	$.get("/event/update", { student_id: sid })
	.done(function(data){

		data = jQuery.parseJSON( data );

		/// update relevent student list
		$("#student"+sid+" tr.event").remove()

		var table = $("#student"+sid+" tr:last")
		for (var i in data){
			tmp = ""
			localstarttime = convert_unix_to_local(data[i].unix_time_stamp_start)
			localendtime = convert_unix_to_local(data[i].unix_time_stamp_end)

			if (data[i].title == "Absent"){
				tmp += "<tr class='event' eventid='" + data[i].id +"'><td>" + localstarttime + " marked <b>" + data[i].title + "</b> [ " + data[i].start_teacher + " ] </td></tr>"
			}else if(data[i].title == "Signout"){
				tmp += "<tr class='event' eventid='" + data[i].id +"'><td>" + localstarttime + " Signed out for the day by <b>" + data[i].guardian + "</b> [ " + data[i].end_teacher + " ] </td></tr>"
			}else if(data[i].title == "Restroom"){
				tmp += "<tr class='event' eventid='" + data[i].id +"'><td>" + localstarttime + " went to the " + data[i].title + " [ " + data[i].start_teacher + " ] </td></tr>"
				if (data[i].unix_time_stamp_end){
					tmp += "<tr class='event' eventid='" + data[i].id +"'><td>" + localendtime + " returned from the " + data[i].title + " [ " + data[i].end_teacher + " ] </td></tr>"
				}
			}else{
				tmp += "<tr class='event' eventid='" + data[i].id +"'><td>" + localstarttime + " checked <b>into</b> " + data[i].title + " [ " + data[i].start_teacher + " ] </td></tr>"
				if (data[i].unix_time_stamp_end){
					tmp += "<tr class='event' eventid='" + data[i].id +"'><td>" + localendtime + " checked <b>out</b> from " + data[i].title + " [ " + data[i].end_teacher + " ] </td></tr>"
				}
			}
			$(table).after(tmp)


		}
	});

}

function event_select_callback(ev){
	event_title = $(ev.data.param1).val()
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/signin", { title: event_title, student_id: sid })
	.done({ param1: sid }, update_event_list)

	$(ev.data.param1).val(ev.data.param2)
}

function signout_select_callback(ev){
	guardian = $(ev.data.param1).val()
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/signout", { title: "Signout", student_id: sid, guardian: guardian })
	.done({ param1: sid }, update_event_list)
}

function bathroom_click_callback(ev){
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/bathroom", { title: "Restroom", student_id: sid })
	.done({ param1: sid }, update_event_list)
}

function absent_click_callback(ev){
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/absent", { title: "Absent", student_id: sid })
	.done({ param1: sid }, update_event_list)
}

function signout_click_callback(ev){
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/signout", { title: "Signout", student_id: sid })
	.done({ param1: sid }, update_event_list)
}

$(document).ready(function(){

	// setup selectors
	$( ".event_selector" ).each(function( index ) {
		original_state = $(this).val()
		$(this).change({param1: this, param2: original_state}, event_select_callback);
	});

	$( ".signout_selector ").each(function ( index ){
		$(this).change({param1: this}, signout_select_callback);
	});

	// retrieve event info for each student
	$( ".event_selector" ).each(function( index ){
		var sid = $(this).attr('studentid')
		update_event_list(sid)
	});

	//set bathroom btn onclick
	$( ".bathroom_btn" ).each(function( index ){
		$(this).click({param1: this}, bathroom_click_callback);
	});

	// set absent btn onclick
	$( ".absent_btn" ).each(function( index ){
		$(this).click({param1: this}, absent_click_callback);
	});

	var intervalID = window.setInterval(function(){
		// retrieve event info for each student
		$( ".event_selector" ).each(function( index ){
			var sid = $(this).attr('studentid')
			update_event_list(sid)
		});
	}, 10000);

});