import urllib.parse

link = "/wiki/Cho%20colate"
link = urllib.parse.unquote(link).replace(" ", "_")
print(link)

