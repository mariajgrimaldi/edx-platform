"""Unit tests for custom UserProfile properties."""


import datetime

import ddt
from django.core.cache import cache
from django.core.exceptions import ValidationError

from openedx.core.djangolib.testing.utils import CacheIsolationTestCase
from common.djangoapps.student.models import UserProfile
from common.djangoapps.student.tests.factories import UserFactory


@ddt.ddt
class UserProfilePropertiesTest(CacheIsolationTestCase):
    """Unit tests for age, gender_display, phone_number, and level_of_education_display properties ."""

    password = "test"

    ENABLED_CACHES = ['default']

    def setUp(self):
        super(UserProfilePropertiesTest, self).setUp()  # lint-amnesty, pylint: disable=super-with-arguments
        self.user = UserFactory.create(password=self.password)
        self.profile = self.user.profile

    def _set_year_of_birth(self, year_of_birth):
        """
        Helper method that sets a birth year for the specified user.
        """
        self.profile.year_of_birth = year_of_birth
        self.profile.save()

    def _set_level_of_education(self, level_of_education):
        """
        Helper method that sets a level of education for the specified user.
        """
        self.profile.level_of_education = level_of_education
        self.profile.save()

    def _set_gender(self, gender):
        """
        Helper method that sets a gender for the specified user.
        """
        self.profile.gender = gender
        self.profile.save()

    @ddt.data(0, 1, 13, 20, 100)
    def test_age(self, years_ago):
        """Verify the age calculated correctly."""
        current_year = datetime.datetime.now().year
        self._set_year_of_birth(current_year - years_ago)

        # In the year that your turn a certain age you will also have been a
        # year younger than that in that same year.  We calculate age based off of
        # the youngest you could be that year.
        age = years_ago - 1
        self.assertEqual(self.profile.age, age)

    def test_age_no_birth_year(self):
        """Verify nothing is returned."""
        self.assertIsNone(self.profile.age)

    @ddt.data(*UserProfile.LEVEL_OF_EDUCATION_CHOICES)
    @ddt.unpack
    def test_display_level_of_education(self, level_enum, display_level):
        """Verify the level of education is displayed correctly."""
        self._set_level_of_education(level_enum)

        self.assertEqual(self.profile.level_of_education_display, display_level)

    def test_display_level_of_education_none_set(self):
        """Verify nothing is returned."""
        self.assertIsNone(self.profile.level_of_education_display)

    @ddt.data(*UserProfile.GENDER_CHOICES)
    @ddt.unpack
    def test_display_gender(self, gender_enum, display_gender):
        """Verify the gender displayed correctly."""
        self._set_gender(gender_enum)

        self.assertEqual(self.profile.gender_display, display_gender)

    def test_display_gender_none_set(self):
        """Verify nothing is returned."""
        self._set_gender(None)

        self.assertIsNone(self.profile.gender_display)

    def test_invalidate_cache_user_profile_country_updated(self):

        country = 'US'
        self.profile.country = country
        self.profile.save()

        cache_key = UserProfile.country_cache_key_name(self.user.id)
        self.assertIsNone(cache.get(cache_key))

        cache.set(cache_key, self.profile.country)
        self.assertEqual(cache.get(cache_key), country)

        country = 'bd'
        self.profile.country = country
        self.profile.save()

        self.assertNotEqual(cache.get(cache_key), country)
        self.assertIsNone(cache.get(cache_key))

    def test_phone_number_can_only_contain_digits(self):
        # validating the profile will fail, because there are letters
        # in the phone number
        self.profile.phone_number = 'abc'
        self.assertRaises(ValidationError, self.profile.full_clean)
        # fail if mixed digits/letters
        self.profile.phone_number = '1234gb'
        self.assertRaises(ValidationError, self.profile.full_clean)
        # fail if whitespace
        self.profile.phone_number = '   123'
        self.assertRaises(ValidationError, self.profile.full_clean)
        # fail with special characters
        self.profile.phone_number = '123!@#$%^&*'
        self.assertRaises(ValidationError, self.profile.full_clean)
        # valid phone number
        self.profile.phone_number = '123456789'
        try:
            self.profile.full_clean()
        except ValidationError:
            self.fail("This phone number should  be valid.")
