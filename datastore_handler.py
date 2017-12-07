#!/usr/bin/env python

#  Inspired by:  https://github.com/bbhlondon/app-engine-export
#  and:  http://gbayer.com/big-data/app-engine-datastore-how-to-efficiently-export-your-data/

from django.http import HttpResponse
from django.db import models

from google.appengine.api.files import records
from google.appengine.datastore import entity_pb
from google.appengine.api import datastore

from os import listdir
from os.path import isfile, join
from operator import itemgetter

import glob
from pydoc import locate

import logging

APP_NAME        = "dev~YOURAPPNAME"

FILE_PATH       = './production_datastore_backups/backups_20171203/20171203/'

MODEL_LOCATIONS = [
    'core.models.', 
    'django.contrib.auth.models.',
    'django.contrib.admin.models.',
    'django.contrib.contenttypes.models.',
    'django.contrib.sessions.models.',
    'cloudstorage.rest_api.',
    'google.appengine.ext.admin.',
]

MODEL_ALIASES   = {
    'auth_user'             : 'User',
    'core_userprofile'      : 'UserProfile',
    'django_content_type'   : 'ContentType',
    'django_session'        : 'Session',
    'django_admin_log'      : 'LogEntry',
}

def glob_output_files(path):
    backup_info_files   = []
    backup_output_files = []
    
    for f in listdir(path):
        if isfile(join(path,f)):    # exclude folders
            if len(f.split(".")) == 2:
                summary_file = f    # exclude summary file
            else:
                backup_info_files.append(f)
        else:
            # 'output-x' files are nested inside another directory with hashed name.
            # use glob to get to nested files
            # change '/*/*' depending on how deep your output-x files are nested
            backup_output_files = backup_output_files + glob.glob(join(path + f + "/*/*"))
            
    return backup_info_files, backup_output_files
            
            
def load_datastore_backup(request):
    
    backup_info_files, backup_output_files = glob_output_files(FILE_PATH)
    
    html = '<body>'
    
    if not request.method == 'POST':
        
        files       = groupFiles( FILE_PATH )
        model_names = [filename.split(".")[1] for filename in backup_info_files]

        html += '<h2>Import datastore backup files into local dev server via  &rarr;datastore_handler.py</h2> \
                <h3>&bull; Using file path: &nbsp; {} <br/><br /> \
                &bull; Click on the "Start Export" at the bottom to start the process. \
                Depending on the export size, this process can take a very long time.</h3>'.format( FILE_PATH )

        lst = '<ul>'

        for ename in files.keys():
            lst += '<a href="/export/{}"> \
                        <li>{} ({} files)</li> \
                    </a>'.format( ename, ename, len(files[ename]) )

        lst += '</ul>\n\n'

        html += lst

        html += '<h4>Model Names:</h4>{}<br /><br />'.format(model_names)
        html += '<h4>backup_info_files: </h4>{}<br /><br />'.format(backup_info_files)
        html += '<h4>backup_output_files: </h4>{}<br /><br />'.format(backup_output_files)
        
        # only allow one submit 
        html += '<script> \
                    function doSubmit() { \
                        var theButton = document.getElementById("submitButton"); \
                        var theForm = document.getElementById("theForm"); \
                        if (theButton.innerText == "Start Import") { \
                            theButton.innerText = "Processing..."; \
                            theForm.submit(); \
                        } \
                    } \
                </script> \
                <form id="theForm" action="" method="post"></form> \
                <center> \
                <button id="submitButton" style="padding:10px;text-align:center;" onclick="doSubmit();">Start Import</button> \
                </center>'
        
    else:   # POST
        
        html = '<h1>Import Finished!</h1> \
                <h3>Check below for errors:</h3>\
                <style>table, th, td {border:1px solid gray; border-collapse: collapse; text-align:center;}</style> \
                <table> \
                    <tr> \
                        <td><b>Output File</b></td> \
                        <td><b>Put() errors</b></td> \
                    </tr>' 

        # directly import (don't put double-underscores in paths!):
        for output_file_name in backup_output_files:
            model_class_name = output_file_name.split("__")[1].split("/")[0]

            # find the model classes dynamically, so don't have to manually import each:
            
            # might be an alias:
            if MODEL_ALIASES.has_key(model_class_name):
                model_class_name = MODEL_ALIASES[model_class_name]
        
            for location in MODEL_LOCATIONS:
                model_class = locate(location + model_class_name)
                if model_class:
                    break
                
            if not model_class:
                html += '<tr><td colspan="2" style="color:red;"><b>Can\'t find this model!  :  {}</b></td></tr>'.format(model_class_name)
            else:
                raw = open(output_file_name, 'rb')
                reader = records.RecordsReader(raw)
            
                put_failure_count = 0
                
                for record in reader:
                    entity_proto = entity_pb.EntityProto(contents=record)
                    entity_proto.key_.set_app( APP_NAME )
                    
                    try:
                        entity = datastore.Entity.FromPb(entity_proto, default_kind=model_class)
                        datastore.Put(entity)
                        
                        # the above works across all: ndb, db, django
                        # more specific, for ndb:
                        # entity = ndb.ModelAdapter(model_class).pb_to_entity(entity_proto)
                        # entity.put()
                        # for db:
                        # entity = db.model_from_protobuf(entity_proto)
                        # entity.put()
                    except  Exception as e:
                        put_failure_count += 1
                        logging.error("Error: {}\n Entity: {}".format(e, entity_proto.value_list() ))
                        
                html += '<tr><td style="text-align:left;">{}</td><td><b>{}</b></td></tr>'.format(
                                                            output_file_name.replace(FILE_PATH, ""), 
                                                            put_failure_count
                                                        )
                
        html += '</table><br /><br /><h1>fin!</h1>'
        
    html += "</body>"
    
    return HttpResponse(html)


