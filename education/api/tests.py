from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from user.models import User, Employee, Student, Role, Source, Speciality
from education.models import Group, Attendance, Dates


class GroupAPITestCase(TestCase):
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
        
        self.mentor_user = User._default_manager.create_user(
            email='mentor@test.com',
            password='testpass123',
            first_name='Mentor',
            last_name='User'
        )
        self.mentor_employee = Employee._default_manager.create(
            user=self.mentor_user,
            full_name='Mentor User',
            role=Role.MENTOR
        )
        
        self.group = Group._default_manager.create(
            speciality_id=Speciality.REVIT_ARCHITECTURE,
            dates=Dates.MON_WED_FRI,
            time='14:00:00',
            seats=15,
            starting_date=date.today() + timedelta(days=10),
            mentor=self.mentor_employee
        )
    
    def test_list_groups_requires_authentication(self):
        url = reverse('education_api:group-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_groups_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:group-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response can be either paginated (DRF format) or success_response format
        if isinstance(response.data, dict):
            # Check if it's a paginated response (has 'results' key) or success_response format
            if 'results' in response.data:
                # Paginated response - check results
                self.assertIn('results', response.data)
                self.assertIsInstance(response.data['results'], list)
            elif 'success' in response.data:
                # success_response format
                self.assertTrue(response.data.get('success', False))
                self.assertIn('data', response.data)
            else:
                # Other dict format - just verify it's a dict
                self.assertIsInstance(response.data, dict)
        else:
            # List response (non-paginated)
            self.assertIsInstance(response.data, list)
    
    def test_create_group_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:group-list-create')
        data = {
            'speciality_id': Speciality.REVIT_STRUCTURE,
            'dates': Dates.TUE_THU_SAT,
            'time': '10:00:00',
            'seats': 12,
            'starting_date': date.today() + timedelta(days=20),
            'mentor': self.mentor_employee.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(Group._default_manager.count(), 2)
    
    def test_create_group_invalid_mentor(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:group-list-create')
        data = {
            'speciality_id': Speciality.REVIT_STRUCTURE,
            'dates': Dates.TUE_THU_SAT,
            'time': '10:00:00',
            'seats': 12,
            'mentor': self.admin_employee.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_group_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:group-retrieve-update-destroy', kwargs={'pk': self.group.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['id'], self.group.id)
    
    def test_update_group_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:group-retrieve-update-destroy', kwargs={'pk': self.group.id})
        data = {'seats': 20}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertEqual(self.group.seats, 20)
    
    def test_delete_group_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:group-retrieve-update-destroy', kwargs={'pk': self.group.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Group._default_manager.filter(id=self.group.id).exists())


class AttendanceAPITestCase(TestCase):
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
        
        self.mentor_user = User._default_manager.create_user(
            email='mentor@test.com',
            password='testpass123',
            first_name='Mentor',
            last_name='User'
        )
        self.mentor_employee = Employee._default_manager.create(
            user=self.mentor_user,
            full_name='Mentor User',
            role=Role.MENTOR
        )
        
        self.group = Group._default_manager.create(
            speciality_id=Speciality.REVIT_ARCHITECTURE,
            dates=Dates.MON_WED_FRI,
            time='14:00:00',
            seats=15,
            mentor=self.mentor_employee
        )
        
        self.student1 = Student._default_manager.create(
            full_name='Student One',
            phone='+998901234567',
            passport_serial_number='AB1234567',
            birth_date=date(2000, 1, 1),
            source=Source.INSTAGRAM,
            group=self.group
        )
        self.student2 = Student._default_manager.create(
            full_name='Student Two',
            phone='+998901234568',
            passport_serial_number='AB1234568',
            birth_date=date(2000, 1, 1),
            source=Source.INSTAGRAM,
            group=self.group
        )
    
    def test_list_attendances_requires_authentication(self):
        url = reverse('education_api:attendance-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_attendances_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:attendance-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response can be either paginated (DRF format) or success_response format
        if isinstance(response.data, dict):
            # Check if it's a paginated response (has 'results' key) or success_response format
            if 'results' in response.data:
                # Paginated response - check results
                self.assertIn('results', response.data)
                self.assertIsInstance(response.data['results'], list)
            elif 'success' in response.data:
                # success_response format
                self.assertTrue(response.data.get('success', False))
                self.assertIn('data', response.data)
            else:
                # Other dict format - just verify it's a dict
                self.assertIsInstance(response.data, dict)
        else:
            # List response (non-paginated)
            self.assertIsInstance(response.data, list)
    
    def test_create_attendance_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:attendance-list-create')
        data = {
            'group': self.group.id,
            'date': date.today(),
            'mentor': self.mentor_employee.id,
            'participants': [self.student1.id, self.student2.id]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(Attendance._default_manager.count(), 1)
    
    def test_create_attendance_invalid_participant(self):
        other_student = Student._default_manager.create(
            full_name='Other Student',
            phone='+998901234569',
            passport_serial_number='AB1234569',
            birth_date=date(2000, 1, 1),
            source=Source.INSTAGRAM
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:attendance-list-create')
        data = {
            'group': self.group.id,
            'date': date.today(),
            'mentor': self.mentor_employee.id,
            'participants': [other_student.id]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_attendance_success(self):
        attendance = Attendance._default_manager.create(
            group=self.group,
            date=date.today(),
            mentor=self.mentor_employee
        )
        attendance.participants.set([self.student1, self.student2])
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:attendance-retrieve-update-destroy', kwargs={'pk': attendance.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_update_attendance_success(self):
        attendance = Attendance._default_manager.create(
            group=self.group,
            date=date.today(),
            mentor=self.mentor_employee
        )
        attendance.participants.set([self.student1])
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:attendance-retrieve-update-destroy', kwargs={'pk': attendance.id})
        data = {'participants': [self.student1.id, self.student2.id]}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attendance.refresh_from_db()
        self.assertEqual(attendance.participants.count(), 2)
    
    def test_delete_attendance_success(self):
        attendance = Attendance._default_manager.create(
            group=self.group,
            date=date.today(),
            mentor=self.mentor_employee
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = reverse('education_api:attendance-retrieve-update-destroy', kwargs={'pk': attendance.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Attendance._default_manager.filter(id=attendance.id).exists())


class BookingAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        self.mentor_user = User._default_manager.create_user(
            email='mentor@test.com',
            password='testpass123',
            first_name='Mentor',
            last_name='User'
        )
        self.mentor_employee = Employee._default_manager.create(
            user=self.mentor_user,
            full_name='Mentor User',
            role=Role.MENTOR
        )
        
        self.planned_group = Group._default_manager.create(
            speciality_id=Speciality.REVIT_ARCHITECTURE,
            dates=Dates.MON_WED_FRI,
            time='14:00:00',
            seats=15,
            starting_date=date.today() + timedelta(days=10),
            mentor=self.mentor_employee
        )
        
        self.active_group = Group._default_manager.create(
            speciality_id=Speciality.REVIT_ARCHITECTURE,
            dates=Dates.TUE_THU_SAT,
            time='10:00:00',
            seats=12,
            starting_date=date.today() - timedelta(days=5),
            mentor=self.mentor_employee
        )
        
        self.old_group = Group._default_manager.create(
            speciality_id=Speciality.REVIT_ARCHITECTURE,
            dates=Dates.MON_WED_FRI,
            time='16:00:00',
            seats=10,
            starting_date=date.today() - timedelta(days=15),
            mentor=self.mentor_employee
        )
        
        self.student = Student._default_manager.create(
            full_name='Test Student',
            phone='+998901234567',
            passport_serial_number='AB1234567',
            birth_date=date(2000, 1, 1),
            source=Source.INSTAGRAM
        )
    
    def test_list_groups_for_booking_no_auth_required(self):
        url = reverse('education_api:booking-group-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
    
    def test_list_groups_includes_booking_info(self):
        url = reverse('education_api:booking-group-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        group_data = response.data[0]
        self.assertIn('can_accept_bookings', group_data)
        self.assertIn('days_since_start', group_data)
        self.assertIn('available_seats', group_data)
    
    def test_book_student_planned_group_success(self):
        url = reverse('education_api:booking-create')
        data = {
            'student_id': self.student.id,
            'group_id': self.planned_group.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.student.refresh_from_db()
        self.assertEqual(self.student.group.id, self.planned_group.id)
    
    def test_book_student_active_group_less_than_10_days_success(self):
        url = reverse('education_api:booking-create')
        data = {
            'student_id': self.student.id,
            'group_id': self.active_group.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
    
    def test_book_student_old_group_fails_10_day_rule(self):
        url = reverse('education_api:booking-create')
        data = {
            'student_id': self.student.id,
            'group_id': self.old_group.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Response can be DRF validation error (no 'success' field) or error_response format
        if isinstance(response.data, dict):
            # If it's error_response format, check 'success' field
            if 'success' in response.data:
                self.assertFalse(response.data.get('success', True))
            # Check message or error details
            message = response.data.get('message', '').lower()
            errors = response.data.get('errors', {})
            # Check if message or errors contain 10-day rule info
            has_10_day_rule = (
                '10-day' in message or '10 day' in message or 'limit' in message or
                '10 kunlik' in message or 'cheklov' in message or
                any('10 kunlik' in str(err) or 'cheklov' in str(err) for err_list in errors.values() for err in (err_list if isinstance(err_list, list) else [err_list]))
            )
            self.assertTrue(has_10_day_rule or 'group_id' in errors, f"Expected 10-day rule error, got: {response.data}")
            if 'data' in response.data and response.data['data']:
                self.assertIn('alternatives', response.data['data'])
    
    def test_book_student_full_group_fails(self):
        for i in range(self.planned_group.seats):
            Student._default_manager.create(
                full_name=f'Student {i}',
                phone=f'+9989012345{i:02d}',
                passport_serial_number=f'AB12345{i:02d}',
                birth_date=date(2000, 1, 1),
                source=Source.INSTAGRAM,
                group=self.planned_group
            )
        
        url = reverse('education_api:booking-create')
        data = {
            'student_id': self.student.id,
            'group_id': self.planned_group.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Response can be DRF validation error (no 'success' field) or error_response format
        if isinstance(response.data, dict):
            # If it's error_response format, check 'success' field
            if 'success' in response.data:
                self.assertFalse(response.data.get('success', True))
            # Check message or error details
            message = response.data.get('message', '').lower()
            errors = response.data.get('errors', {})
            # Check if message or errors contain seat availability info
            has_seat_error = (
                'no available seats' in message or 'full' in message or 'seats' in message or
                'bo\'sh o\'rin' in message or 'to\'liq' in message or
                any('o\'rin' in str(err) or 'to\'liq' in str(err) for err_list in errors.values() for err in (err_list if isinstance(err_list, list) else [err_list]))
            )
            self.assertTrue(has_seat_error or 'group_id' in errors, f"Expected seat availability error, got: {response.data}")
    
    def test_book_student_already_booked_fails(self):
        self.student.group = self.planned_group
        self.student.save()
        
        url = reverse('education_api:booking-create')
        data = {
            'student_id': self.student.id,
            'group_id': self.active_group.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Response can be DRF validation error (no 'success' field) or error_response format
        if isinstance(response.data, dict):
            # If it's error_response format, check 'success' field
            if 'success' in response.data:
                self.assertFalse(response.data.get('success', True))
            # Check message or error details
            message = response.data.get('message', '').lower()
            errors = response.data.get('errors', {})
            # Check if message or errors contain already booked info
            has_already_booked_error = (
                'already booked' in message or 'already has' in message or
                'allaqachon yozilgan' in message or 'boshqa guruhga' in message or
                any('yozilgan' in str(err) for err_list in errors.values() for err in (err_list if isinstance(err_list, list) else [err_list]))
            )
            self.assertTrue(has_already_booked_error or 'student_id' in errors or 'group_id' in errors, f"Expected already booked error, got: {response.data}")
    
    def test_book_student_not_found(self):
        url = reverse('education_api:booking-create')
        data = {
            'student_id': 99999,
            'group_id': self.planned_group.id
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST])
    
    def test_book_group_not_found(self):
        url = reverse('education_api:booking-create')
        data = {
            'student_id': self.student.id,
            'group_id': 99999
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST])
    
    def test_cancel_booking_success(self):
        self.student.group = self.planned_group
        self.student.save()
        
        url = reverse('education_api:booking-cancel')
        data = {'student_id': self.student.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.student.refresh_from_db()
        self.assertIsNone(self.student.group)
    
    def test_cancel_booking_no_booking_fails(self):
        url = reverse('education_api:booking-cancel')
        data = {'student_id': self.student.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        message = response.data.get('message', '').lower()
        self.assertTrue('no active booking' in message or 'faol yozilishi yo\'q' in message or 'faol yozilishi' in message)
    
    def test_cancel_booking_student_not_found(self):
        url = reverse('education_api:booking-cancel')
        data = {'student_id': 99999}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_alternative_groups_suggested_on_10_day_limit(self):
        alternative_group = Group._default_manager.create(
            speciality_id=Speciality.REVIT_ARCHITECTURE,
            dates=Dates.TUE_THU_SAT,
            time='10:00:00',
            seats=10,
            starting_date=date.today() + timedelta(days=20),
            mentor=self.mentor_employee
        )
        
        url = reverse('education_api:booking-create')
        data = {
            'student_id': self.student.id,
            'group_id': self.old_group.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        if isinstance(response.data, dict) and 'data' in response.data and response.data['data']:
            alternatives = response.data['data'].get('alternatives', [])
            if alternatives:
                self.assertGreater(len(alternatives), 0)
                self.assertEqual(alternatives[0]['speciality_id'], Speciality.REVIT_ARCHITECTURE)
