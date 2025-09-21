# backup_db.py
import os, zipfile, datetime, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.join(ROOT, "instance")
DB = os.path.join(INSTANCE, "database.db")
UPLOADS = os.path.join(INSTANCE, "uploads")
BACKUPS = os.path.join(ROOT, "backups")
os.makedirs(BACKUPS, exist_ok=True)

stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
out_zip = os.path.join(BACKUPS, f"backup-{stamp}.zip")

with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
    if os.path.exists(DB):
        z.write(DB, arcname="database.db")
    if os.path.isdir(UPLOADS):
        for root, _, files in os.walk(UPLOADS):
            for f in files:
                full_path = os.path.join(root, f)
                rel = os.path.relpath(full_path, INSTANCE)  # uploads/...
                z.write(full_path, arcname=rel)

print(f"✅ Backup written: {out_zip}")
