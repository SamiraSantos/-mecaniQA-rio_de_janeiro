import urllib.request, urllib.parse, json

def q(expr):
    u = "http://172.17.0.2:9090/api/v1/query?query=" + urllib.parse.quote(expr)
    try:
        req = urllib.request.urlopen(u)
        res = json.loads(req.read())["data"]["result"]
        return res[0]["value"][1] if res else "NO_DATA"
    except Exception as e:
        return str(e)

print("1. CPU %:", q("process_cpu_usage * 100"))
print("2. JVM Memory %:", q("(sum(jvm_memory_used_bytes{area='heap'}) / sum(jvm_memory_max_bytes{area='heap'})) * 100"))
print("3. Max Latency (s):", q("max(http_server_requests_seconds_max)"))
print("4. HTTP Errors %:", q("(sum(rate(http_server_requests_seconds_count{status=~'5..'}[2m])) / sum(rate(http_server_requests_seconds_count[2m]))) * 100"))

