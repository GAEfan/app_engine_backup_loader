# app_engine_backup_loader
Fast &amp; easy way to load GAE's datastore backup files into local development server

Assumes you have already backed up your production datastore.  Here are the steps if needed:

1) Go to: https://ah-builtin-python-bundle-dot-YOURAPPNAME.appspot.com/_ah/datastore_admin?app_id=s~YOURAPPNAME
2) Select the entities to back up
3) Hit "Backup Entities".  Store to bucket (e.g.: my-backups/20171203) (Suggest a nearline bucket for cheap storage)
4) To download the backups, cd to the directory you want: 

$ cd /some/directory/I/like/

5) Then run  

$ gsutil -m cp -r gs://my-backups/20171203/ ./backups_20171203/ <== create this folder first (cp copies the data)

or:

$ gsutil  -m rsync -r gs://my-backups/20171203/ ./backups_20171203/ <== create this folder first (rsync syncs the 2 folders)

6) Move this local directory to a directory in your app, at same level as app.yaml

e.g.: /production_datastore_backups/

{Before you move to the next step, you may want to back up or rename the existing local datastore file.  With the old upload methods, the backup entities would be uploaded as duplicates, doubling the entities.  This new method doesn't seem to do that, but why bother with possible data errors?  To get a fresh local datastore, start with a blank one, then upload the new files. 1) Stop your local app instance. 2) Locate the local db file.  On OSX it is a file called "dev_appserver.datastore". 3) Rename or delete this. 4) Restart local dev server.}

7) To upload to dev server, navigate to:

http://localhost:8000/load_datastore_backup

and click the button at the bottom of the page, if all the files look correct.

(Of course, you need a url handler in your app to handle this url)

This was written inside a Django app, but writes directly to HTML without any template, for simplicity.  You can easily adapt to wsgi, for example.  One of the issues with Django is that datastore models have aliased names (User -> auth_user).  This handles those.  Also, this uses a method that can write the entities regardless of their model type (ndb, db, django, etc.)

In testing, this is much faster and less error-prone (and less expensive!) than the old `bulkloader.py` or `appcfg.py upload_data` methods.


EXPORT AS CSV:

export_as_csv() lets you quickly export your datastore backup files in csv format.  Wire a url handler to that function.  e.g:

http://localhost:8000/export_as_csv