def export_as_csv(request):
    
    backup_info_files, backup_output_files = glob_output_files(FILE_PATH)
    
    html = '<body>'
    
    if not request.method == 'POST':
        
        files       = groupFiles( FILE_PATH )
        model_names = [filename.split(".")[1] for filename in backup_info_files]

        html += '<h2>Export datastore backup file as CSV using  &rarr;views_datastore_handler.py</h2> \
                <h3>&bull; Using file path: &nbsp; {} <br/><br /> \
                &bull; Select a model, then click on the "Export as CSV" at the bottom to convert.</h3>'.format( FILE_PATH )

        html += '<form id="ModelNameForm" action="" method="post">'
        
        for model_name in model_names:
            html += '<input type="radio" name="modelChoice" value="{}" style="margin-left:16px;"/> {} <br />'.format(model_name, model_name)
            
        # only allow one submit every 2.5 seconds
        html += '<script> \
                    function doSubmit() { \
                        var theButton = document.getElementById("submitButton"); \
                        var theForm = document.getElementById("theForm"); \
                        if (theButton.innerText == "Export as CSV") { \
                            theButton.innerText = "Processing..."; \
                            setTimeout(function(){ document.getElementById("submitButton").innerHTML = "Export as CSV"; }, 2500); \
                            theForm.submit(); \
                        } \
                    } \
                </script> \
                <br /><br /> \
                <button id="submitButton" style="padding:10px;text-align:center;" onclick="doSubmit();">Export as CSV</button> \
                </form>'

        html += '<br /><br /><h3>For debugging, here are the files available:</h3>'
        html += '<h4>backup_info_files: </h4>{}<br /><br />'.format(backup_info_files)
        html += '<h4>backup_output_files: </h4>{}<br /><br />'.format(backup_output_files)
        
        
                
        html += '</body>'
        
        return HttpResponse(html)
                
    else:   # POST
    
        model_name = request.POST.get("modelChoice")
        if not model_name:
            return HttpResponse('You forgot to choose a model', content_type='text/html')
        
        separator = '\t'
        rows = []
        
        try:
            for output_file_name in backup_output_files:
                model_class_name = output_file_name.split("__")[1].split("/")[0]
                if model_class_name == model_name:
            
                    # might be an alias:
                    if MODEL_ALIASES.has_key(model_class_name):
                        model_class_name = MODEL_ALIASES[model_class_name]
        
                    for location in MODEL_LOCATIONS:
                        model_class = locate(location + model_class_name)
                        if model_class:
                            break
                    
                    raw = open(output_file_name, 'rb')
                    reader = records.RecordsReader(raw)
                
                    response = HttpResponse(content_type='text/csv')
                    response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(model_name)
                    writer = csv.writer(response)
            
                    for record in reader:
                        entity_proto = entity_pb.EntityProto(contents=record)
                        entity_proto.key_.set_app( APP_NAME )
                
                        entity = datastore.Entity.FromPb(entity_proto, default_kind=model_class)
                        
                        header = []
                        row = []
                        for k,v in entity.items():
                            header.append(k)
                            row.append(v)
                        rows.append(row)
                        
                    writer.writerow(header)
                    for row in rows:
                        writer.writerow(row)
                            
                    return response
            return HttpResponse('Model not found: {}'.format(model_name), content_type='text/html')
        except  Exception as e:
            return HttpResponse("Error: {}\n Entity: {}".format(e, entity_proto.value_list() ))
            
            header = []
            row = []
            for k,v in entity.items():
                header.append(k)
                row.append(v)
            rows.append(row)
            

def groupFiles(path):
    "processes the path and returns all data files grouped by export name"
    onlyfiles = [ f for f in listdir(path) if isfile(join(path,f)) ]
    files = {}
    for f in onlyfiles:
        if f.find('.') == -1:
            split = f.split('-')
            if split[0] not in files:
                files[split[0]] = []
            split.append(f)
            files[split[0]].append(split)
    return files

    

