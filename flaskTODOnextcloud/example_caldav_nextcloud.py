from caldav import DAVClient
from datetime import datetime
import vobject

"""
example how to read all cards from all boards using caldav. independant from api    
"""

url = "http://<your server>/remote.php/dav"
username = "your user"
password = "<key for app from nextcloud>"


client = DAVClient(url, username=username, password=password)
principal = client.principal()
calendars = principal.calendars()

for calendar in calendars:
    print(f"Kalendarz: {calendar.name}")
    todos = calendar.todos()
    for todo in todos:
        vobj = todo.vobject_instance
        if hasattr(vobj, "vtodo"):
            summary = vobj.vtodo.summary.value
            due = getattr(vobj.vtodo, "due", None)
            due_val = due.value.isoformat() if due else "brak terminu"
            print(f"Zadanie: {summary} | Termin: {due_val}")
