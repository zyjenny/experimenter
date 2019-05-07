import datetime
import decimal
import random
import re
from urllib.parse import urlencode

import mock
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from experimenter.base.tests.factories import CountryFactory, LocaleFactory
from experimenter.experiments.forms import (
    ExperimentVariantsAddonForm,
    ExperimentVariantsPrefForm,
)
from experimenter.experiments.forms import NormandyIdForm
from experimenter.experiments.models import Experiment
from experimenter.experiments.tests.factories import ExperimentFactory
from experimenter.experiments.tests.mixins import MockTasksMixin
from experimenter.openidc.tests.factories import UserFactory
from experimenter.projects.tests.factories import ProjectFactory
from experimenter.experiments.views import (
    ExperimentFilterset,
    ExperimentFiltersetForm,
    ExperimentFormMixin,
    ExperimentOrderingForm,
)


class TestExperimentFiltersetForm(TestCase):

    def test_get_project_display_value_returns_project_str(self):
        project = ProjectFactory.create()
        form = ExperimentFiltersetForm({"project": project.id})
        self.assertEqual(form.get_project_display_value(), str(project))

    def test_get_owner_display_value_returns_user_str(self):
        user = UserFactory.create()
        form = ExperimentFiltersetForm({"owner": user.id})
        self.assertEqual(form.get_owner_display_value(), str(user))

    def test_get_type_display_value_returns_type_str(self):
        form = ExperimentFiltersetForm({"type": Experiment.TYPE_ADDON})
        self.assertEqual(
            form.get_type_display_value(),
            dict(Experiment.TYPE_CHOICES)[Experiment.TYPE_ADDON],
        )


