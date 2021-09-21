from flask_dance.contrib.azure import make_azure_blueprint

auth = make_azure_blueprint(
    client_id="c2b23466-72d6-4a1b-9f78-3200e6c808b5",
    client_secret="ZZaZ7z_~0U348-r~Yz9UslfQK.Dmv4Kzu5",
    tenant="84cba236-0ee0-4481-bf46-8016d81056fa",
    scope=["openid", "email", "profile", "User.Read", "User.Read.All", "User.ReadBasic.All", "User.Export.All",
           "Mail.Send", "Mail.Send.Shared", "Directory.Read.All", "Directory.AccessAsUser.All",
           "Directory.ReadWrite.All", "User.ReadWrite.All"],
)


from . import routes