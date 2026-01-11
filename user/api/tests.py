from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from user.models import Employee, Role, User  # type: ignore
from user.api.serializers import EmployeeProfileSerializer

User = get_user_model()


class EmployeeAuthenticationAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
    
    def test_employee_registration_success(self):
        url = reverse('user_api:employee-register')
        data = {
            'email': 'newemployee@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!',
            'full_name': 'John Doe',
            'role': Role.MENTOR,
            'professionality': 'Revit Architecture Expert'
        }
        response = self.client.post(url, data, format='json')  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  # type: ignore
        self.assertTrue(response.data['success'])  # type: ignore
        self.assertIn('tokens', response.data['data'])  # type: ignore
        self.assertIn('employee', response.data['data'])  # type: ignore
        self.assertTrue(User._default_manager.filter(email='newemployee@test.com').exists())  # type: ignore
        self.assertTrue(Employee._default_manager.filter(user__email='newemployee@test.com').exists())  # type: ignore
    
    def test_employee_registration_password_mismatch(self):
        url = reverse('user_api:employee-register')
        data = {
            'email': 'newemployee@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'SecurePassword123!',
            'password_confirm': 'DifferentPassword123!',
            'full_name': 'John Doe',
            'role': Role.MENTOR
        }
        response = self.client.post(url, data, format='json')  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # type: ignore
    
    def test_employee_registration_duplicate_email(self):
        User._default_manager.create_user(  # type: ignore
            email='existing@test.com',
            password='testpass123',
            first_name='Existing',
            last_name='User'
        )
        
        url = reverse('user_api:employee-register')
        data = {
            'email': 'existing@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!',
            'full_name': 'John Doe',
            'role': Role.MENTOR
        }
        response = self.client.post(url, data, format='json')  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # type: ignore
    
    def test_employee_login_success(self):
        user = User._default_manager.create_user(
            email='employee@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        Employee._default_manager.create(  # type: ignore
            user=user,
            full_name='John Doe',
            role=Role.MENTOR
        )
        
        url = reverse('user_api:employee-login')
        data = {
            'email': 'employee@test.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # type: ignore
        self.assertTrue(response.data['success'])  # type: ignore
        self.assertIn('tokens', response.data['data'])  # type: ignore
    
    def test_employee_login_invalid_credentials(self):
        url = reverse('user_api:employee-login')
        data = {
            'email': 'nonexistent@test.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # type: ignore
    
    def test_employee_login_no_employee_profile(self):
        user = User._default_manager.create_user(
            email='user@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        
        url = reverse('user_api:employee-login')
        data = {
            'email': 'user@test.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # type: ignore
    
    def test_get_profile_requires_authentication(self):
        url = reverse('user_api:employee-profile')
        response = self.client.get(url)  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)  # type: ignore
    
    def test_get_profile_success(self):
        user = User._default_manager.create_user(
            email='employee@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        employee = Employee._default_manager.create(
            user=user,
            full_name='John Doe',
            role=Role.MENTOR,
            professionality='Revit Expert'
        )
        
        token = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        
        url = reverse('user_api:employee-profile')
        response = self.client.get(url)  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # type: ignore
        self.assertTrue(response.data['success'])  # type: ignore
        self.assertEqual(response.data['data']['id'], employee.id)  # type: ignore
        self.assertEqual(response.data['data']['email'], 'employee@test.com')  # type: ignore
    
    def test_update_profile_success(self):
        user = User._default_manager.create_user(
            email='employee@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        employee = Employee._default_manager.create(
            user=user,
            full_name='John Doe',
            role=Role.MENTOR
        )
        
        token = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
        
        url = reverse('user_api:employee-profile')
        data = {
            'full_name': 'John Updated Doe',
            'professionality': 'Updated Professionality'
        }
        response = self.client.patch(url, data, format='json')  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # type: ignore
        self.assertTrue(response.data['success'])  # type: ignore
        employee.refresh_from_db()
        self.assertEqual(employee.full_name, 'John Updated Doe')
        self.assertEqual(employee.professionality, 'Updated Professionality')


class EmployeeManagementAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        self.admin_user = User._default_manager.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        self.admin_employee = Employee._default_manager.create(
            user=self.admin_user,
            full_name='Admin User',
            role=Role.ADMINISTRATOR
        )
        admin_token = RefreshToken.for_user(self.admin_user)
        self.admin_token = str(admin_token.access_token)
        
        self.employee_user = User._default_manager.create_user(
            email='employee@test.com',
            password='testpass123',
            first_name='Employee',
            last_name='User'
        )
        self.employee = Employee._default_manager.create(
            user=self.employee_user,
            full_name='Employee User',
            role=Role.MENTOR
        )
    
    def test_list_employees_requires_authentication(self):
        url = reverse('user_api:employee-list')
        response = self.client.get(url)  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)  # type: ignore
    
    def test_list_employees_requires_admin_or_developer(self):
        mentor_user = User._default_manager.create_user(
            email='mentor@test.com',
            password='testpass123',
            first_name='Mentor',
            last_name='User'
        )
        Employee._default_manager.create(  # type: ignore
            user=mentor_user,
            full_name='Mentor User',
            role=Role.MENTOR
        )
        mentor_token = RefreshToken.for_user(mentor_user)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(mentor_token.access_token)}')
        url = reverse('user_api:employee-list')
        response = self.client.get(url)  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  # type: ignore
    
    def test_list_employees_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('user_api:employee-list')
        response = self.client.get(url)  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # type: ignore
        if isinstance(response.data, dict):  # type: ignore
            self.assertTrue(response.data.get('success', False))  # type: ignore
            if 'data' in response.data:  # type: ignore
                self.assertIsInstance(response.data['data'], list)  # type: ignore
        else:
            self.assertIsInstance(response.data, list)  # type: ignore
            self.assertGreater(len(response.data), 0)  # type: ignore
    
    def test_get_employee_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('user_api:employee-detail', kwargs={'pk': self.employee.id})
        response = self.client.get(url)  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # type: ignore
        if isinstance(response.data, dict):  # type: ignore
            self.assertTrue(response.data.get('success', False))  # type: ignore
            if 'data' in response.data:  # type: ignore
                self.assertEqual(response.data['data']['id'], self.employee.id)  # type: ignore
    
    def test_update_employee_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('user_api:employee-detail', kwargs={'pk': self.employee.id})
        data = {
            'role': Role.SALES_AGENT,
            'is_active': False,
            'full_name': 'Updated Name'
        }
        response = self.client.patch(url, data, format='json')  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # type: ignore
        if isinstance(response.data, dict):  # type: ignore
            self.assertTrue(response.data.get('success', False))  # type: ignore
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.role, Role.SALES_AGENT)
        self.assertFalse(self.employee.user.is_active)
    
    def test_update_employee_admin_cannot_update_director(self):
        director_user = User._default_manager.create_user(
            email='director@test.com',
            password='testpass123',
            first_name='Director',
            last_name='User'
        )
        director_employee = Employee._default_manager.create(
            user=director_user,
            full_name='Director User',
            role=Role.DIRECTOR
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('user_api:employee-detail', kwargs={'pk': director_employee.id})
        data = {'role': Role.MENTOR}
        response = self.client.patch(url, data, format='json')  # type: ignore
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])  # type: ignore
    
    def test_update_employee_developer_can_update_anyone(self):
        developer_user = User._default_manager.create_user(
            email='developer@test.com',
            password='testpass123',
            first_name='Developer',
            last_name='User'
        )
        developer_employee = Employee._default_manager.create(
            user=developer_user,
            full_name='Developer User',
            role=Role.DEVELOPER
        )
        developer_token = RefreshToken.for_user(developer_user)
        
        director_user = User._default_manager.create_user(
            email='director@test.com',
            password='testpass123',
            first_name='Director',
            last_name='User'
        )
        director_employee = Employee._default_manager.create(
            user=director_user,
            full_name='Director User',
            role=Role.DIRECTOR
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(developer_token.access_token)}')
        url = reverse('user_api:employee-detail', kwargs={'pk': director_employee.id})
        data = {'role': Role.MENTOR}
        response = self.client.patch(url, data, format='json')  # type: ignore
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # type: ignore
        director_employee.refresh_from_db()
        self.assertEqual(director_employee.role, Role.MENTOR)
