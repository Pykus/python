from django.test import TestCase
from .models import Device

class DeviceModelTests(TestCase):
    def test_hostname_is_unique(self):
        Device.objects.create(hostname="lab-pc-01")
        with self.assertRaises(Exception):
            Device.objects.create(hostname="lab-pc-01")

    def test_default_order_is_hostname(self):
        Device.objects.create(hostname="lab-pc-02")
        Device.objects.create(hostname="lab-pc-01")
        self.assertEqual(list(Device.objects.values_list("hostname", flat=True)), ["lab-pc-01", "lab-pc-02"])
