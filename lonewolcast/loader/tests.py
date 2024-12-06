from django.test import TestCase
from firebase_admin import db

class FirebaseConnectionTest(TestCase):
    def test_firebase_connection(self):
        ref = db.reference('test')
        # Test write
        ref.set({'test': 'connection'})
        # Test read
        data = ref.get()
        self.assertEqual(data['test'], 'connection')
        # Clean up
        ref.delete()