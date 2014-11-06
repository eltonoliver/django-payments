import urllib
from unittest import TestCase
from urllib2 import URLError

from mock import MagicMock

from payments import RedirectNeeded
from . import Dummy3DSecureProvider


VARIANT = 'dummy-3ds'


class Payment(object):

    id = 1
    variant = VARIANT
    currency = 'USD'
    total = 100
    status = 'waiting'
    fraud_status = ''

    def get_process_url(self):
        return 'http://example.com'

    def get_failure_url(self):
        return 'http://cancel.com'

    def get_success_url(self):
        return 'http://success.com'

    def change_status(self, new_status):
        self.status = new_status

    def change_fraud_status(self, fraud_status):
        self.fraud_status = fraud_status


class TestDummy3DSProvider(TestCase):

    def setUp(self):
        self.payment = Payment()

    def test_process_data_supports_verification_result(self):
        provider = Dummy3DSecureProvider(self.payment)
        verification_status = 'confirmed'
        request = MagicMock()
        request.GET = {'verification_result': verification_status}
        response = provider.process_data(request)
        self.assertEqual(self.payment.status, verification_status)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['location'], self.payment.get_success_url())

    def test_process_data_redirects_to_success_on_payment_success(self):
        self.payment.status = 'preauth'
        provider = Dummy3DSecureProvider(self.payment)
        request = MagicMock()
        request.GET = {}
        response = provider.process_data(request)
        self.assertEqual(response['location'], self.payment.get_success_url())

    def test_process_data_redirects_to_failure_on_payment_failure(self):
        self.payment.status = 'reject'
        provider = Dummy3DSecureProvider(self.payment)
        request = MagicMock()
        request.GET = {}
        response = provider.process_data(request)
        self.assertEqual(response['location'], self.payment.get_failure_url())

    def test_provider_supports_non_3ds_transactions(self):
        provider = Dummy3DSecureProvider(self.payment)
        data = {
            'status': 'preauth',
            'fraud_status': 'unknown',
            'gateway_response': '3ds-disabled',
            'verification_result': ''
        }
        with self.assertRaises(RedirectNeeded) as exc:
            provider.get_form(data)
            self.assertEqual(exc.args[0], self.payment.get_success_url())

    def test_provider_supports_3ds_redirect(self):
        provider = Dummy3DSecureProvider(self.payment)
        verification_result = 'confirmed'
        data = {
            'status': 'waiting',
            'fraud_status': 'unknown',
            'gateway_response': '3ds-redirect',
            'verification_result': verification_result
        }
        params = urllib.urlencode({'verification_result': verification_result})
        expected_redirect = '%s?%s' % (self.payment.get_process_url(), params)

        with self.assertRaises(RedirectNeeded) as exc:
            provider.get_form(data)
            self.assertEqual(exc.args[0], expected_redirect)

    def test_provider_supports_gateway_failure(self):
        provider = Dummy3DSecureProvider(self.payment)
        data = {
            'status': 'waiting',
            'fraud_status': 'unknown',
            'gateway_response': 'failure',
            'verification_result': ''
        }
        with self.assertRaises(URLError) as exc:
            provider.get_form(data)

    def test_provider_raises_redirect_needed_on_success(self):
        provider = Dummy3DSecureProvider(self.payment)
        data = {
            'status': 'preauth',
            'fraud_status': 'unknown',
            'gateway_response': '3ds-disabled',
            'verification_result': ''
        }
        with self.assertRaises(RedirectNeeded) as exc:
            provider.get_form(data)
            self.assertEqual(exc.args[0], self.payment.get_success_url())

    def test_provider_raises_redirect_needed_on_failure(self):
        provider = Dummy3DSecureProvider(self.payment)
        data = {
            'status': 'error',
            'fraud_status': 'unknown',
            'gateway_response': '3ds-disabled',
            'verification_result': ''
        }
        with self.assertRaises(RedirectNeeded) as exc:
            provider.get_form(data)
            self.assertEqual(exc.args[0], self.payment.get_failure_url())
