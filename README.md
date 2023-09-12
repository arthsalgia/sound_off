# sound_off
This is a python application designed to run on a Raspberry Pi (works on computers as well), to constantly capture ambient sound levels, convert to dbA and store the data in a time series data base influxdb. 
Coded a Flask-based backend service that exposed REST APIs to compute and respond with Median, Min, Max, etc sound readings for a given time range.
Built a react application to call these REST APIs and graphically display sound levels as gauges and graphs using the giraffe library to the user
