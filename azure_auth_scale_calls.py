from azure_auth_scale import *

microsoft_groups_token = ""
microsoft_create_apps_token = ""
windows_consent_app_token = ""
redirect_urls = []

azure_automation = AzureAuthScaleAutomation(microsoft_groups_token, microsoft_create_apps_token, windows_consent_app_token, redirect_urls)


# In this example it creates 5 groups that are called from 26500 to 26504 group
# Make sure to read the documentation of the method.

# To use this you only need the **microsoft_groups_token**
azure_automation.create_group_scale_threading(26500, 5)


# Creates and configures an application in azure, so make sure to read the documentation of the function.
# In this example, the first parameters stands for the active directory id,
# the second is the index of the app that will start creating: 300
# and the last parameter is the number of apps to be created: scale_app_300, scale_app_301

# To use this you need both tokens **microsoft_create_apps_token** and **windows_consent_app_token**
azure_automation.create_azure_app_registrations_apis("", 300, 2)


# Assigns random groups to the users list, please read the function documentation before proceeding
# user_sample.csv and all_data_groups.csv has to have a format like:
#   <headers>
#   <data>
#   <one-empty-row>

#   If you have more than 5k of users, then please run this with a csv of 5k users, then wait at least 5 minutes, update the csv with other 6k users
#   and run it again and so on. If you have more than 10k users, then try to update the microsoft_groups_token after those 10k users run.

# To use this you only need the **microsoft_groups_token**
azure_automation.assign_groups_to_members_threading("user_sample.csv", "all_data_groups.csv")


# Modify the redirect urls of the apps
# In this case, will replace the redirect urls of the apps from the csv called object_id_test.csv
# Example:
#   You set the redirect_urls list with:                                               ["link_1", "link_2", "link_3"]
#   You have applications with redirect_urls like:                                     ["link_2", "link_3"]
#   When you execute the script the applications you selected will have the following: ["link_1", "link_2", "link_3"]

# To use this you only need the **microsoft_create_apps_token**
azure_automation.modify_redirect_urls_of_app_threading("azure_app_object_id.csv")


# Deletes the apps from the azure portal
# In this case, will delete all the apps from the csv called object_id_test.csv

# To use this you only need the **microsoft_create_apps_token**
azure_automation.delete_active_application_threading("objects_id_test.csv")