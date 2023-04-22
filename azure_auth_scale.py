import logging
import concurrent.futures
import pandas as pd
import random
import time
import requests
import os

from datetime import datetime
from requests.structures import CaseInsensitiveDict


# Output the logs to the stdout
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__file__)


WAIT_TIME = 30
SLEEP_TIME_FOR_ASSIGN_GROUPS = 150
PORTAL_AZURE_LINK = "https://portal.azure.com/"
GROUPS_AZURE_LINK = "https://graph.microsoft.com/beta/groups"
ASSIGN_GROUPS_AZURE_LINK = r"https://graph.microsoft.com/beta/$batch"
APPS_AZURE_LINK  = "https://graph.microsoft.com/v1.0/myorganization/applications"
APP_AZURE_DELETE_PERMANENTLY_LINK = "https://graph.microsoft.com/v1.0/directory/deletedItems"
ADMIN_CONSENT_FOR_APP_URL = "https://graph.windows.net/myorganization/consentToApp?api-version=2.0"


def get_datetime_to_ISO_format(dt: datetime):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "Z"


def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))


class AzureAuthScaleAutomation:
    def __init__(self,
                microsoft_groups_token: str,
                microsoft_create_apps_token: str,
                windows_consent_app_token: str,
                redirect_urls: list):
        self.microsoft_groups_headers = CaseInsensitiveDict()
        self.microsoft_groups_headers["Accept"] = "application/json"
        self.microsoft_groups_headers["Content-Type"] = "application/json"
        self.microsoft_groups_headers["Authorization"] = microsoft_groups_token
        self.microsoft_create_apps_headers = CaseInsensitiveDict()
        self.microsoft_create_apps_headers["Accept"] = "application/json"
        self.microsoft_create_apps_headers["Content-Type"] = "application/json"
        self.microsoft_create_apps_headers["Authorization"] = microsoft_create_apps_token
        self.windows_consent_app_headers = CaseInsensitiveDict()
        self.windows_consent_app_headers["Accept"] = "application/json"
        self.windows_consent_app_headers["Content-Type"] = "application/json"
        self.windows_consent_app_headers["Authorization"] = windows_consent_app_token
        self.redirect_urls = redirect_urls
        self.groups_size = None
        self.groups_df = None


    def __create_group_scale(self, scale_group_index: int):
        """
        Creates an azure group

        This function simply creates a group in an azure directory

        Parameters
        ----------
        scale_group_index : int
            This is a just a number to add at the end of the group name
        """
        index_str = str(scale_group_index)

        json_body = {
            "displayName": f"scale_group{index_str}",
            "mailEnabled": True,
            "securityEnabled": True,
            "groupTypes": [
            "Unified"
            ],
            "description": f"scale_group{index_str}",
            "mailNickname": f"scale_group{index_str}",
            "visibility": "private"
        }
        requests.post(url=GROUPS_AZURE_LINK, headers=self.microsoft_groups_headers, json=json_body)


    def create_group_scale_threading(self, start_index: int, number_of_groups: int):
        """
        Creates multiple azure groups

        This function creates azure groups using multi-threading approach

        Parameters
        ----------
        start_index : int
            The sequential number that will be the suffix of the credential name
        number_of_groups : int
            The number of accounts that will be created
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.__create_group_scale, range(start_index, start_index + number_of_groups))


    def create_azure_app_registration(self, app_name: str):
        """
        Creates a web app in azure

        This function simply creates a web app in azure with a specific name which is requested as a parameter

        Parameters
        ----------
        app_name : str

        Returns
        -------
        Response
        """
        create_app_body = {
            "displayName": app_name,
            "spa": {
                "redirectUris": []
            },
            "publicClient": {
                "redirectUris": []
            },
            "web": {
                "redirectUris": []
            },
            "signInAudience": "AzureADMyOrg",
            "requiredResourceAccess": [
                {
                    "resourceAppId": "00000003-0000-0000-c000-000000000000",
                    "resourceAccess": [
                        {
                            "id": "e1fe6dd8-ba31-4d61-89e7-88639da4683d",
                            "type": "Scope"
                        }
                    ]
                }
            ]
        }
        return requests.post(APPS_AZURE_LINK, headers=self.microsoft_create_apps_headers, json=create_app_body)


    def __assign_groups_to_members(self, user_id):
        """
        Assigns 1 to 6 random groups

        This function is called from assign_groups_to_members_threading, because it uses a multi-threading
        approach to call this function. This function assigns randomly from 1 to 6 groups to this user.

        Parameters
        ----------
        user_id : str
            The id of the user
        """
        json_body = {
            "requests": []
        }

        num_of_groups = random.randint(1, 6)
        random_groups = random.sample(range(0, self.groups_size), num_of_groups)
        for group_index in random_groups:
            group_id = self.groups_df.iloc[group_index]
            tmp_request = {
                "id": f"member_{group_id}_{user_id}",
                "method": "POST",
                "url": f"/groups/{group_id}/members/$ref",
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": {
                    "@odata.id": f"https://graph.microsoft.com/beta/directoryObjects/{user_id}"
                }
            }
            json_body["requests"].append(tmp_request)
        requests.post(ASSIGN_GROUPS_AZURE_LINK, headers=self.microsoft_groups_headers, json=json_body)


    def assign_groups_to_members_threading(self, users_csv_path: str, groups_csv_path: str):
        """
        Assigns randomly assigns 1 to 6 groups to users in azure

        This function loads a csv with users info and groups info, then selects 1000 to 1000 users
        to call a function that assigns a user with groups. After that, it needs an sleep time because
        azure rejects many requests at the same, maybe it's something about DDOS protection. Be aware that the
        execution may be interrupted or something, that's because you selected too many users. If that's
        the case, then you should wait the program to end and watch manually who was the last users with
        groups assigned.

        Parameters
        ----------
        users_csv_path : str
            The path for the csv of the users you want to assign to groups
        groups_csv_path : str
            The path for the csv file of the groups you want to be assign
        """
        users_df = pd.read_csv(users_csv_path)
        groups_df = pd.read_csv(groups_csv_path)

        self.groups_df = groups_df["id"]
        users_df = users_df["id"]
        users_size = users_df.size
        self.groups_size = self.groups_df.size

        start_index = end_index = 0
        end_index = clamp(end_index+1000, 0, users_size-1)
        while start_index < users_size:
            tmp_users_df = users_df.loc[start_index:end_index]

            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(self.__assign_groups_to_members, tmp_users_df)

            logger.info(f"Execution finished from {start_index} to {end_index}, waiting to run 1000 more...")
            time.sleep(130)
            start_index = end_index+1
            end_index = clamp(end_index+1000, 0, users_size-1)
        logger.info(f"start index is: {start_index} and last index is: {end_index}")


    def grant_read_permissions(self, app_object_id: str):
        """
        Grants the basic permissions to an app

        This function grants Read permissions to User, Directory and Group to the app. This only receives
        the app_object_id of the app to work.

        Parameters
        ----------
        app_object_id : str
        """
        grant_read_permissions = {
            "requiredResourceAccess": [
                {
                    "resourceAppId": "00000003-0000-0000-c000-000000000000",
                    "resourceAccess": [
                        {
                            "id": "e1fe6dd8-ba31-4d61-89e7-88639da4683d",
                            "type": "Scope"
                        },
                        {
                            "id": "df021288-bdef-4463-88db-98f22de89214",
                            "type": "Role"
                        },
                        {
                            "id": "5b567255-7703-4780-807c-7be8301ae99b",
                            "type": "Role"
                        },
                        {
                            "id": "7ab1d382-f21e-4acd-a863-ba3e13f7da61",
                            "type": "Role"
                        }
                    ]
                }
            ]
        }
        requests.patch(f"{APPS_AZURE_LINK}/{app_object_id}",
                    headers=self.microsoft_create_apps_headers, json=grant_read_permissions)


    def consent_admin_permissions(self, app_client_id: str):
        """
        Consents the permissions of an app

        This function gives admin consent of all the permissions in the app. By default, the app
        has only Read permissions.

        Parameters
        ----------
        app_client_id: str
        """
        admin_consent_body = {
            "clientAppId": f"{app_client_id}",
            "onBehalfOfAll": True,
            "checkOnly": False,
            "tags": [],
            "constrainToRra": True,
            "dynamicPermissions": [
                {
                    "appIdentifier": "00000003-0000-0000-c000-000000000000",
                    "appRoles": [
                        "User.Read.All",
                        "Group.Read.All",
                        "Directory.Read.All"
                    ],
                    "scopes": [
                        "User.Read"
                    ]
                }
            ]
        }
        # Gives the consent to the app permissions as an admin
        requests.post(ADMIN_CONSENT_FOR_APP_URL, headers=self.windows_consent_app_headers,
                    json=admin_consent_body)


    def __create_secret_client(self, app_object_id: str, years_to_expire: int = 3):
        """
        Creates api permission credentials to the app

        This function generates an api key and client secret to access the app. This function has to be
        private because you need to catch the client secret that is only shown once.

        Parameters
        ----------
        app_object_id : str
        years_to_expire : int

        Output
        ------
        json
        """
        start_date_time = datetime.now()
        end_date_time = start_date_time.replace(year=start_date_time.year + years_to_expire)

        parsed_start_dt = get_datetime_to_ISO_format(start_date_time)
        parsed_end_dt = get_datetime_to_ISO_format(end_date_time)

        app_secret_client_body = {
            "passwordCredential": {
                "displayName": "test-description",
                "endDateTime": f"{parsed_end_dt}",
                "startDateTime": f"{parsed_start_dt}"
            }
        }

        return requests.post(f"{APPS_AZURE_LINK}/{app_object_id}/addPassword",
                                                headers=self.microsoft_create_apps_headers, json=app_secret_client_body)


    def modify_redirect_urls_of_app(self, app_object_id: str):
        """
        Updates the redirect_urls of a web app

        This function sends a patch request to modify the redirect urls of a specific web app. It is important to
        know that this functions fully updates the redirect urls, so make sure to initialize this class
        with all urls you want your app to have.

        Parameters
        ----------
        app_object_id : str

        """
        redirect_url_body = {
            "spa": {
                "redirectUris": []
            },
            "publicClient": {
                "redirectUris": []
            },
            "web": {
                "redirectUris": self.redirect_urls
            }
        }
        requests.patch(f"{APPS_AZURE_LINK}/{app_object_id}", headers=self.microsoft_create_apps_headers,
                    json=redirect_url_body)


    def modify_redirect_urls_of_app_threading(self, object_id_csv_path: str):
        """
        Modifies multiple redirect urls from a csv

        This function reads a csv containing the object ids of the azure apps, then executes
        the funcion modify_redirect_urls_of_app using multi-threading

        Parameters
        ----------
        object_id_csv_path : str
            The path of the parameter of the csv
        """
        df = pd.read_csv(object_id_csv_path)
        df = df['object_id']

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.modify_redirect_urls_of_app, df)


    def create_azure_app_registrations_apis(self, tenant_id: str, start: int, number_of_apps: int):
        """
        Registers, configures an azure app and returns a csv with API credentials

        This function calls several functions to fully configure an azure app. The first one is for the
        creation of the app, then another to grant User.Read.All, Directory.Read.All, Group.Read.All. Then,
        you it calls a function that works from another API to give admin consent the previous permissions
        of the app. Furthermore, creates an API key and saves the secret key. After that, adds the
        redirect urls in the app and at last, creates two csv with the credentials of the app.

        Parameters
        ----------
        start : int
            The start index for the app name that will be created
        number_of_apps: int
            The number of apps that will be created starting from the ``start`` index
        tenant_id: str
            The id of the azure active directory

        Returns
        -------
        None
            Doesn't return anything but creates two csv files

        Examples
        --------
        >>> create_azure_app_registrations_apis("89f8652e-c99e-43a0-ab1f-9273081e5aaa", 10, 5)
        >>> create_azure_app_registrations_apis("89f8652e-c99e-43a0-ab1f-9273081e5aaa", 5, 1)
        """

        tenant_id_list = list()
        client_id_list = list()
        client_secret_list = list()
        object_id_list = list()
        for app_index in range(start, start + number_of_apps):
            try:
                create_request_response = self.create_azure_app_registration(f"aruba-cloudauth-cred-scale-{app_index}")
                app_object_id = create_request_response.json()["id"]
                app_client_id = create_request_response.json()["appId"]

                self.grant_read_permissions(app_object_id)

                self.consent_admin_permissions(app_client_id)

                app_secret_client_request = self.__create_secret_client(app_object_id)

                secret_client_content = app_secret_client_request.json()
                client_secret = secret_client_content["secretText"]

                self.modify_redirect_urls_of_app(app_object_id)

                tenant_id_list.append(tenant_id)
                client_id_list.append(app_client_id)
                client_secret_list.append(client_secret)
                object_id_list.append(app_object_id)

            except Exception:
                logger.error(Exception("The script didn't finished as expected! Saving the results in the csv"))
                break

        df = pd.DataFrame({'tenant_id': tenant_id_list,
                            'client_id': client_id_list,
                            'client_secret': client_secret_list})
        does_file_exists = os.path.isfile(r"azure_app_credentials.csv")
        df.to_csv(r"azure_app_credentials.csv", index=False, header=(not does_file_exists), mode='a')

        df_object_id = pd.DataFrame({'object_id': object_id_list})
        does_file_exists_object_id = os.path.isfile(r"azure_app_object_id.csv")
        df_object_id.to_csv(r"azure_app_object_id.csv", index=False, header=(not does_file_exists_object_id), mode='a')


    def __delete_active_application(self, app_object_id: str):
        """
        Deletes permanently an application

        This function deletes temporary an active azure application, then deletes it permanently from that
        temporary directory.

        Parameters
        ----------
        app_object_id: str
            The object id of the application
        """

        requests.delete(f"{APPS_AZURE_LINK}/{app_object_id}", headers=self.microsoft_create_apps_headers)

        requests.delete(f"{APP_AZURE_DELETE_PERMANENTLY_LINK}/{app_object_id}", headers=self.microsoft_create_apps_headers)


    def delete_active_application_threading(self, object_id_csv_path):
        """
        Deletes multiple applications

        This function reads a csv with the object ids of the application that will be deleted, then deletes
        each of them twice; the first one is temporary and the second one is permanently.

        Parameters
        ----------
        object_id_csv_path: csv
            The csv containing one or more objects id for applications
        """

        df = pd.read_csv(object_id_csv_path)
        df = df['object_id']

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.__delete_active_application, df)

