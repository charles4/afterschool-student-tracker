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

function update_event_list(event_data){

		/// event data is a list of events
		data = event_data
		if (data.length > 0){
			sid = data[0].student_id

			/// clear existing tr's for the student
			$("#student"+sid+" tr.event").remove()

			/// add new event data
			var table = $("#student"+sid+" tr:last")
			for (var i in data){
				time = convert_unix_to_local(data[i].unix_time_stamp)
				title = data[i].title
				type = ""
				author = data[i].author
				ip = data[i].ip_address
				if (data[i].type == "start" || data[i].type == "ASstart"){
					type = "Signed into"
				}else{
					type = "Signed out from"
				}
				tmp = "<tr class='event'><td>" + time + " : " + type + " " + title + " by " + author + "</td></tr>"
				$(table).append(tmp)

			}
		}
}

function update_all_events(sids){

	$.get("/event/update/all")
	.done(function( data ){
		 data = jQuery.parseJSON( data );

		 for(var index=0; index<data.length; index++){

		 	// data[i] is a list of events for a particular student
		 	update_event_list(data[index])

		 }
	});

}

function update_counts(){
	$.get("/status")
	.done(function(data){
		 data = jQuery.parseJSON( data );

		 $('#count_general').html(data.count_general);
		 $('#count_afterschool').html(data.count_afterschool);
	});
}

function event_select_callback(ev){
	event_title = $(ev.data.param1).val()
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/signin", { title: event_title, student_id: sid })
	.done(update_all_events)

	$(ev.data.param1).val(ev.data.param2)
}

function signout_select_callback(ev){
	guardian = $(ev.data.param1).val()
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/afterschoolsignout", { title: "Signout", student_id: sid, guardian: guardian })
	.done(update_all_events)
}

function bathroom_click_callback(ev){
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/bathroom", { title: "Restroom", student_id: sid })
	.done(update_all_events)
}

function absent_click_callback(ev){
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/absent", { title: "Absent", student_id: sid })
	.done(update_all_events)
}

function signout_btn_callback(ev){
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/signout", { title: "Signout", student_id: sid })
	.done(update_all_events)
}

function signout_click_callback(ev){
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/signout", { title: "Signout", student_id: sid })
	.done(update_all_events)
}

function afterschool_click_callback(ev){
	sid = $(ev.data.param1).attr("studentid")

	$.post("/event/afterschool", { title: "Afterschool", student_id: sid })
	.done(update_all_events)
}

$(document).ready(function(){

	// setup selectors
	$( ".event_selector" ).each(function( index ) {
		original_state = $(this).val()
		$(this).change({param1: this, param2: original_state}, event_select_callback);
	});

	$( ".signout_selector").each(function ( index ){
		$(this).change({param1: this}, signout_select_callback);
	});

	$(".signout_btn").each(function (index){
		$(this).click({param1: this}, signout_btn_callback);
	});

	// retrieve event info for each student
	update_all_events();

	//setup initial counts
	update_counts();

	//set bathroom btn onclick
	$( ".bathroom_btn" ).each(function( index ){
		$(this).click({param1: this}, bathroom_click_callback);
	});

	// set absent btn onclick
	$( ".absent_btn" ).each(function( index ){
		$(this).click({param1: this}, absent_click_callback);
	});

	$( ".afterschool_btn" ).each(function( index ){
		$(this).click({param1: this}, afterschool_click_callback);
	});

	var intervalID = window.setInterval(function(){
		// retrieve event info for each student
		var sids = []
		$( ".event_selector" ).each(function( index ){
			var sid = $(this).attr('studentid')
			sids.push(sid)
		});

		update_all_events(sids);

		update_counts();

	}, 10000);

});