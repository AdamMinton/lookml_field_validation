import os
import json
import looker_sdk
from looker_sdk import models
from mdutils.mdutils import MdUtils
import argparse
import sys

def cli():
  parser = argparse.ArgumentParser()
  parser.add_argument('--branch', '-b', type=str, required=True, help='Branch to run LookML tests on')
  parser.add_argument('--location', '-loc', type=str, required=False, default=os.path.split(__file__)[0], help='Output Location of Result and Validation File')
  parser.add_argument('--config_file', '-cf', type=str, required=False, default="looker.ini", help='Configuration file for Looker')
  parser.add_argument('--section', '-sec', type=str, required=False, default="looker", help='If multiple sections in config_file, specify which instance')
  parser.add_argument('--validation_file', '-vf', type=str, required=True, help='Validation file contains test definitions')
  args = parser.parse_args()
  parser.set_defaults(func=lookml_validation_main(args))

def initiate_looker_sdk(config_file,section):
  """Will initiate looker sdk either based on environemtn variables if specified
  or will take the config file and section from the args
  """
  if "LOOKERSDK_CLIENT_ID" and "LOOKERSDK_CLIENT_SECRET" and "LOOKERSDK_BASE_URL" in os.environ:
    sdk = looker_sdk.init40()
  else:
    sdk = looker_sdk.init40(config_file=config_file,section=section)
  return(sdk)

def initiate_dev_mode(sdk, branch_name, lookml_project):
  """Swaps the session of the API to dev mode for a specific branch
  """
  sdk.session()
  sdk.update_session(body = models.WriteApiSession(workspace_id ='dev'))
  branch = models.WriteGitBranch(name=branch_name)
  sdk.update_git_branch(project_id=lookml_project, body=branch)

def find_check_dimension(field_name,lookml_dimensions):
  """Resolves only the fields that should be included
  based on how the validation string is composed. ALL_FIELDS* 
  will include all dimensions and then - can be used to remove specific
  fields
  """
  field_found = False
  for dimension in lookml_dimensions:
      if dimension.name == field_name:
        return(dimension)
  if field_found == False:
    raise AssertionError("Could not find field")

def validation_dimensions(validation,lookml_dimensions):
  """Resolves only the fields that should be included
  based on how the validation string is composed. ALL_FIELDS* 
  will include all dimensions and then - can be used to remove specific
  fields
  """
  validation = validation.split(",")
  validation_fields = []

  if "ALL_FIELDS*" in validation:
    validation_fields = lookml_dimensions
  
  for field in validation:
    if field.startswith('-'):
      field_name = field[1:]
    else:
      field_name = field
    for dimension in lookml_dimensions:
      if type(dimension).__name__ == 'LookmlModelExploreField' and dimension.name == field_name:
        if field.startswith('-'): #INFO: Remove fields that start with -
          validation_fields.remove(dimension)
        else:
          validation_fields.append(dimension)

    if validation_fields == []:
      raise AssertionError("No validation fields specified")
    
  return(validation_fields)

def add_level(test_results):
  """Adds result icon if failed or passed
  """
  errors = 0
  passes = 0
  for row in test_results:
    if row['result'] == 'Failed':
      row['level'] = '⛔'
      errors += 1
    else: 
      row['level'] = '✅'
      passes += 1
    
  summary = f"{errors} ⛔ | {passes} ✅"
  return(test_results,summary)

def output_markdown(target_directory,column_headers,results,summary):
  """Creates a markdown page containing the validation results 
  """
  mdFile = MdUtils(file_name=os.path.join(target_directory,'lookml_validation_results'),title='LookML Validation Results: '+ summary)

  number_of_columns = len(column_headers)
  number_of_rows = 0
  for row in results:
      number_of_rows +=1
      column_headers.extend(row.values())
  
  mdFile.new_line()
  mdFile.new_table(columns=number_of_columns, rows=number_of_rows+1, text=column_headers)
  mdFile.create_md_file()

def lookml_validation_main(args):

  #Args
  config_file = args.config_file
  section = args.section
  validation = args.validation_file
  location = args.location
  branch = args.branch
  
  validation_file_location = os.path.join(location,validation)
  sdk = initiate_looker_sdk(config_file=config_file,section=section)
  
  test_result_fields = ["Test Name","Result","Error Message","Level"]
  test_results = []

  #INFO: Load Validation Test in Dictionary Variable
  validation_tests = json.load(open(validation_file_location, "r"))

  for validation_test in validation_tests:
    #INFO: Enter dev mode for a specific branch
    dev_mode = initiate_dev_mode(sdk = sdk, branch_name=branch,lookml_project=validation_test['project'])
    
    #INFO: Pull LookML Mode/Explore Definition for dimensions
    lookml_model_explore = sdk.lookml_model_explore(lookml_model_name=validation_test['model'],explore_name=validation_test['explore'])
  
    #INFO: Checks are the field and parameter to check for specific short name fields mentioned
    for check in validation_test['checks']:
      try:
        check_dimension = find_check_dimension(check['field'],lookml_dimensions=lookml_model_explore.fields.dimensions)
      except AssertionError as err:
        print(f"Unexpected {err=}, {type(err)=}")
        test_results.append({"test_name":validation_test['test_name'],"result":"Failed", "error_message": err})
        continue
      
      try:
        validation_fields = validation_dimensions(validation_test['validation'],lookml_model_explore.fields.dimensions)
      except AssertionError as err:
        print(f"Unexpected {err=}, {type(err)=}")
        test_results.append({"test_name":validation_test['test_name'],"result":"Failed", "error_message": err})
        continue
      
      missing_fields = []
      found_fields = []

      for dimension in validation_fields:
        short_name = dimension.name.split('.')[1]
        if short_name in check_dimension[check['parameter']]:
          found_fields.append(dimension)
        else:
          missing_fields.append(dimension)      

      if len(missing_fields) > 0: 
        missing_fields_join = []
        for field in missing_fields:
          missing_fields_join.append(field.name)
        missing_fields_join = ' '.join(missing_fields_join)
        test_results.append({"test_name":validation_test['test_name'],"result":"Failed", "error_message": "Missing Fields: " + missing_fields_join})
      else:
        test_results.append({"test_name":validation_test['test_name'],"result":"Passed", "error_message": ""})
  
      
  test_results, summary = add_level(test_results)

  markdown = output_markdown(location,test_result_fields,test_results, summary)

  if len(missing_fields) > 0:
    sys.exit(3)
  else:
    sys.exit()

cli()