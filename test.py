import requests
import json
import pandas as pd


app_id = 'c2b23466-72d6-4a1b-9f78-3200e6c808b5'  # Application Id - on the azure app-updated overview page
client_secret = 'ZZaZ7z_~0U348-r~Yz9UslfQK.Dmv4Kzu5'  # Use the redirect URL to create a token url
token_url = 'https://login.microsoftonline.com/84cba236-0ee0-4481-bf46-8016d81056fa/oauth2/token'
token_data = {
    'grant_type': 'password',
    'client_id': app_id,
    'client_secret': client_secret,
    'resource': 'https://graph.microsoft.com',
    'scope': 'https://graph.microsoft.com',
    'username': 'leonard.muriithi@wiocc.net',  # Account with no 2MFA
    'password': 'Tintagel@77#',
}
token_r = requests.post(token_url, data=token_data)
token = token_r.json().get('access_token')

users_url = 'https://graph.microsoft.com/v1.0/users?$top=500'

headers = {
    'Authorization': 'Bearer{}'.format(token)
}

userId, displayName, mailAddress, plans_data, planId, PlanGrpOwnerId, PlanTitle, PlanCreatedBy, bucketId, bucketName, bucketPlanId, taskId, taskPlanId, taskBucketId, taskName, taskPercentComplete, taskStartDateTime, taskDueDateTime, taskCompleteDateTime, taskIdAssignment, taskUserIdAssignment = [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []

user_response_data = json.loads(requests.get(users_url, headers=headers).text)
# user_response_data['@odata.nextLink']#initial user data
# get all users
for user in user_response_data['value']:
    userId.append(user['id'])
    displayName.append(user['displayName'])
    mailAddress.append(user['userPrincipalName'])

    users_dict = {
        'userId': userId, 'displayName': displayName, 'mailAddress': mailAddress
    }

    users_df = pd.DataFrame(data=users_dict)  # additional user query for paging
    while '@odata.nextLink' in user_response_data:
        user_response_data = json.loads(requests.get(users_url, headers=headers).text)
        if '@odata.nextLink' in user_response_data:
            users_url = user_response_data['@odata.nextLink']

            for user in user_response_data['value']:
                userId.append(user['id'])
                displayName.append(user['displayName'])
                mailAddress.append(user['userPrincipalName'])

                users_dict = {
                    'userId': userId,
                    'displayName': displayName,
                    'mailAddress': mailAddress
                }
                users_df = pd.DataFrame(data=users_dict)
                users_df.head()
