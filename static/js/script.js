setInterval(                               //Periodically 
  function()
  {
     $.getJSON(                            //Get some values from the server
        $SCRIPT_ROOT + '/get_values',      // At this URL
        {},                                // With no extra parameters
        function(data)                     // And when you get a response
        {
          $("#result").text(data.result);  // Write the results into the 
                                           // #result element
        });
  },
  500);                                    // And do it every 500ms
