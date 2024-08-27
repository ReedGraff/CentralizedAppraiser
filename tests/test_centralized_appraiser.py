# python -m unittest discover -s tests
import unittest
import sys
import os

# Run the tests from the src directory to support the relative imports within the module
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
sys.path.insert(0, os.getcwd())

import CentralizedAppraiser
from CentralizedAppraiser import GoogleClient, RegridClient


class TestCentralizedAppraiser(unittest.TestCase):

    def setUp(self):
        creds_path = os.path.join(os.path.dirname(__file__), 'creds.txt')
        with open(creds_path, "r") as f:
            googleApiKey = f.readline().strip()
            regridApiKey = f.readline().strip()

        # Initialize clients with API keys from creds.txt
        self.googleClient = GoogleClient(googleApiKey)
        self.regridClient = RegridClient(regridApiKey)

    def testGoogleClientInitialization(self):
        self.assertIsInstance(self.googleClient, GoogleClient)

    def testRegridClientInitialization(self):
        self.assertIsInstance(self.regridClient, RegridClient)

    def testGoogleClientGetByAddress(self):
        addressInfo, errorHandler = self.googleClient.getByAddress("6760 SW 48TH ST, MiamiDade")
        self.assertIsNotNone(addressInfo)
        self.assertEqual(errorHandler["status"], "success")

    def testRegridClientGetByAddress(self):
        addressInfo, errorHandler = self.regridClient.getByAddress("6760 SW 48TH ST, MiamiDade")
        self.assertIsNotNone(addressInfo)
        self.assertEqual(errorHandler["status"], "success")

    def testAppraiserInfoByAddressInfoGoogle(self):
        addressInfo, _ = self.googleClient.getByAddress("6760 SW 48TH ST, MiamiDade")
        appraiserInfo, errorHandler = CentralizedAppraiser.appraiserInfoByAddressInfo(addressInfo, self.googleClient)
        self.assertIsNotNone(appraiserInfo)
        self.assertEqual(errorHandler["status"], "success")

    def testAppraiserInfoByAddressInfoRegrid(self):
        addressInfo, _ = self.regridClient.getByAddress("6760 SW 48TH ST, MiamiDade")
        appraiserInfo, errorHandler = CentralizedAppraiser.appraiserInfoByAddressInfo(addressInfo, self.regridClient)
        self.assertIsNotNone(appraiserInfo)
        self.assertEqual(errorHandler["status"], "success")

if __name__ == '__main__':
    unittest.main()