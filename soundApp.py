from flask import Flask, request
import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision


bucket = "sound_off"
measurement = "sound"
token = os.environ.get("INFLUXDB_TOKEN")
org = "salgia"
url = "http://localhost:8086"
bucket="sound_off"
measurement = "sound"
src = "src"
deviceName = "arthsiMac"
dbA = "dbA"
field = "dba"
client = InfluxDBClient(url=url, token=token, org=org)
influxDb = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

soundApp = Flask(__name__, static_folder='html')

@soundApp.route('/')
def homepage():
    return soundApp.send_static_file("soundHome.html")

@soundApp.route("/median")
def median(timeRange, source):
    timeRange = request.args.get('timeRange')
    source = request.args.get('source')
    query = """from(bucket: "sound_off")
        |> range(start: """ + timeRange + \
        """)|> filter(fn: (r) => r["_measurement"] == "sound")
        |> aggregateWindow(every: 15s, fn: mean, createEmpty: true)
        |> yield(name: "median")"""

#        |> filter(fn: (r) => r["src"] == "arthsiMac")

    query_api = client.query_api()
    tables = query_api.query(query, org="salgia")
    return print(tables)

@soundApp.errorhandler(404)
def not_found(e):
    return "Sorry, page not found"





if __name__ == "__main__":
    soundApp.run(debug=True)