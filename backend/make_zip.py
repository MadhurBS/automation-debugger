import zipfile, io, os, json
buf = io.BytesIO()
proj = {"name":"TestProject","projectVersion":"1.0.0","main":"Main.xaml","dependencies":{"UiPath.System.Activities":"22.4.2"}}
xaml = '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"><Sequence DisplayName="Main"></Sequence></Activity>'
with zipfile.ZipFile(buf, "w") as z:
    z.writestr("project.json", json.dumps(proj))
    z.writestr("Main.xaml", xaml)
with open("test_upload.zip","wb") as f:
    f.write(buf.getvalue())
print("OK", os.path.getsize("test_upload.zip"))