class TestExperimentFilterset(TestCase):

    def test_filters_out_archived_by_default(self):
        for i in range(3):
            ExperimentFactory.create_with_status(
                Experiment.STATUS_DRAFT, archived=False
            )

        for i in range(3):
            ExperimentFactory.create_with_status(
                Experiment.STATUS_DRAFT, archived=True
            )

        filter = ExperimentFilterset(
            data={}, queryset=Experiment.objects.all()
        )

        self.assertEqual(
            set(filter.qs), set(Experiment.objects.filter(archived=False))
        )

    def test_allows_archived_if_True(self):
        for i in range(3):
            ExperimentFactory.create_with_status(
                Experiment.STATUS_DRAFT, archived=False
            )

        for i in range(3):
            ExperimentFactory.create_with_status(
                Experiment.STATUS_DRAFT, archived=True
            )

        filter = ExperimentFilterset(
            data={"archived": True}, queryset=Experiment.objects.all()
        )

        self.assertEqual(set(filter.qs), set(Experiment.objects.all()))

    def test_filters_by_project(self):
        project = ProjectFactory.create()

        for i in range(3):
            ExperimentFactory.create_with_status(
                Experiment.STATUS_DRAFT, project=project
            )
            ExperimentFactory.create_with_status(Experiment.STATUS_DRAFT)

        filter = ExperimentFilterset(
            {"project": project.id}, queryset=Experiment.objects.all()
        )

        self.assertEqual(
            set(filter.qs), set(Experiment.objects.filter(project=project))
        )

    def test_filters_by_owner(self):
        owner = UserFactory.create()

        for i in range(3):
            ExperimentFactory.create_with_status(
                Experiment.STATUS_DRAFT, owner=owner
            )
            ExperimentFactory.create_with_status(Experiment.STATUS_DRAFT)

        filter = ExperimentFilterset(
            {"owner": owner.id}, queryset=Experiment.objects.all()
        )

        self.assertEqual(
            set(filter.qs), set(Experiment.objects.filter(owner=owner))
        )

    def test_filters_by_status(self):
        for i in range(3):
            ExperimentFactory.create_with_status(Experiment.STATUS_DRAFT)
            ExperimentFactory.create_with_status(Experiment.STATUS_REVIEW)

        filter = ExperimentFilterset(
            {"status": Experiment.STATUS_DRAFT},
            queryset=Experiment.objects.all(),
        )

        self.assertEqual(
            set(filter.qs),
            set(Experiment.objects.filter(status=Experiment.STATUS_DRAFT)),
        )

    def test_filters_by_firefox_version(self):
        include_version = Experiment.VERSION_CHOICES[1][0]
        exclude_version = Experiment.VERSION_CHOICES[2][0]

        for i in range(3):
            ExperimentFactory.create_with_variants(
                firefox_version=include_version
            )
            ExperimentFactory.create_with_variants(
                firefox_version=exclude_version
            )

        filter = ExperimentFilterset(
            {"firefox_version": include_version},
            queryset=Experiment.objects.all(),
        )
        self.assertEqual(
            set(filter.qs),
            set(Experiment.objects.filter(firefox_version=include_version)),
        )

    def test_filters_by_firefox_channel(self):
        include_channel = Experiment.CHANNEL_CHOICES[1][0]
        exclude_channel = Experiment.CHANNEL_CHOICES[2][0]

        for i in range(3):
            ExperimentFactory.create_with_variants(
                firefox_channel=include_channel
            )
            ExperimentFactory.create_with_variants(
                firefox_channel=exclude_channel
            )

        filter = ExperimentFilterset(
            {"firefox_channel": include_channel},
            queryset=Experiment.objects.all(),
        )
        self.assertEqual(
            set(filter.qs),
            set(Experiment.objects.filter(firefox_channel=include_channel)),
        )

    def test_list_filters_by_search_text(self):
        user_email = "user@example.com"

        exp_1 = ExperimentFactory.create_with_status(
            random.choice(Experiment.STATUS_CHOICES)[0],
            name="Experiment One Cat",
            short_description="",
            slug="exp-1",
            related_work="",
            addon_experiment_id="1",
            pref_key="",
            public_name="",
            public_description="",
            objectives="",
            analysis="",
            analysis_owner="",
            engineering_owner="",
            bugzilla_id="4",
            normandy_slug="",
        )

        exp_2 = ExperimentFactory.create_with_status(
            random.choice(Experiment.STATUS_CHOICES)[0],
            name="Experiment Two Cat",
            short_description="",
            slug="exp-2",
            related_work="",
            addon_experiment_id="2",
            pref_key="",
            public_name="",
            public_description="",
            objectives="",
            analysis="",
            analysis_owner="",
            engineering_owner="",
            bugzilla_id="5",
            normandy_slug="",
        )

        exp_3 = ExperimentFactory.create_with_status(
            random.choice(Experiment.STATUS_CHOICES)[0],
            name="Experiment Three Dog",
            short_description="",
            slug="exp-3",
            related_work="",
            addon_experiment_id="3",
            pref_key="",
            public_name="",
            public_description="",
            objectives="",
            analysis="",
            analysis_owner="",
            engineering_owner="",
            bugzilla_id="6",
            normandy_slug="",
        )

        first_response_context = self.client.get(
            "{url}?{params}".format(
                url=reverse("home"), params=urlencode({"search": "Cat"})
            ),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        ).context[0]

        second_response_context = self.client.get(
            "{url}?{params}".format(
                url=reverse("home"), params=urlencode({"search": "Dog"})
            ),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        ).context[0]

        self.assertEqual(
            set(first_response_context["experiments"]), set([exp_1, exp_2])
        )
        self.assertEqual(
            set(second_response_context["experiments"]), set([exp_3])
        )

    def test_filters_by_review_in_qa(self):
        exp_1 = ExperimentFactory.create_with_variants(
            review_qa_requested=True, review_qa=False
        )
        ExperimentFactory.create_with_variants(
            review_qa_requested=False, review_qa=False
        )
        ExperimentFactory.create_with_variants(
            review_qa_requested=True, review_qa=True
        )

        filter = ExperimentFilterset(
            {"in_qa": "on"}, queryset=Experiment.objects.all()
        )

        self.assertEqual(set(filter.qs), set([exp_1]))


class TestExperimentOrderingForm(TestCase):

    def test_accepts_valid_ordering(self):
        ordering = ExperimentOrderingForm.ORDERING_CHOICES[1][0]
        form = ExperimentOrderingForm({"ordering": ordering})
        self.assertTrue(form.is_valid())

    def test_rejects_invalid_ordering(self):
        form = ExperimentOrderingForm({"ordering": "invalid ordering"})
        self.assertFalse(form.is_valid())


