import os


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


class Config(object):
    SECRET_KEY = 'kjhfgdhjkbd78435n4fsdgrt756ytru67867yhrt3454uyoihy0943u34j9r8y34908'

    SQLALCHEMY_DATABASE_URI = 'mssql+pymssql://sa:admin123@localhost/test'
    # Password
    # pcZkkB2HtjUDvq

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CLIENT_ID = "c2b23466-72d6-4a1b-9f78-3200e6c808b5"

    CLIENT_SECRET = "ZZaZ7z_~0U348-r~Yz9UslfQK.Dmv4Kzu5"

    TENANT_ID = '84cba236-0ee0-4481-bf46-8016d81056fa'

    AUTHORITY = "https://login.microsoftonline.com/84cba236-0ee0-4481-bf46-8016d81056fa"

    REDIRECT_PATH = "/getAToken"

    ENDPOINT = 'https://graph.microsoft.com/v1.0/users'

    SCOPE = ["User.ReadBasic.All"]

    SESSION_TYPE = "filesystem"

    APP_URL = 'http://localhost:5000'

    REQUIRE_AUTHENTICATION = str2bool('true')  # Obviously, should be true in prod
    HTTPS_SCHEME = 'https' if APP_URL.startswith('https') else 'http'
