import datetime
import decimal
import json
import random

import factory
from django.utils.text import slugify
from django.utils import timezone
from faker import Factory as FakerFactory

from experimenter.base.models import Country, Locale
from experimenter.experiments.constants import ExperimentConstants
from experimenter.experiments.models import (
    Experiment,
    ExperimentChangeLog,
    ExperimentComment,
    ExperimentVariant,
)
from experimenter.openidc.tests.factories import UserFactory
from experimenter.projects.tests.factories import ProjectFactory

faker = FakerFactory.create()


class ExperimentFactory(
    ExperimentConstants, factory.django.DjangoModelFactory
):
    type = Experiment.TYPE_PREF
    owner = factory.SubFactory(UserFactory)
    engineering_owner = factory.LazyAttribute(lambda o: faker.name())
    project = factory.SubFactory(ProjectFactory)
    name = factory.LazyAttribute(lambda o: faker.catch_phrase())
    slug = factory.LazyAttribute(lambda o: "{}_".format(slugify(o.name)))
    archived = False
    short_description = factory.LazyAttribute(
        lambda o: faker.text(random.randint(100, 500))
    )
    data_science_bugzilla_url = (
        "https://bugzilla.mozilla.org/show_bug.cgi?id=12345"
    )
    feature_bugzilla_url = "https://bugzilla.mozilla.org/show_bug.cgi?id=12345"
    related_work = "See also: https://www.example.com/myproject/"
    proposed_start_date = factory.LazyAttribute(
        lambda o: (
            timezone.now().date()
            + datetime.timedelta(days=random.randint(1, 10))
        )
    )
    proposed_duration = factory.LazyAttribute(lambda o: random.randint(10, 60))
    proposed_enrollment = factory.LazyAttribute(
        lambda o: random.choice([None, random.randint(2, o.proposed_duration)])
        if o.proposed_duration
        else None
    )

    population_percent = factory.LazyAttribute(
        lambda o: decimal.Decimal(random.randint(1, 10) * 10)
    )
    client_matching = "Geos: US, CA, GB\n" 'Some "additional" filtering'
    platform = factory.LazyAttribute(
        lambda o: random.choice(Experiment.PLATFORM_CHOICES)[0]
    )

    pref_key = factory.LazyAttribute(
        lambda o: "browser.{pref}.enabled".format(
            pref=faker.catch_phrase().replace(" ", ".").lower()
        )
    )
    pref_type = factory.LazyAttribute(
        lambda o: random.choice(Experiment.PREF_TYPE_CHOICES[1:])[0]
    )
    pref_branch = factory.LazyAttribute(
        lambda o: random.choice(Experiment.PREF_BRANCH_CHOICES[1:])[0]
    )
    firefox_version = factory.LazyAttribute(
        lambda o: random.choice(Experiment.VERSION_CHOICES[1:])[0]
    )
    firefox_channel = factory.LazyAttribute(
        lambda o: random.choice(Experiment.CHANNEL_CHOICES[1:])[0]
    )
    addon_experiment_id = factory.LazyAttribute(
        lambda o: slugify(faker.catch_phrase())
    )
    addon_release_url = factory.LazyAttribute(
        lambda o: "https://www.example.com/{}-release.xpi".format(
            o.addon_experiment_id
        )
    )
    objectives = factory.LazyAttribute(
        lambda o: faker.text(random.randint(500, 5000))
    )
    analysis_owner = factory.LazyAttribute(lambda o: faker.name())
    analysis = factory.LazyAttribute(
        lambda o: faker.text(random.randint(500, 5000))
    )

    risk_internal_only = False
    risk_partner_related = False
    risk_brand = False
    risk_fast_shipped = False
    risk_confidential = False
    risk_release_population = False
    risk_revenue = False
    risk_data_category = False
    risk_external_team_impact = False
    risk_telemetry_data = False
    risk_ux = False
    risk_security = False
    risk_revision = False
    risk_technical = False

    risk_technical_description = factory.LazyAttribute(
        lambda o: faker.text(random.randint(500, 1000))
    )
    risks = factory.LazyAttribute(
        lambda o: faker.text(random.randint(500, 1000))
    )
    testing = factory.LazyAttribute(
        lambda o: faker.text(random.randint(500, 1000))
    )
    test_builds = factory.LazyAttribute(
        lambda o: faker.text(random.randint(500, 1000))
    )
    qa_status = factory.LazyAttribute(
        lambda o: faker.text(random.randint(500, 1000))
    )

    review_advisory = False
    review_science = False
    review_engineering = False
    review_bugzilla = False
    review_qa = False
    review_relman = False
    review_legal = False
    review_ux = False
    review_security = False
    review_vp = False
    review_data_steward = False
    review_comms = False
    review_impacted_teams = False

    bugzilla_id = "12345"

    class Meta:
        model = Experiment

    @classmethod
    def create_with_variants(cls, num_variants=3, *args, **kwargs):
        experiment = cls.create(*args, **kwargs)

        for i in range(num_variants):
            if i == 0:
                ExperimentControlFactory.create(experiment=experiment)
            else:
                ExperimentVariantFactory.create(experiment=experiment)

        return experiment

    @classmethod
    def create_with_status(cls, target_status, *args, **kwargs):
        experiment = cls.create_with_variants(*args, **kwargs)

        now = timezone.now() - datetime.timedelta(
            days=random.randint(100, 200)
        )

        old_status = None
        for status_value, status_label in Experiment.STATUS_CHOICES:
            experiment.status = status_value
            experiment.save()

            change = ExperimentChangeLogFactory.create(
                experiment=experiment,
                old_status=old_status,
                new_status=status_value,
            )
            change.changed_on = now
            change.save()

            if status_value == Experiment.STATUS_SHIP:
                experiment.normandy_slug = experiment.generate_normandy_slug()
                experiment.save()

            if status_value == target_status:
                break

            old_status = status_value
            now += datetime.timedelta(days=random.randint(5, 20))

        return experiment

    @factory.post_generation
    def subscribers(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for user in extracted:
                self.subscribers.add(user)

    @factory.post_generation
    def locales(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted is None:
            extracted = _generate_many_to_many_list(LocaleFactory)

        for locale in extracted:
            self.locales.add(locale)

    @factory.post_generation
    def countries(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted is None:
            extracted = _generate_many_to_many_list(CountryFactory)

        for country in extracted:
            self.countries.add(country)


def _generate_many_to_many_list(factory):
    """Helper function to help generate a list of related objects."""
    # Generate a list of elements with an emphasis on 0- and
    # 1-length lists
    length = random.randint(0, 2)
    if length == 2:
        length = random.randint(2, 30)

    lst = [factory.create() for i in range(length)]

    return lst


class BaseExperimentVariantFactory(factory.django.DjangoModelFactory):
    description = factory.LazyAttribute(lambda o: faker.text())
    experiment = factory.SubFactory(ExperimentFactory)
    name = factory.LazyAttribute(lambda o: faker.catch_phrase())
    slug = factory.LazyAttribute(lambda o: slugify(o.name))

    class Meta:
        model = ExperimentVariant


class ExperimentVariantFactory(BaseExperimentVariantFactory):
    is_control = False
    ratio = factory.LazyAttribute(lambda o: random.randint(1, 10))

    @factory.lazy_attribute
    def value(self):
        value = self.is_control
        if self.experiment.pref_type == Experiment.PREF_TYPE_INT:
            value = random.randint(1, 100)
        elif self.experiment.pref_type == Experiment.PREF_TYPE_STR:
            value = slugify(faker.catch_phrase())
        return json.dumps(value)


class ExperimentControlFactory(ExperimentVariantFactory):
    is_control = True


class ExperimentChangeLogFactory(factory.django.DjangoModelFactory):
    experiment = factory.SubFactory(ExperimentFactory)
    changed_by = factory.SubFactory(UserFactory)
    old_status = factory.LazyAttribute(
        lambda o: random.choice(Experiment.STATUS_CHOICES)[0]
    )
    new_status = factory.LazyAttribute(
        lambda o: random.choice(
            Experiment.STATUS_TRANSITIONS[o.old_status] or [o.old_status]
        )
    )

    class Meta:
        model = ExperimentChangeLog


class ExperimentCommentFactory(factory.django.DjangoModelFactory):
    experiment = factory.SubFactory(ExperimentFactory)
    section = factory.LazyAttribute(
        lambda o: random.choice(Experiment.SECTION_CHOICES)[0]
    )
    created_by = factory.SubFactory(UserFactory)
    text = factory.LazyAttribute(lambda o: faker.text())

    class Meta:
        model = ExperimentComment


def letter_code_sequence(n):
    # faker.Sequence starts at 0, which would produce an empty string
    n += 1
    s = ""
    while n > 0:
        letter = n % 26
        s += chr(letter + ord("a"))
        n = n // 26

    return s


class CountryFactory(factory.django.DjangoModelFactory):
    code = factory.Sequence(letter_code_sequence)
    name = factory.LazyAttribute(lambda o: faker.country())

    class Meta:
        model = Country
        django_get_or_create = ("code",)


class LocaleFactory(factory.django.DjangoModelFactory):
    code = factory.Sequence(letter_code_sequence)
    name = factory.LazyAttribute(
        lambda o: faker.word()  # not technically correct, but sure
    )

    class Meta:
        model = Locale
        django_get_or_create = ("code",)