class TestExperimentListView(TestCase):

    def test_list_view_lists_experiments_with_default_order_no_archived(self):
        user_email = "user@example.com"

        # Archived experiment is ommitted
        ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT, archived=True
        )

        for i in range(3):
            ExperimentFactory.create_with_status(
                random.choice(Experiment.STATUS_CHOICES)[0]
            )

        experiments = (
            Experiment.objects.all()
            .filter(archived=False)
            .order_by(ExperimentOrderingForm.ORDERING_CHOICES[0][0])
        )

        response = self.client.get(
            reverse("home"), **{settings.OPENIDC_EMAIL_HEADER: user_email}
        )

        context = response.context[0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(context["experiments"]), list(experiments))

    def set_up_date_tests(self):

        self.exp_1 = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT,
            name="experiment 1",
            proposed_start_date=datetime.date(2019, 4, 5),
            proposed_duration=30,
            proposed_enrollment=3,
        )

        self.exp_2 = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT,
            name="experiment 2",
            proposed_start_date=datetime.date(2019, 3, 29),
            proposed_duration=14,
            proposed_enrollment=4,
        )

        self.exp_3 = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT,
            name="experiment 3",
            proposed_start_date=datetime.date(2019, 5, 29),
            proposed_duration=30,
            proposed_enrollment=None,
        )

        self.exp_4 = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT,
            name="experiment 4",
            proposed_start_date=datetime.date(2019, 3, 15),
            proposed_duration=25,
            proposed_enrollment=1,
        )

        self.start_range_date = "2019-04-01"
        self.end_range_date = "2019-05-01"
        self.user_email = "user@example.com"

    def test_list_shows_all_experiments_with_start_in_range(self):

        self.set_up_date_tests()

        response = self.client.get(
            "{url}?{params}".format(
                url=reverse("home"),
                params=urlencode(
                    {
                        "experiment_date_field": Experiment.EXPERIMENT_STARTS,
                        "date_range_after": self.start_range_date,
                        "date_range_before": self.end_range_date,
                    }
                ),
            ),
            **{settings.OPENIDC_EMAIL_HEADER: self.user_email},
        )

        context = response.context[0]

        self.assertEqual(set(context["experiments"]), set([self.exp_1]))

    def test_list_shows_all_experiments_with_pause_in_range(self):
        self.set_up_date_tests()

        response = self.client.get(
            "{url}?{params}".format(
                url=reverse("home"),
                params=urlencode(
                    {
                        "experiment_date_field": Experiment.EXPERIMENT_PAUSES,
                        "date_range_after": self.start_range_date,
                        "date_range_before": self.end_range_date,
                    }
                ),
            ),
            **{settings.OPENIDC_EMAIL_HEADER: self.user_email},
        )

        context = response.context[0]

        self.assertEqual(
            set(context["experiments"]), set([self.exp_1, self.exp_2])
        )

    def test_list_shows_all_experiments_with_end_in_range(self):
        self.set_up_date_tests()

        response = self.client.get(
            "{url}?{params}".format(
                url=reverse("home"),
                params=urlencode(
                    {
                        "experiment_date_field": Experiment.EXPERIMENT_ENDS,
                        "date_range_after": self.start_range_date,
                        "date_range_before": self.end_range_date,
                    }
                ),
            ),
            **{settings.OPENIDC_EMAIL_HEADER: self.user_email},
        )

        context = response.context[0]

        self.assertEqual(
            set(context["experiments"]), set([self.exp_2, self.exp_4])
        )

    def test_list_shows_all_experiments_with_start_in_range_start_date_only(
        self
    ):

        self.set_up_date_tests()

        response = self.client.get(
            "{url}?{params}".format(
                url=reverse("home"),
                params=urlencode(
                    {
                        "experiment_date_field": Experiment.EXPERIMENT_STARTS,
                        "date_range_after": self.start_range_date,
                        "date_range_before": "",
                    }
                ),
            ),
            **{settings.OPENIDC_EMAIL_HEADER: self.user_email},
        )

        context = response.context[0]

        self.assertEqual(
            set(context["experiments"]), set([self.exp_1, self.exp_3])
        )

    def test_list_shows_all_experiments_with_start_in_range_end_date_only(
        self
    ):
        self.set_up_date_tests()

        response = self.client.get(
            "{url}?{params}".format(
                url=reverse("home"),
                params=urlencode(
                    {
                        "experiment_date_field": Experiment.EXPERIMENT_STARTS,
                        "date_range_after": "",
                        "date_range_before": self.end_range_date,
                    }
                ),
            ),
            **{settings.OPENIDC_EMAIL_HEADER: self.user_email},
        )

        context = response.context[0]

        self.assertEqual(
            set(context["experiments"]),
            set([self.exp_1, self.exp_2, self.exp_4]),
        )

    def test_list_view_shows_all_including_archived(self):
        user_email = "user@example.com"

        # Archived experiment is included
        ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT, archived=True
        )

        for i in range(3):
            ExperimentFactory.create_with_status(
                random.choice(Experiment.STATUS_CHOICES)[0]
            )

        experiments = Experiment.objects.all()

        response = self.client.get(
            "{url}?{params}".format(
                url=reverse("home"), params=urlencode({"archived": True})
            ),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )

        context = response.context[0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(context["experiments"]), set(experiments))

    def test_list_view_filters_and_orders_experiments(self):
        user_email = "user@example.com"

        ordering = "latest_change"
        filtered_channel = Experiment.CHANNEL_CHOICES[1][0]
        filtered_owner = UserFactory.create()
        filtered_project = ProjectFactory.create()
        filtered_status = Experiment.STATUS_DRAFT
        filtered_version = Experiment.VERSION_CHOICES[1][0]

        for i in range(10):
            ExperimentFactory.create_with_status(
                firefox_channel=filtered_channel,
                firefox_version=filtered_version,
                owner=filtered_owner,
                project=filtered_project,
                target_status=filtered_status,
            )

        for i in range(10):
            ExperimentFactory.create_with_status(
                random.choice(Experiment.STATUS_CHOICES)[0]
            )

        filtered_ordered_experiments = Experiment.objects.filter(
            firefox_channel=filtered_channel,
            firefox_version=filtered_version,
            owner=filtered_owner,
            project=filtered_project,
            status=filtered_status,
        ).order_by(ordering)

        response = self.client.get(
            "{url}?{params}".format(
                url=reverse("home"),
                params=urlencode(
                    {
                        "firefox_channel": filtered_channel,
                        "firefox_version": filtered_version,
                        "ordering": ordering,
                        "owner": filtered_owner.id,
                        "project": filtered_project.id,
                        "status": filtered_status,
                    }
                ),
            ),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )

        context = response.context[0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(context["experiments"]), list(filtered_ordered_experiments)
        )

    def test_list_view_orders_experiments_firefox_channel_sort(self):
        user_email = "user@example.com"
        ordering = "firefox_channel_sort"
        channels = [
            Experiment.CHANNEL_RELEASE,
            Experiment.CHANNEL_NIGHTLY,
            Experiment.CHANNEL_BETA,
            "",
        ]
        for channel in channels:
            ExperimentFactory.create(firefox_channel=channel)

        response = self.client.get(
            "{url}?{params}".format(
                url=reverse("home"), params=urlencode({"ordering": ordering})
            ),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )

        context = response.context[0]
        self.assertEqual(
            list(exp.firefox_channel for exp in context["experiments"]),
            [
                "",
                Experiment.CHANNEL_NIGHTLY,
                Experiment.CHANNEL_BETA,
                Experiment.CHANNEL_RELEASE,
            ],
        )

    def test_list_view_total_experiments_count(self):
        user_email = "user@example.com"

        number_of_experiments = settings.EXPERIMENTS_PAGINATE_BY + 1
        for i in range(number_of_experiments):
            ExperimentFactory.create_with_status(
                random.choice(Experiment.STATUS_CHOICES)[0]
            )

        response = self.client.get(
            reverse("home"), **{settings.OPENIDC_EMAIL_HEADER: user_email}
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        total_count_regex = re.compile(
            rf"{number_of_experiments}\s+Experiments"
        )
        self.assertTrue(total_count_regex.search(html))

        # Go to page 2, and the total shouldn't change.
        response = self.client.get(
            "{url}?{params}".format(
                url=reverse("home"), params=urlencode({"page": 2})
            ),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertTrue(total_count_regex.search(html))
        self.assertTrue("Page 2" in html)


class TestExperimentFormMixin(TestCase):

    def test_get_form_kwargs_adds_request(self):

        class BaseTestView(object):

            def __init__(self, request):
                self.request = request

            def get_form_kwargs(self):
                return {}

        class TestView(ExperimentFormMixin, BaseTestView):
            pass

        request = mock.Mock()
        view = TestView(request=request)
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs["request"], request)

    @mock.patch("experimenter.experiments.views.reverse")
    def test_get_success_url_returns_next_url_if_action_is_continue(
        self, mock_reverse
    ):

        class BaseTestView(object):

            def __init__(self, request, instance):
                self.request = request
                self.object = instance

        class TestView(ExperimentFormMixin, BaseTestView):
            next_view_name = "next-test-view"

        def mock_reverser(url_name, *args, **kwargs):
            return url_name

        mock_reverse.side_effect = mock_reverser

        instance = mock.Mock()
        instance.slug = "slug"

        request = mock.Mock()
        request.POST = {"action": "continue"}

        view = TestView(request, instance)
        redirect = view.get_success_url()
        self.assertEqual(redirect, TestView.next_view_name)
        mock_reverse.assert_called_with(
            TestView.next_view_name, kwargs={"slug": instance.slug}
        )

    @mock.patch("experimenter.experiments.views.reverse")
    def test_get_success_url_returns_detail_url_if_action_is_empty(
        self, mock_reverse
    ):

        class BaseTestView(object):

            def __init__(self, request, instance):
                self.request = request
                self.object = instance

        class TestView(ExperimentFormMixin, BaseTestView):
            next_view_name = "next-test-view"

        def mock_reverser(url_name, *args, **kwargs):
            return url_name

        mock_reverse.side_effect = mock_reverser

        instance = mock.Mock()
        instance.slug = "slug"

        request = mock.Mock()
        request.POST = {}

        view = TestView(request, instance)
        redirect = view.get_success_url()
        self.assertEqual(redirect, "experiments-detail")
        mock_reverse.assert_called_with(
            "experiments-detail", kwargs={"slug": instance.slug}
        )


class TestExperimentCreateView(TestCase):

    def test_view_creates_experiment(self):
        user = UserFactory.create()
        user_email = user.email

        data = {
            "type": Experiment.TYPE_PREF,
            "name": "A new experiment!",
            "short_description": "Let us learn new things",
            "data_science_bugzilla_url": "https://bugzilla.mozilla.org/123/",
            "feature_bugzilla_url": "https://bugzilla.mozilla.org/123/",
            "related_work": "Designs: https://www.example.com/myproject/",
            "proposed_start_date": timezone.now().date(),
            "proposed_enrollment": 10,
            "proposed_duration": 20,
            "owner": user.id,
        }

        response = self.client.post(
            reverse("experiments-create"),
            data,
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertEqual(response.status_code, 302)

        experiment = Experiment.objects.get()
        self.assertEqual(experiment.status, experiment.STATUS_DRAFT)
        self.assertEqual(experiment.name, data["name"])

        self.assertEqual(experiment.changes.count(), 1)

        change = experiment.changes.get()

        self.assertEqual(change.changed_by, user)
        self.assertEqual(change.old_status, None)
        self.assertEqual(change.new_status, experiment.STATUS_DRAFT)


class TestExperimentOverviewUpdateView(TestCase):

    def test_view_saves_experiment(self):
        user = UserFactory.create()
        user_email = user.email
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT, proposed_enrollment=1, proposed_duration=2
        )

        new_start_date = timezone.now().date() + datetime.timedelta(
            days=random.randint(1, 100)
        )
        new_enrollment = experiment.proposed_enrollment + 1
        new_duration = experiment.proposed_duration + 1

        data = {
            "type": Experiment.TYPE_PREF,
            "name": "A new name!",
            "short_description": "A new description!",
            "data_science_bugzilla_url": "https://bugzilla.mozilla.org/123/",
            "feature_bugzilla_url": "https://bugzilla.mozilla.org/123/",
            "related_work": "Designs: https://www.example.com/myproject/",
            "proposed_start_date": new_start_date,
            "proposed_enrollment": new_enrollment,
            "proposed_duration": new_duration,
            "owner": user.id,
        }

        response = self.client.post(
            reverse(
                "experiments-overview-update", kwargs={"slug": experiment.slug}
            ),
            data,
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertEqual(response.status_code, 302)

        experiment = Experiment.objects.get()
        self.assertEqual(experiment.name, data["name"])
        self.assertEqual(
            experiment.short_description, data["short_description"]
        )
        self.assertEqual(experiment.proposed_start_date, new_start_date)
        self.assertEqual(experiment.proposed_enrollment, new_enrollment)
        self.assertEqual(experiment.proposed_duration, new_duration)

        self.assertEqual(experiment.changes.count(), 2)

        change = experiment.changes.latest()

        self.assertEqual(change.changed_by, user)
        self.assertEqual(change.old_status, experiment.STATUS_DRAFT)
        self.assertEqual(change.new_status, experiment.STATUS_DRAFT)


class TestExperimentVariantsUpdateView(TestCase):

    def test_uses_addon_form_for_addon_experiment(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT, type=Experiment.TYPE_ADDON
        )
        response = self.client.get(
            reverse(
                "experiments-variants-update", kwargs={"slug": experiment.slug}
            ),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(
            response.context["form"], ExperimentVariantsAddonForm
        )

    def test_uses_pref_form_for_pref_experiment(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT, type=Experiment.TYPE_PREF
        )
        response = self.client.get(
            reverse(
                "experiments-variants-update", kwargs={"slug": experiment.slug}
            ),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(
            response.context["form"], ExperimentVariantsPrefForm
        )

    def test_view_saves_experiment(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT
        )
        locale = LocaleFactory()
        country = CountryFactory()

        data = {
            "population_percent": "11",
            "firefox_version": Experiment.VERSION_CHOICES[-1][0],
            "firefox_channel": Experiment.CHANNEL_NIGHTLY,
            "client_matching": "New matching!",
            "platform": Experiment.PLATFORM_WINDOWS,
            "locales": [locale.code],
            "countries": [country.code],
            "public_name": "hello",
            "public_description": "description",
            "pref_key": "browser.test.example",
            "pref_type": Experiment.PREF_TYPE_STR,
            "pref_branch": Experiment.PREF_BRANCH_DEFAULT,
            "variants-TOTAL_FORMS": "3",
            "variants-INITIAL_FORMS": "0",
            "variants-MIN_NUM_FORMS": "0",
            "variants-MAX_NUM_FORMS": "1000",
            "variants-0-is_control": True,
            "variants-0-ratio": "34",
            "variants-0-name": "control name",
            "variants-0-description": "control desc",
            "variants-0-value": '"control value"',
            "variants-1-is_control": False,
            "variants-1-ratio": "33",
            "variants-1-name": "branch 1 name",
            "variants-1-description": "branch 1 desc",
            "variants-1-value": '"branch 1 value"',
            "variants-2-is_control": False,
            "variants-2-ratio": "33",
            "variants-2-name": "branch 2 name",
            "variants-2-description": "branch 2 desc",
            "variants-2-value": '"branch 2 value"',
        }

        response = self.client.post(
            reverse(
                "experiments-variants-update", kwargs={"slug": experiment.slug}
            ),
            data,
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertEqual(response.status_code, 302)

        experiment = Experiment.objects.get()

        self.assertEqual(
            experiment.population_percent,
            decimal.Decimal(data["population_percent"]),
        )
        self.assertEqual(experiment.firefox_version, data["firefox_version"])
        self.assertEqual(experiment.firefox_channel, data["firefox_channel"])
        self.assertEqual(experiment.platform, data["platform"])

        self.assertEqual(experiment.pref_key, data["pref_key"])
        self.assertEqual(experiment.pref_type, data["pref_type"])
        self.assertEqual(experiment.pref_branch, data["pref_branch"])

        self.assertTrue(locale in experiment.locales.all())

        self.assertTrue(country in experiment.countries.all())

        self.assertEqual(experiment.changes.count(), 2)

        change = experiment.changes.latest()

        self.assertEqual(change.changed_by.email, user_email)
        self.assertEqual(change.old_status, experiment.STATUS_DRAFT)
        self.assertEqual(change.new_status, experiment.STATUS_DRAFT)


class TestExperimentObjectivesUpdateView(TestCase):

    def test_view_saves_experiment(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT
        )

        data = {
            "objectives": "Some new objectives!",
            "analysis_owner": "Suzy Data Science",
            "analysis": "Some new analysis!",
        }

        response = self.client.post(
            reverse(
                "experiments-objectives-update",
                kwargs={"slug": experiment.slug},
            ),
            data,
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertEqual(response.status_code, 302)

        experiment = Experiment.objects.get()
        self.assertEqual(experiment.objectives, data["objectives"])
        self.assertEqual(experiment.analysis, data["analysis"])

        self.assertEqual(experiment.changes.count(), 2)

        change = experiment.changes.latest()

        self.assertEqual(change.changed_by.email, user_email)
        self.assertEqual(change.old_status, experiment.STATUS_DRAFT)
        self.assertEqual(change.new_status, experiment.STATUS_DRAFT)


class TestExperimentRisksUpdateView(TestCase):

    def test_view_saves_experiment(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT
        )

        data = {
            "risk_internal_only": True,
            "risk_partner_related": True,
            "risk_brand": True,
            "risk_fast_shipped": True,
            "risk_confidential": True,
            "risk_release_population": True,
            "risk_revenue": True,
            "risk_data_category": True,
            "risk_external_team_impact": True,
            "risk_telemetry_data": True,
            "risk_ux": True,
            "risk_security": True,
            "risk_revision": True,
            "risk_technical": True,
            "risk_technical_description": "It's complicated",
            "risks": "There are some risks",
            "testing": "Always be sure to test!",
            "test_builds": "Latest Build",
            "qa_status": "Green",
        }

        response = self.client.post(
            reverse(
                "experiments-risks-update", kwargs={"slug": experiment.slug}
            ),
            data,
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertEqual(response.status_code, 302)

        experiment = Experiment.objects.get()

        self.assertTrue(experiment.risk_internal_only)
        self.assertTrue(experiment.risk_partner_related)
        self.assertTrue(experiment.risk_brand)
        self.assertTrue(experiment.risk_fast_shipped)
        self.assertTrue(experiment.risk_confidential)
        self.assertTrue(experiment.risk_release_population)
        self.assertTrue(experiment.risk_technical)
        self.assertEqual(
            experiment.risk_technical_description,
            data["risk_technical_description"],
        )
        self.assertEqual(experiment.risks, data["risks"])
        self.assertEqual(experiment.testing, data["testing"])
        self.assertEqual(experiment.test_builds, data["test_builds"])
        self.assertEqual(experiment.qa_status, data["qa_status"])

        self.assertEqual(experiment.changes.count(), 2)

        change = experiment.changes.latest()

        self.assertEqual(change.changed_by.email, user_email)
        self.assertEqual(change.old_status, experiment.STATUS_DRAFT)
        self.assertEqual(change.new_status, experiment.STATUS_DRAFT)


class TestExperimentDetailView(TestCase):

    def test_view_renders_correctly(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT
        )

        response = self.client.get(
            reverse("experiments-detail", kwargs={"slug": experiment.slug}),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "experiments/detail_draft.html")
        self.assertTemplateUsed(response, "experiments/detail_base.html")

    def test_view_renders_locales_correctly(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT
        )
        experiment.locales.add(LocaleFactory(code="yy", name="Why"))
        experiment.locales.add(LocaleFactory(code="xx", name="Xess"))
        response = self.client.get(
            reverse("experiments-detail", kwargs={"slug": experiment.slug}),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertEqual(response.status_code, 200)

    def test_view_renders_countries_correctly(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT
        )
        experiment.countries.add(CountryFactory(code="YY", name="Wazoo"))
        experiment.countries.add(CountryFactory(code="XX", name="Xanadu"))
        response = self.client.get(
            reverse("experiments-detail", kwargs={"slug": experiment.slug}),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertEqual(response.status_code, 200)

    def test_includes_normandy_id_form_in_context(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_SHIP
        )
        response = self.client.get(
            reverse("experiments-detail", kwargs={"slug": experiment.slug}),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertTrue(
            isinstance(response.context[0]["normandy_id_form"], NormandyIdForm)
        )

    def test_includes_bound_normandy_id_form_if_GET_param_set(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_SHIP
        )
        bad_normandy_id = "abc"
        detail_url = reverse(
            "experiments-detail", kwargs={"slug": experiment.slug}
        )
        response = self.client.get(
            f"{detail_url}?normandy_id={bad_normandy_id}",
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        normandy_form = response.context[0]["normandy_id_form"]
        self.assertTrue(isinstance(normandy_form, NormandyIdForm))
        self.assertEqual(normandy_form.data["normandy_id"], bad_normandy_id)
        self.assertFalse(normandy_form.is_valid())


class TestExperimentStatusUpdateView(MockTasksMixin, TestCase):

    def test_view_updates_status_and_redirects(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT
        )

        new_status = experiment.STATUS_REVIEW

        response = self.client.post(
            reverse(
                "experiments-status-update", kwargs={"slug": experiment.slug}
            ),
            {"status": new_status},
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )

        self.assertRedirects(
            response,
            reverse("experiments-detail", kwargs={"slug": experiment.slug}),
            fetch_redirect_response=False,
        )
        updated_experiment = Experiment.objects.get(slug=experiment.slug)
        self.assertEqual(updated_experiment.status, new_status)

    def test_view_redirects_on_failure(self):
        user_email = "user@example.com"
        original_status = Experiment.STATUS_DRAFT
        experiment = ExperimentFactory.create_with_status(original_status)

        response = self.client.post(
            reverse(
                "experiments-status-update", kwargs={"slug": experiment.slug}
            ),
            {"status": Experiment.STATUS_COMPLETE},
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )

        self.assertRedirects(
            response,
            reverse("experiments-detail", kwargs={"slug": experiment.slug}),
            fetch_redirect_response=False,
        )
        updated_experiment = Experiment.objects.get(slug=experiment.slug)
        self.assertEqual(updated_experiment.status, original_status)


class TestExperimentReviewUpdateView(TestCase):

    def test_view_updates_reviews_and_redirects(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_REVIEW
        )

        data = {
            "review_science": True,
            "review_engineering": True,
            "review_qa_requested": True,
            "review_intent_to_ship": True,
            "review_bugzilla": True,
            "review_advisory": True,
            "review_legal": True,
            "review_ux": True,
            "review_security": True,
            "review_vp": True,
            "review_data_steward": True,
            "review_comms": True,
            "review_impacted_teams": True,
        }

        response = self.client.post(
            reverse(
                "experiments-review-update", kwargs={"slug": experiment.slug}
            ),
            data,
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertRedirects(
            response,
            reverse("experiments-detail", kwargs={"slug": experiment.slug}),
            fetch_redirect_response=False,
        )

        experiment = Experiment.objects.get()

        self.assertTrue(experiment.review_science)
        self.assertTrue(experiment.review_legal)
        self.assertTrue(experiment.review_ux)
        self.assertTrue(experiment.review_security)

        change = experiment.changes.latest()

        self.assertEqual(change.changed_by.email, user_email)
        self.assertEqual(change.old_status, experiment.STATUS_REVIEW)
        self.assertEqual(change.new_status, experiment.STATUS_REVIEW)


class TestExperimentCommentCreateView(TestCase):

    def test_view_creates_comment_redirects_to_detail_page(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT
        )

        section = experiment.SECTION_OBJECTIVES
        text = "Hello!"

        response = self.client.post(
            reverse(
                "experiments-comment-create", kwargs={"slug": experiment.slug}
            ),
            {"experiment": experiment.id, "section": section, "text": text},
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )

        self.assertRedirects(
            response,
            "{url}#{section}-comments".format(
                url=reverse(
                    "experiments-detail", kwargs={"slug": experiment.slug}
                ),
                section=section,
            ),
            fetch_redirect_response=False,
        )
        comment = experiment.comments.sections[section][0]
        self.assertEqual(comment.text, text)
        self.assertEqual(comment.created_by.email, user_email)

    def test_view_redirects_to_detail_page_when_form_is_invalid(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_DRAFT
        )

        section = "invalid section"
        text = ""

        response = self.client.post(
            reverse(
                "experiments-comment-create", kwargs={"slug": experiment.slug}
            ),
            {"experiment": experiment.id, "section": section, "text": text},
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )

        self.assertRedirects(
            response,
            reverse("experiments-detail", kwargs={"slug": experiment.slug}),
            fetch_redirect_response=False,
        )


class TestExperimentArchiveUpdateView(TestCase):

    def test_view_flips_archive_bool_and_redirects(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create(archived=False)

        response = self.client.post(
            reverse(
                "experiments-archive-update", kwargs={"slug": experiment.slug}
            ),
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )

        self.assertRedirects(
            response,
            reverse("experiments-detail", kwargs={"slug": experiment.slug}),
            fetch_redirect_response=False,
        )

        experiment = Experiment.objects.get(id=experiment.id)
        self.assertTrue(experiment.archived)


class TestExperimentSubscribedUpdateView(TestCase):

    def test_view_flips_subscribed_bool_and_redirects(self):
        user = UserFactory()
        experiment = ExperimentFactory.create()
        self.assertFalse(user in experiment.subscribers.all())

        response = self.client.post(
            reverse(
                "experiments-subscribed-update",
                kwargs={"slug": experiment.slug},
            ),
            **{settings.OPENIDC_EMAIL_HEADER: user.email},
        )

        self.assertRedirects(
            response,
            reverse("experiments-detail", kwargs={"slug": experiment.slug}),
            fetch_redirect_response=False,
        )

        experiment = Experiment.objects.get(id=experiment.id)
        self.assertTrue(user in experiment.subscribers.all())


class TestExperimentNormandyUpdateView(TestCase):

    def test_valid_recipe_id_updates_experiment_status(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_SHIP
        )
        normandy_id = 123

        response = self.client.post(
            reverse(
                "experiments-normandy-update", kwargs={"slug": experiment.slug}
            ),
            {"normandy_id": normandy_id},
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )
        self.assertRedirects(
            response,
            reverse("experiments-detail", kwargs={"slug": experiment.slug}),
            fetch_redirect_response=False,
        )

        experiment = Experiment.objects.get(id=experiment.id)
        self.assertEqual(experiment.normandy_id, normandy_id)
        self.assertEqual(experiment.status, Experiment.STATUS_ACCEPTED)

    def test_invalid_recipe_id_redirects_to_detail(self):
        user_email = "user@example.com"
        experiment = ExperimentFactory.create_with_status(
            Experiment.STATUS_SHIP
        )
        normandy_id = "abc"

        response = self.client.post(
            reverse(
                "experiments-normandy-update", kwargs={"slug": experiment.slug}
            ),
            {"normandy_id": normandy_id},
            **{settings.OPENIDC_EMAIL_HEADER: user_email},
        )

        detail_url = reverse(
            "experiments-detail", kwargs={"slug": experiment.slug}
        )
        self.assertRedirects(
            response,
            f"{detail_url}?normandy_id={normandy_id}",
            fetch_redirect_response=False,
        )
