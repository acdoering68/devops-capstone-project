"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def help_create_account(self):
        account = self._create_accounts(1)[0]
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        return (account, response)

    def test_create_account(self):
        """It should Create a new Account"""
        account, response = self.help_create_account()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_list_accounts(self):
        """ Return a list of accounts """
        # first insert one account, so we know at least one list element
        account, response = self.help_create_account()
        response = self.client.get(
            BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        account_list_dict = response.text
        listoutputf = open("listoutput.txt", "w")
        print(type(account_list_dict), file=listoutputf)
        print(account_list_dict, file=listoutputf)
        listoutputf.close()

    def _check_account(self, refaccount, response):
        resaccount = response.get_json()
        self.assertEqual(refaccount.name, resaccount["name"])
        self.assertEqual(refaccount.address, resaccount["address"])
        self.assertEqual(refaccount.email, resaccount["email"])
        self.assertEqual(refaccount.phone_number, resaccount["phone_number"])

    def test_get_account(self):
        """Retrieve one particular account"""
        # first insert one account, so we know at least one list element
        account, response = self.help_create_account()
        response = self.client.get(
            BASE_URL+"/"+str(account.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self._check_account(account, response)

    def test_update_account(self):
        """ Update an account """
        account, response = self.help_create_account()
        account2 = self._create_accounts(1)[0]
        account.phone_number = account2.phone_number
        response = self.client.put(
            BASE_URL+"/"+str(account.id),
            json=account.serialize(),
            content_type="application/json"
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # new read the updated account to check that it got updated
        response = self.client.get(
            BASE_URL+"/"+str(account.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self._check_account(account, response)

    def test_delete_account(self):
        """ Delete an account """
        account, response = self.help_create_account()
        response = self.client.delete(
            BASE_URL+"/"+str(account.id)
            )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(
            BASE_URL+"/"+str(account.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_environment_overwrite(self):
        """It should get the unsafe header"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        for key, value in headers.items():
            self.assertEqual(response.headers.get(key), value)
